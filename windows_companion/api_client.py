"""
API client for communicating with the Flask backend.
"""

import requests
from dataclasses import dataclass
from typing import Optional
from datetime import date


@dataclass
class ResearchGroup:
    """Research group model."""
    id: int
    name: str
    manager_name: str
    project_name: str


@dataclass
class TimeEntryResponse:
    """Response from creating a time entry."""
    id: int
    date: str
    task_description: str
    total_hours: float


class APIClient:
    """HTTP client for Flask backend API communication."""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url.rstrip("/")
        self.timeout = 10
    
    def update_base_url(self, url: str):
        """Update the backend URL."""
        self.base_url = url.rstrip("/")
    
    def health_check(self) -> bool:
        """Check if the Flask backend is reachable."""
        try:
            response = requests.get(
                f"{self.base_url}/api/health",
                timeout=self.timeout
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def fetch_groups(self) -> list[ResearchGroup]:
        """Fetch all research groups from the backend."""
        try:
            response = requests.get(
                f"{self.base_url}/api/groups",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            groups = []
            for g in response.json():
                groups.append(ResearchGroup(
                    id=g["id"],
                    name=g["name"],
                    manager_name=g.get("manager_name", ""),
                    project_name=g.get("project_name", "")
                ))
            return groups
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to fetch groups: {e}")
    
    def create_group(self, name: str, manager_name: str = "", project_name: str = "") -> ResearchGroup:
        """Create a new research group."""
        try:
            response = requests.post(
                f"{self.base_url}/api/groups",
                json={
                    "name": name,
                    "manager_name": manager_name,
                    "project_name": project_name
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            g = response.json()
            return ResearchGroup(
                id=g["id"],
                name=g["name"],
                manager_name=g.get("manager_name", ""),
                project_name=g.get("project_name", "")
            )
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to create group: {e}")
    
    def delete_group(self, group_id: int) -> bool:
        """Delete a research group."""
        try:
            response = requests.delete(
                f"{self.base_url}/api/groups/{group_id}",
                timeout=self.timeout
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def create_entry(
        self,
        research_group_id: int,
        task_description: str,
        start_time: str,
        end_time: str,
        entry_date: Optional[str] = None
    ) -> TimeEntryResponse:
        """Create a new time entry."""
        if entry_date is None:
            entry_date = date.today().isoformat()
        
        try:
            response = requests.post(
                f"{self.base_url}/api/entries",
                json={
                    "research_group_id": research_group_id,
                    "task_description": task_description,
                    "date": entry_date,
                    "start_time": start_time,
                    "end_time": end_time
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            return TimeEntryResponse(
                id=data["id"],
                date=data["date"],
                task_description=data["task_description"],
                total_hours=data["total_hours"]
            )
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to create entry: {e}")
