import httpx
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from app.config import get_settings

settings = get_settings()


class YouGileService:
    def __init__(self):
        self.api_key = settings.YOUGILE_API_KEY
        self.base_url = settings.YOUGILE_BASE_URL
        self.board_id = settings.YOUGILE_BOARD_ID
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}{endpoint}"
            try:
                if method == "GET":
                    response = await client.get(url, headers=self.headers, timeout=30)
                elif method == "POST":
                    response = await client.post(url, headers=self.headers, json=data, timeout=30)
                elif method == "PUT":
                    response = await client.put(url, headers=self.headers, json=data, timeout=30)
                elif method == "DELETE":
                    response = await client.delete(url, headers=self.headers, timeout=30)
                else:
                    return {"error": f"Unsupported method: {method}"}

                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}", "details": response.text}
            except Exception as e:
                return {"error": str(e)}

    async def get_boards(self) -> List[Dict]:
        result = await self._request("GET", "/boards")
        return result.get("content", []) if "error" not in result else []

    async def get_columns(self, board_id: str = None) -> List[Dict]:
        bid = board_id or self.board_id
        result = await self._request("GET", f"/boards/{bid}/columns")
        return result.get("content", []) if "error" not in result else []

    async def get_tasks(self, board_id: str = None, column_id: str = None) -> List[Dict]:
        bid = board_id or self.board_id
        params = f"?boardId={bid}"
        if column_id:
            params += f"&columnId={column_id}"
        result = await self._request("GET", f"/tasks{params}")
        return result.get("content", []) if "error" not in result else []

    async def create_task(self, title: str, description: str = "", 
                          assignee_id: str = None, deadline: datetime = None,
                          column_id: str = None, priority: str = "medium") -> Dict[str, Any]:
        data = {
            "title": title,
            "description": description,
            "boardId": self.board_id,
        }
        if column_id:
            data["columnId"] = column_id
        if assignee_id:
            data["assigned"] = [assignee_id]
        if deadline:
            data["deadline"] = deadline.isoformat()

        result = await self._request("POST", "/tasks", data)
        return result

    async def update_task_status(self, task_id: str, column_id: str) -> Dict[str, Any]:
        data = {"columnId": column_id}
        return await self._request("PUT", f"/tasks/{task_id}", data)

    async def close_task(self, task_id: str) -> Dict[str, Any]:
        # In YouGile, closing typically means moving to a "Done" column
        columns = await self.get_columns()
        done_column = None
        for col in columns:
            if any(kw in col.get("title", "").lower() for kw in ["done", "готово", "выполнено", "завершено", "closed"]):
                done_column = col["id"]
                break

        if done_column:
            return await self.update_task_status(task_id, done_column)
        return {"error": "Done column not found"}

    async def sync_task_status(self, local_task_id: str, new_status: str) -> Dict[str, Any]:
        columns = await self.get_columns()
        target_column = None

        status_map = {
            "backlog": ["backlog", "бэклог", "todo", "к выполнению"],
            "todo": ["todo", "к выполнению", "to do"],
            "in_progress": ["in progress", "в работе", "doing", "progress"],
            "review": ["review", "на проверке", "проверка"],
            "done": ["done", "готово", "выполнено", "завершено", "closed"]
        }

        keywords = status_map.get(new_status.lower(), [new_status.lower()])
        for col in columns:
            if any(kw in col.get("title", "").lower() for kw in keywords):
                target_column = col["id"]
                break

        if target_column:
            return await self.update_task_status(local_task_id, target_column)
        return {"error": f"Column for status '{new_status}' not found"}

    async def get_or_create_column(self, title: str) -> str:
        columns = await self.get_columns()
        for col in columns:
            if col.get("title", "").lower() == title.lower():
                return col["id"]

        # Create new column
        data = {
            "title": title,
            "boardId": self.board_id
        }
        result = await self._request("POST", "/columns", data)
        return result.get("id", "")

    async def get_task_by_title(self, title: str) -> Optional[Dict]:
        tasks = await self.get_tasks()
        for task in tasks:
            if task.get("title", "").lower() == title.lower():
                return task
        return None


# Fallback mock service for hackathon demo
class MockKanbanService:
    def __init__(self):
        self.tasks = []
        self.columns = [
            {"id": "col_1", "title": "Backlog"},
            {"id": "col_2", "title": "To Do"},
            {"id": "col_3", "title": "In Progress"},
            {"id": "col_4", "title": "Review"},
            {"id": "col_5", "title": "Done"}
        ]
        self._task_counter = 0

    async def get_boards(self):
        return [{"id": "board_1", "title": "Demo Board"}]

    async def get_columns(self, board_id=None):
        return self.columns

    async def get_tasks(self, board_id=None, column_id=None):
        if column_id:
            return [t for t in self.tasks if t.get("columnId") == column_id]
        return self.tasks

    async def create_task(self, title, description="", assignee_id=None, 
                          deadline=None, column_id=None, priority="medium"):
        self._task_counter += 1
        task = {
            "id": f"task_{self._task_counter}",
            "title": title,
            "description": description,
            "columnId": column_id or "col_2",
            "assigned": [assignee_id] if assignee_id else [],
            "deadline": deadline.isoformat() if deadline else None,
            "priority": priority,
            "createdAt": datetime.now().isoformat()
        }
        self.tasks.append(task)
        return task

    async def update_task_status(self, task_id, column_id):
        for task in self.tasks:
            if task["id"] == task_id:
                task["columnId"] = column_id
                return task
        return {"error": "Task not found"}

    async def close_task(self, task_id):
        return await self.update_task_status(task_id, "col_5")

    async def sync_task_status(self, local_task_id, new_status):
        status_map = {
            "backlog": "col_1",
            "todo": "col_2", 
            "in_progress": "col_3",
            "review": "col_4",
            "done": "col_5"
        }
        col_id = status_map.get(new_status.lower(), "col_2")
        return await self.update_task_status(local_task_id, col_id)

    async def get_task_by_title(self, title):
        for task in self.tasks:
            if task.get("title", "").lower() == title.lower():
                return task
        return None


def get_kanban_service():
    if settings.YOUGILE_API_KEY and settings.YOUGILE_BOARD_ID:
        return YouGileService()
    return MockKanbanService()
