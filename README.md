# Smart ToDo Manager (Advanced DevOps Edition)

This version upgrades the basic app with:

- PostgreSQL persistence
- JWT authentication
- Search/filter/sort/pagination APIs
- Task comments and file attachments
- Improved frontend UX
- CI/CD workflow and stronger Kubernetes manifests

## Features Implemented

### 1. Persistent Storage (PostgreSQL)
- Tasks, users, comments, and attachments metadata are stored in a relational DB.
- Local/dev: `docker-compose.yml` includes PostgreSQL.
- Kubernetes: `postgres-deployment.yaml`, `postgres-service.yaml`, `postgres-pvc.yaml`.

### 2. Authentication (JWT)
- `POST /auth/register`
- `POST /auth/login`
- All task/comment/attachment endpoints are protected with bearer tokens.

### 4. Search / Filter / Sort / Pagination
- `GET /tasks` supports:
  - `search`
  - `status`
  - `priority`
  - `sort_by` (`created_at`, `updated_at`, `title`, `priority`, `status`, `due_date`)
  - `sort_order` (`asc`, `desc`)
  - `page`, `per_page`
  - `due_before`, `due_after`

### 5. Attachments and Comments
- `POST /tasks/<id>/comments`
- `GET /tasks/<id>/comments`
- `POST /tasks/<id>/attachments` (multipart file)
- `GET /tasks/<id>/attachments`
- `GET /attachments/<id>/download`
- `DELETE /attachments/<id>`

## DevOps Improvements

- Hardened Docker image:
  - non-root user
  - healthcheck
  - gunicorn runtime
- Kubernetes improvements:
  - readiness/liveness probes
  - rolling update strategy
  - resource requests/limits
  - HPA (`k8s/hpa.yaml`)
  - ingress (`k8s/ingress.yaml`)
  - secrets for DB/JWT (`k8s/*secret*.yaml`)
  - persistent volumes for DB/uploads
  - network policy for PostgreSQL access
- CI/CD:
  - `.github/workflows/ci-cd.yml`
  - test + docker build on push/PR
  - optional deploy job via `workflow_dispatch` with `KUBE_CONFIG_DATA`
- Safer rollout script:
  - `scripts/rolling-update.ps1` auto-undo on failure

## Local Run (Docker Compose)

```bash
docker compose up --build
```

- Backend API: `http://localhost:5000`
- Frontend: `http://localhost:8080`

## Local Run (Without Docker)

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Open frontend file or serve it:

```bash
cd frontend
python -m http.server 5500
```

Frontend URL: `http://localhost:5500`

## Kubernetes Deploy

Build image inside Minikube:

```bash
minikube image build -t todo-backend:latest backend
```

Apply manifests:

```bash
kubectl apply -k k8s
kubectl get pods
kubectl get svc
```

## Test

```bash
cd backend
pytest -q
```
