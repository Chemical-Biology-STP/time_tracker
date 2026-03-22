"""Bidirectional sync between Time Tracker and ProjMgmt.

Structure (labs, projects, tasks) flows ProjMgmt → Time Tracker.
Time logs flow Time Tracker → ProjMgmt.

Auto-sync runs every 5 minutes via a background thread.
Manual sync is triggered from the /sync page.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime

import requests

from .models import db, ResearchGroup, Project, TimeEntry

logger = logging.getLogger(__name__)

DEFAULT_PROJMGMT_URL = "http://10.0.208.117:8009"
SYNC_INTERVAL_SECONDS = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _instance_dir() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "instance",
    )


def _config_path() -> str:
    return os.path.join(_instance_dir(), "sync_config.json")


def _load_config() -> dict:
    path = _config_path()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _save_config(config: dict) -> None:
    d = _instance_dir()
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "sync_config.json"), "w") as f:
        json.dump(config, f, indent=2)


# ---------------------------------------------------------------------------
# ProjMgmtSync client
# ---------------------------------------------------------------------------

class ProjMgmtSync:
    """Handles bidirectional sync with the ProjMgmt server."""

    def __init__(self, server_url: str = DEFAULT_PROJMGMT_URL, email: str = ""):
        self.server_url = server_url.rstrip("/")
        self.email = email
        self.user_info: dict | None = None

    def _headers(self) -> dict:
        return {"X-Sync-Email": self.email}

    # -- Auth ---------------------------------------------------------------

    def authenticate(self) -> dict:
        """Authenticate with ProjMgmt. Returns user info dict."""
        try:
            resp = requests.post(
                f"{self.server_url}/sync/auth",
                json={"email": self.email},
                timeout=10,
            )
        except requests.RequestException as exc:
            raise ConnectionError(f"Cannot reach ProjMgmt server: {exc}") from exc

        if resp.status_code == 401:
            raise ValueError(f"User '{self.email}' not found on ProjMgmt server.")
        if resp.status_code != 200:
            raise ValueError(f"Auth failed: {resp.text}")

        self.user_info = resp.json()
        return self.user_info

    # -- Initial push (Time Tracker → ProjMgmt) ----------------------------

    def push_initial(self) -> dict:
        """Push all local labs, projects, and time logs to ProjMgmt."""
        groups = ResearchGroup.query.all()

        labs_payload = []
        for g in groups:
            projects = Project.query.filter_by(research_group_id=g.id).all()
            labs_payload.append({
                "id": g.id,
                "name": g.name,
                "manager_name": g.manager_name,
                "projects": [
                    {"id": p.id, "name": p.name, "archived": p.archived}
                    for p in projects
                ],
            })

        entries = TimeEntry.query.all()
        logs_payload = []
        for e in entries:
            logs_payload.append({
                "entry_id": e.id,
                "group_id": e.research_group_id,
                "project_id": e.project_id,
                "date": e.date.isoformat(),
                "task_description": e.task_description,
                "total_hours": e.total_hours,
            })

        resp = requests.post(
            f"{self.server_url}/sync/initial",
            headers=self._headers(),
            json={"labs": labs_payload, "time_logs": logs_payload},
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            raise ValueError(f"Initial push failed: {resp.text}")

        return resp.json()

    # -- Pull structure (ProjMgmt → Time Tracker) --------------------------

    def pull_structure(self) -> dict:
        """Pull labs and projects from ProjMgmt, create locally if missing.

        Also removes local groups/projects that no longer exist on ProjMgmt.
        Returns counts of created/deleted labs/projects.
        """
        resp = requests.get(
            f"{self.server_url}/sync/labs",
            headers=self._headers(),
            timeout=10,
        )
        if resp.status_code != 200:
            raise ValueError(f"Failed to pull labs: {resp.text}")

        remote_labs = resp.json()
        labs_created = 0
        projects_created = 0
        labs_deleted = 0
        projects_deleted = 0

        # Load previously synced lab names so we can detect deletions
        config = _load_config()
        previously_synced_labs = set(config.get("synced_lab_names", []))

        # Collect remote lab names and their project names
        remote_lab_names = set()
        remote_projects_by_lab = {}  # lab_name -> set of project names

        for lab_data in remote_labs:
            lab_name = lab_data.get("name") or f"Lab {lab_data.get('id', '?')}"
            manager = lab_data.get("manager_name") or ""
            remote_lab_names.add(lab_name)
            remote_projects_by_lab[lab_name] = set()

            # Find or create local group
            local_group = ResearchGroup.query.filter_by(name=lab_name).first()
            if not local_group:
                local_group = ResearchGroup(
                    name=lab_name,
                    manager_name=manager,
                    project_name="",
                )
                db.session.add(local_group)
                db.session.flush()
                labs_created += 1

            for proj_data in lab_data.get("projects") or []:
                proj_name = proj_data.get("name") or f"Project {proj_data.get('id', '?')}"
                remote_projects_by_lab[lab_name].add(proj_name)
                local_proj = Project.query.filter_by(
                    name=proj_name, research_group_id=local_group.id
                ).first()
                if not local_proj:
                    local_proj = Project(
                        name=proj_name,
                        research_group_id=local_group.id,
                        archived=bool(proj_data.get("archived")),
                    )
                    db.session.add(local_proj)
                    projects_created += 1

        # Clean up projects: remove local projects under synced labs that
        # no longer exist on ProjMgmt (skip PM- task projects)
        for lab_name in remote_lab_names:
            local_group = ResearchGroup.query.filter_by(name=lab_name).first()
            if not local_group:
                continue
            remote_proj_names = remote_projects_by_lab.get(lab_name, set())
            local_projects = Project.query.filter_by(research_group_id=local_group.id).all()
            for lp in local_projects:
                if lp.name.startswith("PM-"):
                    continue  # task project, handled by pull_tasks
                if lp.name not in remote_proj_names:
                    db.session.delete(lp)
                    projects_deleted += 1

        # Clean up labs: remove local groups that were previously synced
        # from ProjMgmt but no longer exist in the remote set
        deleted_lab_names = previously_synced_labs - remote_lab_names
        for lab_name in deleted_lab_names:
            local_group = ResearchGroup.query.filter_by(name=lab_name).first()
            if not local_group:
                continue
            # Delete all non-PM projects under this group first
            local_projects = Project.query.filter_by(research_group_id=local_group.id).all()
            for lp in local_projects:
                db.session.delete(lp)
                projects_deleted += 1
            # Delete the group itself
            db.session.delete(local_group)
            labs_deleted += 1

        # Save the current set of synced lab names for next time
        config["synced_lab_names"] = sorted(remote_lab_names)
        _save_config(config)

        db.session.commit()
        return {
            "labs_created": labs_created,
            "projects_created": projects_created,
            "labs_deleted": labs_deleted,
            "projects_deleted": projects_deleted,
        }

    # -- Pull tasks (ProjMgmt → Time Tracker) ------------------------------

    def pull_tasks(self) -> dict:
        """Pull ProjMgmt subtasks and create as time entries under the correct project.

        Each subtask becomes a TimeEntry with 0 hours under the lab's project,
        using the subtask title as the task description. The user then fills in
        time blocks to log actual hours.

        Also cleans up old-style PM-* projects from previous sync versions.

        Returns counts of entries created/deleted.
        """
        from datetime import date as date_cls

        resp = requests.get(
            f"{self.server_url}/sync/tasks",
            headers=self._headers(),
            params={"all": "true"},
            timeout=10,
        )
        if resp.status_code != 200:
            raise ValueError(f"Failed to pull tasks: {resp.text}")

        tasks = resp.json()
        if not tasks:
            return {"tasks_created": 0, "tasks_deleted": 0}

        tasks_created = 0
        tasks_deleted = 0

        for task in tasks:
            task_id = task.get("id") or "?"
            lab_name = task.get("lab_name") or ""
            lab_project_name = task.get("lab_project_name") or ""
            subtasks = task.get("subtasks") or []

            # Clean up any old-style PM-* projects (from previous sync versions)
            pm_prefix = f"PM-{task_id}"
            old_projects = Project.query.filter(
                Project.name.like(f"{pm_prefix}%")
            ).all()
            for op in old_projects:
                db.session.delete(op)
                tasks_deleted += 1

            # Find the local group and project for this task's lab
            if not lab_name:
                continue

            local_group = ResearchGroup.query.filter_by(name=lab_name).first()
            if not local_group:
                continue

            local_project = None
            if lab_project_name:
                local_project = Project.query.filter_by(
                    name=lab_project_name, research_group_id=local_group.id
                ).first()

            # Create time entries for each subtask
            for st in subtasks:
                st_id = st.get("id") or "?"
                st_title = st.get("title") or "Subtask"
                # Tag with PM prefix so we can identify synced entries
                entry_desc = f"[PM-{task_id}.{st_id}] {st_title}"

                # Check if this entry already exists (by description match)
                existing = TimeEntry.query.filter_by(
                    research_group_id=local_group.id,
                    task_description=entry_desc,
                ).first()
                if not existing:
                    entry = TimeEntry(
                        research_group_id=local_group.id,
                        project_id=local_project.id if local_project else None,
                        date=date_cls.today(),
                        task_description=entry_desc,
                        total_hours=0.0,
                    )
                    db.session.add(entry)
                    tasks_created += 1

        db.session.commit()
        return {"tasks_created": tasks_created, "tasks_deleted": tasks_deleted}

    # -- Push time logs (Time Tracker → ProjMgmt) --------------------------

    def push_time_logs(self, since_date: str | None = None) -> dict:
        """Push all local time entries to ProjMgmt as time logs.

        Returns counts of created/updated/skipped/errors.
        """
        query = TimeEntry.query
        if since_date:
            try:
                from datetime import date as date_cls
                cutoff = date_cls.fromisoformat(since_date)
                query = query.filter(TimeEntry.date >= cutoff)
            except ValueError:
                pass

        entries = query.order_by(TimeEntry.date.asc()).all()

        payload = []
        for e in entries:
            if not e.project_id:
                continue
            group_name = e.group.name if e.group else ""
            project_name = e.project.name if e.project else ""
            payload.append({
                "entry_id": e.id,
                "group_id": e.research_group_id,
                "project_id": e.project_id,
                "group_name": group_name,
                "project_name": project_name,
                "date": e.date.isoformat(),
                "task_description": e.task_description or "",
                "total_hours": e.total_hours or 0,
            })

        if not payload:
            return {"created": 0, "updated": 0, "skipped": 0, "errors": ["No entries to push"]}

        resp = requests.post(
            f"{self.server_url}/sync/time-logs",
            headers=self._headers(),
            json={"entries": payload},
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            raise ValueError(f"Push failed: {resp.text}")

        return resp.json()

    # -- Pull changes (ProjMgmt → Time Tracker) ----------------------------

    def pull_changes(self, since: str | None = None) -> dict:
        """Pull changes from ProjMgmt since a given timestamp.

        Creates new local groups/projects as needed.
        Returns summary of what was synced.
        """
        params = {}
        if since:
            params["since"] = since

        resp = requests.get(
            f"{self.server_url}/sync/changes",
            headers=self._headers(),
            params=params,
            timeout=10,
        )
        if resp.status_code != 200:
            raise ValueError(f"Failed to pull changes: {resp.text}")

        data = resp.json()
        labs_created = 0
        projects_created = 0

        # Process new labs
        for lab_data in data.get("labs") or []:
            lab_name = lab_data.get("name") or f"Lab {lab_data.get('id', '?')}"
            local_group = ResearchGroup.query.filter_by(name=lab_name).first()
            if not local_group:
                local_group = ResearchGroup(
                    name=lab_name,
                    manager_name=lab_data.get("manager_name") or "",
                    project_name="",
                )
                db.session.add(local_group)
                db.session.flush()
                labs_created += 1

            for proj_data in lab_data.get("projects") or []:
                proj_name = proj_data.get("name") or f"Project {proj_data.get('id', '?')}"
                if not Project.query.filter_by(name=proj_name, research_group_id=local_group.id).first():
                    db.session.add(Project(
                        name=proj_name,
                        research_group_id=local_group.id,
                        archived=bool(proj_data.get("archived")),
                    ))
                    projects_created += 1

        # Process new standalone projects
        for proj_data in data.get("projects") or []:
            lab_name = proj_data.get("lab_name") or "Unknown Lab"
            local_group = ResearchGroup.query.filter_by(name=lab_name).first()
            if not local_group:
                local_group = ResearchGroup(
                    name=lab_name, manager_name="", project_name=""
                )
                db.session.add(local_group)
                db.session.flush()
                labs_created += 1

            proj_name = proj_data.get("name") or f"Project {proj_data.get('id', '?')}"
            if not Project.query.filter_by(name=proj_name, research_group_id=local_group.id).first():
                db.session.add(Project(
                    name=proj_name,
                    research_group_id=local_group.id,
                    archived=bool(proj_data.get("archived")),
                ))
                projects_created += 1

        db.session.commit()

        server_time = data.get("server_time")
        return {
            "labs_created": labs_created,
            "projects_created": projects_created,
            "tasks": len(data.get("tasks") or []),
            "server_time": server_time,
        }

    # -- Full sync (convenience) -------------------------------------------

    def full_sync(self, since: str | None = None) -> dict:
        """Run a full bidirectional sync cycle.

        1. Pull structure + changes from ProjMgmt
        2. Push time logs to ProjMgmt
        """
        self.authenticate()

        pull_result = self.pull_changes(since)
        push_result = self.push_time_logs()

        return {
            "pull": pull_result,
            "push": push_result,
        }


# ---------------------------------------------------------------------------
# Background auto-sync
# ---------------------------------------------------------------------------

_sync_thread: threading.Thread | None = None
_sync_stop_event = threading.Event()


def _auto_sync_loop(app):
    """Background loop that runs full_sync every SYNC_INTERVAL_SECONDS."""
    logger.info("Auto-sync thread started (interval=%ds)", SYNC_INTERVAL_SECONDS)

    while not _sync_stop_event.is_set():
        config = _load_config()
        server_url = config.get("server_url")
        email = config.get("email")
        last_sync = config.get("last_sync")

        if server_url and email:
            try:
                with app.app_context():
                    sync_client = ProjMgmtSync(server_url, email)
                    result = sync_client.full_sync(since=last_sync)

                    # Update last_sync timestamp
                    server_time = result.get("pull", {}).get("server_time")
                    if server_time:
                        config["last_sync"] = server_time
                        _save_config(config)

                    logger.info("Auto-sync completed: %s", result)
            except Exception:
                logger.exception("Auto-sync failed")
        else:
            logger.debug("Auto-sync skipped — no config")

        _sync_stop_event.wait(SYNC_INTERVAL_SECONDS)

    logger.info("Auto-sync thread stopped")


def start_auto_sync(app):
    """Start the background auto-sync thread."""
    global _sync_thread
    if _sync_thread and _sync_thread.is_alive():
        return  # already running

    _sync_stop_event.clear()
    _sync_thread = threading.Thread(
        target=_auto_sync_loop, args=(app,), daemon=True, name="projmgmt-sync"
    )
    _sync_thread.start()


def stop_auto_sync():
    """Stop the background auto-sync thread."""
    _sync_stop_event.set()
    if _sync_thread:
        _sync_thread.join(timeout=5)
