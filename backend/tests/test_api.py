import io
import os
import pathlib
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app import create_app, db


@pytest.fixture()
def client():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "JWT_SECRET_KEY": "this-is-a-very-long-test-secret-key-for-jwt",
            "UPLOAD_FOLDER": tempfile.mkdtemp(prefix="todo-uploads-"),
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()

    with app.test_client() as test_client:
        yield test_client

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()

    os.close(db_fd)
    try:
        os.unlink(db_path)
    except PermissionError:
        pass


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client):
    register_resp = client.post(
        "/auth/register", json={"username": "tester", "password": "password123"}
    )
    assert register_resp.status_code == 201

    login_resp = client.post("/auth/login", json={"username": "tester", "password": "password123"})
    assert login_resp.status_code == 200
    token = login_resp.get_json()["access_token"]
    return token


def test_auth_and_task_crud_with_filters(client):
    token = register_and_login(client)
    headers = auth_headers(token)

    create_1 = client.post(
        "/tasks",
        headers=headers,
        json={
            "title": "Buy groceries",
            "description": "Milk and eggs",
            "status": "todo",
            "priority": "high",
            "due_date": "2026-03-10",
        },
    )
    assert create_1.status_code == 201

    create_2 = client.post(
        "/tasks",
        headers=headers,
        json={"title": "Read docs", "status": "in-progress", "priority": "low"},
    )
    assert create_2.status_code == 201

    filtered = client.get(
        "/tasks?search=groceries&status=todo&priority=high&page=1&per_page=5&sort_by=title&sort_order=asc",
        headers=headers,
    )
    assert filtered.status_code == 200
    payload = filtered.get_json()
    assert payload["pagination"]["total"] == 1
    assert payload["items"][0]["title"] == "Buy groceries"

    task_id = create_1.get_json()["task"]["id"]
    update = client.patch(f"/tasks/{task_id}", headers=headers, json={"status": "done"})
    assert update.status_code == 200
    assert update.get_json()["task"]["status"] == "done"

    delete = client.delete(f"/tasks/{task_id}", headers=headers)
    assert delete.status_code == 200


def test_comments_and_attachments(client):
    token = register_and_login(client)
    headers = auth_headers(token)

    create_task = client.post("/tasks", headers=headers, json={"title": "Task with files"})
    task_id = create_task.get_json()["task"]["id"]

    comment = client.post(
        f"/tasks/{task_id}/comments", headers=headers, json={"content": "Initial comment"}
    )
    assert comment.status_code == 201

    comments = client.get(f"/tasks/{task_id}/comments", headers=headers)
    assert comments.status_code == 200
    assert len(comments.get_json()) == 1

    upload = client.post(
        f"/tasks/{task_id}/attachments",
        headers=headers,
        data={"file": (io.BytesIO(b"hello world"), "note.txt")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201
    attachment_id = upload.get_json()["attachment"]["id"]

    attachments = client.get(f"/tasks/{task_id}/attachments", headers=headers)
    assert attachments.status_code == 200
    assert len(attachments.get_json()) == 1

    delete_attachment = client.delete(f"/attachments/{attachment_id}", headers=headers)
    assert delete_attachment.status_code == 200
