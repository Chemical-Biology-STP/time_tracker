"""ProjMgmt sync module — pull projects and push time entries to the server.

Usage from the Time Tracker app:
    sync = ProjMgmtSync("http://10.0.208.117:8009", "user@crick.ac.uk")
    sync.authenticate()
    projects = sync.pull_projects()
    sync.push_entries(group_id, project_mapping)
"""

from __future__ import annotations

import logging
from datetime import datetime

import requests

from .models import db, ResearchGroup, Project, TimeEntry

logger = logging.getLogger(__name__)

# Default ProjMgmt server URL
DEFAULT_PROJMGMT_URL = "http://10.0.208.117:8009"


class ProjMgmtSync:
    """Handles bidirectional sync between local Time Tracker and ProjMgmt server."""

    def __init__(self, server_url: str = DEFAULT_PROJMGMT_URL, email: str = ""):
        self.server_url = server_url.rstrip("/")
        self.email = email
        self.user_info: dict | None = None

    def authenticate(self) -> dict:
        """Authenticate with ProjMgmt and store user info.

        Returns user info dict on success.
        Raises ConnectionError or ValueError on failure.
        """
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

    def _headers(self) -> dict:
        return {"X-Sync-Email": self.email}

    def pull_projects(self, include_all: bool = False) -> list[dict]:
        """Pull the user's projects from ProjMgmt.

        Returns a list of project dicts with id, state, milestone, etc.
        """
        params = {}
        if include_all:
            params["all"] = "true"

        resp = requests.get(
            f"{self.server_url}/sync/projects",
            headers=self._headers(),
            params=params,
            timeout=10,
        )
        if resp.status_code != 200:
            raise ValueError(f"Failed to pull projects: {resp.text}")

        return resp.json()

    def push_entries(
        self,
        group_id: int,
        project_mapping: dict[int, int],
        since_date: str | None = None,
    ) -> dict:
        """Push local time entries to ProjMgmt.

        Args:
            group_id: Local research group ID to sync from.
            project_mapping: Maps local Project.id -> ProjMgmt project ID.
            since_date: Only push entries on or after this date (YYYY-MM-DD).

        Returns dict with created/skipped/errors counts.
        """
        query = TimeEntry.query.filter_by(research_group_id=group_id)

        if since_date:
            from datetime import date as date_cls
            try:
                cutoff = date_cls.fromisoformat(since_date)
                query = query.filter(TimeEntry.date >= cutoff)
            except ValueError:
                pass

        local_entries = query.order_by(TimeEntry.date.asc()).all()

        payload_entries = []
        for entry in local_entries:
            # Map local project to ProjMgmt project
            remote_project_id = None
            if entry.project_id and entry.project_id in project_mapping:
                remote_project_id = project_mapping[entry.project_id]
            elif entry.project_id:
                # Skip entries whose project isn't mapped
                continue
            else:
                # No project assigned locally — skip
                continue

            # Build start/end times from time blocks
            blocks = entry.get_sorted_time_blocks()
            started_at = None
            ended_at = None
            if blocks:
                started_at = datetime.combine(entry.date, blocks[0].start_time).isoformat()
                ended_at = datetime.combine(entry.date, blocks[-1].end_time).isoformat()

            payload_entries.append({
                "project_id": remote_project_id,
                "date": entry.date.isoformat(),
                "description": entry.task_description,
                "duration_minutes": int(entry.total_hours * 60),
                "started_at": started_at,
                "ended_at": ended_at,
                "external_id": f"tt-{entry.id}",
            })

        if not payload_entries:
            return {"created": 0, "skipped": 0, "errors": ["No mapped entries to push"]}

        resp = requests.post(
            f"{self.server_url}/sync/time-entries",
            headers=self._headers(),
            json={"entries": payload_entries},
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            raise ValueError(f"Push failed: {resp.text}")

        return resp.json()

    def pull_time_entries(self, project_id: int | None = None, since: str | None = None) -> list[dict]:
        """Pull time entries from ProjMgmt for the authenticated user."""
        params = {}
        if project_id:
            params["project_id"] = project_id
        if since:
            params["since"] = since

        resp = requests.get(
            f"{self.server_url}/sync/time-entries",
            headers=self._headers(),
            params=params,
            timeout=10,
        )
        if resp.status_code != 200:
            raise ValueError(f"Failed to pull time entries: {resp.text}")

        return resp.json()
