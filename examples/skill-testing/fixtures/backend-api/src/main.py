"""Main FastAPI application.

This file contains intentional issues for skill testing:
- Fat route handlers with business logic inline
- Poor error handling
- Missing validation
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Task API")


# In-memory storage (simulating a database)
tasks_db: dict[int, dict] = {
    1: {"id": 1, "title": "First task", "completed": False, "user_id": 1},
    2: {"id": 2, "title": "Second task", "completed": True, "user_id": 1},
}
users_db: dict[int, dict] = {
    1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
    2: {"id": 2, "name": "Bob", "email": "bob@example.com"},
}
next_task_id = 3


class TaskCreate(BaseModel):
    title: str
    user_id: int


class TaskUpdate(BaseModel):
    title: str | None = None
    completed: bool | None = None


# ISSUE: Fat route handler - business logic inline, no service layer
@app.get("/tasks")
def get_tasks(user_id: int | None = None, completed: bool | None = None):
    """Get all tasks with optional filters."""
    result = []
    for task in tasks_db.values():
        # Business logic mixed with HTTP handling
        if user_id is not None and task["user_id"] != user_id:
            continue
        if completed is not None and task["completed"] != completed:
            continue

        # Inline data transformation
        user = users_db.get(task["user_id"])
        result.append({
            "id": task["id"],
            "title": task["title"],
            "completed": task["completed"],
            "user_name": user["name"] if user else "Unknown",
        })
    return {"tasks": result, "count": len(result)}


# ISSUE: Poor error handling - catches generic Exception, exposes internal errors
@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Get a specific task by ID."""
    try:
        task = tasks_db[task_id]
        user = users_db[task["user_id"]]
        return {
            "id": task["id"],
            "title": task["title"],
            "completed": task["completed"],
            "user": {"id": user["id"], "name": user["name"]},
        }
    except Exception as e:
        # ISSUE: Exposes internal error messages
        raise HTTPException(status_code=500, detail=str(e))


# ISSUE: Fat handler with validation, business logic, and persistence all mixed
@app.post("/tasks")
def create_task(task: TaskCreate):
    """Create a new task."""
    global next_task_id

    # Validation mixed in handler
    if len(task.title) < 1:
        raise HTTPException(status_code=400, detail="Title too short")
    if len(task.title) > 200:
        raise HTTPException(status_code=400, detail="Title too long")

    # Check user exists - business logic in handler
    if task.user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")

    # Create task - persistence logic in handler
    new_task = {
        "id": next_task_id,
        "title": task.title,
        "completed": False,
        "user_id": task.user_id,
    }
    tasks_db[next_task_id] = new_task
    next_task_id += 1

    return {"message": "Task created", "task": new_task}


# ISSUE: No error handling at all
@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):
    """Update an existing task."""
    existing = tasks_db[task_id]  # KeyError if not found - no handling!

    if task.title is not None:
        existing["title"] = task.title
    if task.completed is not None:
        existing["completed"] = task.completed

    return existing


# ISSUE: Inconsistent error response format
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    """Delete a task."""
    if task_id not in tasks_db:
        # Different error format than other endpoints
        return {"error": True, "message": "Task not found"}

    del tasks_db[task_id]
    return {"success": True}
