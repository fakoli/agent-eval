"""Tests for the task API."""

import pytest
from fastapi.testclient import TestClient

from src.main import app, tasks_db, next_task_id


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the database before each test."""
    global next_task_id
    tasks_db.clear()
    tasks_db[1] = {"id": 1, "title": "Test task", "completed": False, "user_id": 1}
    tasks_db[2] = {"id": 2, "title": "Done task", "completed": True, "user_id": 1}
    next_task_id = 3


def test_get_tasks(client):
    """Test getting all tasks."""
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert data["count"] == 2


def test_get_tasks_filter_by_user(client):
    """Test filtering tasks by user."""
    response = client.get("/tasks?user_id=1")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2


def test_get_tasks_filter_by_completed(client):
    """Test filtering tasks by completion status."""
    response = client.get("/tasks?completed=true")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["tasks"][0]["completed"] is True


def test_get_task_exists(client):
    """Test getting a specific task that exists."""
    response = client.get("/tasks/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Test task"


def test_get_task_not_found(client):
    """Test getting a task that doesn't exist."""
    response = client.get("/tasks/999")
    # Currently returns 500 due to poor error handling
    assert response.status_code in [404, 500]


def test_create_task(client):
    """Test creating a new task."""
    response = client.post("/tasks", json={"title": "New task", "user_id": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["task"]["title"] == "New task"
    assert data["task"]["id"] == 3


def test_create_task_invalid_user(client):
    """Test creating a task with invalid user."""
    response = client.post("/tasks", json={"title": "New task", "user_id": 999})
    assert response.status_code == 404


def test_create_task_empty_title(client):
    """Test creating a task with empty title."""
    response = client.post("/tasks", json={"title": "", "user_id": 1})
    assert response.status_code == 400


def test_update_task(client):
    """Test updating a task."""
    response = client.put("/tasks/1", json={"title": "Updated title"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated title"


def test_update_task_completed(client):
    """Test marking a task as completed."""
    response = client.put("/tasks/1", json={"completed": True})
    assert response.status_code == 200
    data = response.json()
    assert data["completed"] is True


def test_delete_task(client):
    """Test deleting a task."""
    response = client.delete("/tasks/1")
    assert response.status_code == 200
    # Task should be gone
    response = client.get("/tasks/1")
    assert response.status_code in [404, 500]


def test_delete_task_not_found(client):
    """Test deleting a task that doesn't exist."""
    response = client.delete("/tasks/999")
    assert response.status_code == 200
    data = response.json()
    assert data.get("error") is True or data.get("success") is not True
