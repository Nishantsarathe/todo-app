import os
import uuid
from datetime import date, datetime, timezone

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

db = SQLAlchemy()
jwt = JWTManager()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    tasks = db.relationship("Task", backref="owner", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at.isoformat(),
        }


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="todo", nullable=False, index=True)
    priority = db.Column(db.String(20), default="medium", nullable=False, index=True)
    due_date = db.Column(db.Date, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    updated_at = db.Column(
        db.DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
        index=True,
    )

    comments = db.relationship("Comment", backref="task", lazy=True, cascade="all, delete-orphan")
    attachments = db.relationship(
        "Attachment", backref="task", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self, include_children=False):
        payload = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "comments_count": len(self.comments),
            "attachments_count": len(self.attachments),
        }
        if include_children:
            payload["comments"] = [comment.to_dict() for comment in self.comments]
            payload["attachments"] = [attachment.to_dict() for attachment in self.attachments]
        return payload


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }


class Attachment(db.Model):
    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False, unique=True)
    mime_type = db.Column(db.String(120), nullable=True)
    size = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "original_name": self.original_name,
            "mime_type": self.mime_type,
            "size": self.size,
            "created_at": self.created_at.isoformat(),
        }


def _parse_due_date(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == "":
        return None
    return date.fromisoformat(value)


def _get_database_uri():
    direct_uri = os.getenv("DATABASE_URL")
    if direct_uri:
        if direct_uri.startswith("postgres://"):
            return direct_uri.replace("postgres://", "postgresql+psycopg://", 1)
        if direct_uri.startswith("postgresql://") and "+psycopg" not in direct_uri:
            return direct_uri.replace("postgresql://", "postgresql+psycopg://", 1)
        return direct_uri

    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_port = os.getenv("DB_PORT", "5432")
    if db_host and db_name and db_user and db_password:
        return f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    return "sqlite:///todo.db"


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = _get_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
    app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", os.path.join(os.getcwd(), "uploads"))
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    CORS(app)
    db.init_app(app)
    jwt.init_app(app)

    with app.app_context():
        db.create_all()

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok"}), 200

    @app.post("/auth/register")
    def register():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip().lower()
        password = data.get("password") or ""

        if len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters"}), 400
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        existing = User.query.filter_by(username=username).first()
        if existing:
            return jsonify({"error": "Username already exists"}), 409

        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "User registered", "user": user.to_dict()}), 201

    @app.post("/auth/login")
    def login():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip().lower()
        password = data.get("password") or ""

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid username or password"}), 401

        token = create_access_token(identity=str(user.id))
        return jsonify({"access_token": token, "user": user.to_dict()}), 200

    def current_user():
        user_id = get_jwt_identity()
        return db.session.get(User, int(user_id))

    def get_user_task_or_404(task_id):
        user = current_user()
        task = Task.query.filter_by(id=task_id, user_id=user.id).first()
        if not task:
            return None, jsonify({"error": "Task not found"}), 404
        return task, None, None

    @app.get("/tasks")
    @jwt_required()
    def list_tasks():
        user = current_user()
        query = Task.query.filter_by(user_id=user.id)

        search = (request.args.get("search") or "").strip()
        if search:
            like = f"%{search}%"
            query = query.filter(or_(Task.title.ilike(like), Task.description.ilike(like)))

        status = (request.args.get("status") or "").strip().lower()
        if status:
            query = query.filter(Task.status == status)

        priority = (request.args.get("priority") or "").strip().lower()
        if priority:
            query = query.filter(Task.priority == priority)

        due_before = request.args.get("due_before")
        if due_before:
            try:
                query = query.filter(Task.due_date <= date.fromisoformat(due_before))
            except ValueError:
                return jsonify({"error": "Invalid due_before date format. Use YYYY-MM-DD."}), 400

        due_after = request.args.get("due_after")
        if due_after:
            try:
                query = query.filter(Task.due_date >= date.fromisoformat(due_after))
            except ValueError:
                return jsonify({"error": "Invalid due_after date format. Use YYYY-MM-DD."}), 400

        sort_by = (request.args.get("sort_by") or "created_at").strip()
        sort_order = (request.args.get("sort_order") or "desc").strip().lower()
        sort_columns = {
            "created_at": Task.created_at,
            "updated_at": Task.updated_at,
            "title": Task.title,
            "priority": Task.priority,
            "status": Task.status,
            "due_date": Task.due_date,
        }
        column = sort_columns.get(sort_by, Task.created_at)
        query = query.order_by(column.asc() if sort_order == "asc" else column.desc())

        try:
            page = max(1, int(request.args.get("page", 1)))
            per_page = min(50, max(1, int(request.args.get("per_page", 10))))
        except ValueError:
            return jsonify({"error": "page and per_page must be integers"}), 400

        result = query.paginate(page=page, per_page=per_page, error_out=False)
        return (
            jsonify(
                {
                    "items": [task.to_dict() for task in result.items],
                    "pagination": {
                        "page": result.page,
                        "per_page": result.per_page,
                        "total": result.total,
                        "pages": result.pages,
                        "has_next": result.has_next,
                        "has_prev": result.has_prev,
                    },
                }
            ),
            200,
        )

    @app.post("/tasks")
    @jwt_required()
    def create_task():
        user = current_user()
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()

        if not title:
            return jsonify({"error": "Task title is required"}), 400

        status = (data.get("status") or "todo").strip().lower()
        priority = (data.get("priority") or "medium").strip().lower()
        allowed_status = {"todo", "in-progress", "done"}
        allowed_priority = {"low", "medium", "high"}
        if status not in allowed_status:
            return jsonify({"error": "status must be one of todo, in-progress, done"}), 400
        if priority not in allowed_priority:
            return jsonify({"error": "priority must be one of low, medium, high"}), 400

        try:
            due_date = _parse_due_date(data.get("due_date"))
        except ValueError:
            return jsonify({"error": "Invalid due_date format. Use YYYY-MM-DD."}), 400

        task = Task(
            user_id=user.id,
            title=title,
            description=(data.get("description") or "").strip(),
            status=status,
            priority=priority,
            due_date=due_date,
        )
        db.session.add(task)
        db.session.commit()
        return jsonify({"message": "Task created", "task": task.to_dict()}), 201

    @app.get("/tasks/<int:task_id>")
    @jwt_required()
    def get_task(task_id):
        task, error_resp, status_code = get_user_task_or_404(task_id)
        if not task:
            return error_resp, status_code
        return jsonify(task.to_dict(include_children=True)), 200

    @app.patch("/tasks/<int:task_id>")
    @jwt_required()
    def update_task(task_id):
        task, error_resp, status_code = get_user_task_or_404(task_id)
        if not task:
            return error_resp, status_code

        data = request.get_json(silent=True) or {}
        if "title" in data:
            title = (data.get("title") or "").strip()
            if not title:
                return jsonify({"error": "Task title cannot be empty"}), 400
            task.title = title

        if "description" in data:
            task.description = (data.get("description") or "").strip()

        if "status" in data:
            status = (data.get("status") or "").strip().lower()
            if status not in {"todo", "in-progress", "done"}:
                return jsonify({"error": "status must be one of todo, in-progress, done"}), 400
            task.status = status

        if "priority" in data:
            priority = (data.get("priority") or "").strip().lower()
            if priority not in {"low", "medium", "high"}:
                return jsonify({"error": "priority must be one of low, medium, high"}), 400
            task.priority = priority

        if "due_date" in data:
            try:
                task.due_date = _parse_due_date(data.get("due_date"))
            except ValueError:
                return jsonify({"error": "Invalid due_date format. Use YYYY-MM-DD."}), 400

        db.session.commit()
        return jsonify({"message": "Task updated", "task": task.to_dict()}), 200

    @app.delete("/tasks/<int:task_id>")
    @jwt_required()
    def delete_task(task_id):
        task, error_resp, status_code = get_user_task_or_404(task_id)
        if not task:
            return error_resp, status_code

        for attachment in task.attachments:
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], attachment.stored_name)
            if os.path.exists(file_path):
                os.remove(file_path)

        db.session.delete(task)
        db.session.commit()
        return jsonify({"message": "Task deleted"}), 200

    @app.get("/tasks/<int:task_id>/comments")
    @jwt_required()
    def list_comments(task_id):
        task, error_resp, status_code = get_user_task_or_404(task_id)
        if not task:
            return error_resp, status_code

        comments = Comment.query.filter_by(task_id=task.id).order_by(Comment.created_at.desc()).all()
        return jsonify([comment.to_dict() for comment in comments]), 200

    @app.post("/tasks/<int:task_id>/comments")
    @jwt_required()
    def add_comment(task_id):
        user = current_user()
        task, error_resp, status_code = get_user_task_or_404(task_id)
        if not task:
            return error_resp, status_code

        data = request.get_json(silent=True) or {}
        content = (data.get("content") or "").strip()
        if not content:
            return jsonify({"error": "Comment content is required"}), 400

        comment = Comment(task_id=task.id, user_id=user.id, content=content)
        db.session.add(comment)
        db.session.commit()
        return jsonify({"message": "Comment added", "comment": comment.to_dict()}), 201

    @app.get("/tasks/<int:task_id>/attachments")
    @jwt_required()
    def list_attachments(task_id):
        task, error_resp, status_code = get_user_task_or_404(task_id)
        if not task:
            return error_resp, status_code

        attachments = (
            Attachment.query.filter_by(task_id=task.id).order_by(Attachment.created_at.desc()).all()
        )
        return jsonify([attachment.to_dict() for attachment in attachments]), 200

    @app.post("/tasks/<int:task_id>/attachments")
    @jwt_required()
    def upload_attachment(task_id):
        user = current_user()
        task, error_resp, status_code = get_user_task_or_404(task_id)
        if not task:
            return error_resp, status_code

        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if not file or not file.filename:
            return jsonify({"error": "Invalid file"}), 400

        original_name = secure_filename(file.filename)
        if original_name == "":
            return jsonify({"error": "Invalid file name"}), 400

        stored_name = f"{uuid.uuid4().hex}_{original_name}"
        upload_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
        file.save(upload_path)
        size = os.path.getsize(upload_path)

        attachment = Attachment(
            task_id=task.id,
            user_id=user.id,
            original_name=original_name,
            stored_name=stored_name,
            mime_type=file.content_type,
            size=size,
        )
        db.session.add(attachment)
        db.session.commit()
        return jsonify({"message": "Attachment uploaded", "attachment": attachment.to_dict()}), 201

    @app.get("/attachments/<int:attachment_id>/download")
    @jwt_required()
    def download_attachment(attachment_id):
        user = current_user()
        attachment = db.session.get(Attachment, attachment_id)
        if not attachment:
            return jsonify({"error": "Attachment not found"}), 404
        if attachment.task.user_id != user.id:
            return jsonify({"error": "Forbidden"}), 403

        return send_from_directory(
            app.config["UPLOAD_FOLDER"],
            attachment.stored_name,
            as_attachment=True,
            download_name=attachment.original_name,
        )

    @app.delete("/attachments/<int:attachment_id>")
    @jwt_required()
    def delete_attachment(attachment_id):
        user = current_user()
        attachment = db.session.get(Attachment, attachment_id)
        if not attachment:
            return jsonify({"error": "Attachment not found"}), 404
        if attachment.task.user_id != user.id:
            return jsonify({"error": "Forbidden"}), 403

        file_path = os.path.join(app.config["UPLOAD_FOLDER"], attachment.stored_name)
        if os.path.exists(file_path):
            os.remove(file_path)

        db.session.delete(attachment)
        db.session.commit()
        return jsonify({"message": "Attachment deleted"}), 200

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(413)
    def file_too_large(_):
        return jsonify({"error": "File exceeds size limit"}), 413

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
