# CASE STUDY REPORT: Smart ToDo Manager (Advanced DevOps Edition)

## 1. Introduction
The **Smart ToDo Manager (Advanced DevOps Edition)** represents a full-lifecycle software engineering project aimed at delivering a secure, scalable, and automated task management platform. While standard ToDo applications focus primarily on UI/UX, this "DevOps Edition" prioritizes the underlying infrastructure and operational excellence. By integrating a Flask-based RESTful API with a PostgreSQL backend and orchestrating the entire stack via Kubernetes, the project serves as a practical blueprint for modern cloud-native application development. It addresses the critical challenges of persistent storage, secure authentication, and zero-downtime deployment in a distributed environment.

## 2. Requirement Analysis
### Functional Requirements:
- **Stateless Authentication**: Implementation of a robust login and registration system using **JSON Web Tokens (JWT)**. This allows the backend to remain stateless, facilitating easier horizontal scaling across multiple pods.
- **Granular Task Management**: Beyond basic CRUD, the system supports rich task metadata including description, status (`todo`, `in-progress`, `done`), and priority (`low`, `medium`, `high`).
- **Dynamic Querying Engine**: A sophisticated API layer capable of performing server-side searches, multi-attribute filtering, and page-based retrieval to optimize network bandwidth.
- **Resource Management**: Support for multi-part file uploads (attachments) and nested resource management (comments), providing a collaborative and information-rich environment.

### Non-Functional Requirements:
- **System Persistence & Reliability**: Mandatory use of a relational database (PostgreSQL) to ensure ACID compliance. The system must handle database connections efficiently using modern drivers like `psycopg`.
- **Infrastructure as Code (IaC)**: Every component, from the database and API server to the frontend and ingress rules, must be defined in declarative configuration files (Docker Compose and Kubernetes Yaml).
- **Hardened Security**: The application must follow the principle of least privilege, with Docker containers running as non-root users and sensitive data managed via Kubernetes Secrets.
- **Self-Healing & Scalability**: The deployment must include health checks (Readiness/Liveness probes) and Horizontal Pod Autoscaling (HPA) to maintain uptime and performance during variable load.

## 3. Development Technologies
The project leverages a high-performance stack selected for its stability and community support:
- **API Component**: Python 3.11 with the **Flask** micro-framework. It utilizes **Flask-SQLAlchemy** for database abstraction, **Flask-CORS** for secure cross-origin resource sharing, and **Werkzeug** for secure password hashing (PBKDF2) and filename sanitization.
- **Data Layer**: **PostgreSQL 16** serves as the primary data store. The application uses the `psycopg[binary]` driver for efficient communication with the relational engine.
- **Frontend Layer**: An optimized, framework-less implementation using **Semantic HTML5**, **Vanilla CSS3** with CSS Variables for theme management, and **ES6 JavaScript** for asynchronous API communication via the `fetch` API.
- **DevOps & Orchestration**:
    - **Docker**: Multistage builds used to create small, secure production images.
    - **Kubernetes**: Orchestration via **Kustomize**, including `Deployment`, `Service`, `HorizontalPodAutoscaler`, `Ingress`, and `NetworkPolicy`.
    - **CI/CD**: **GitHub Actions** workflows automate the lifecycle, running **Pytest** for unit testing and building versioned Docker images on every push to the main branch.
    - **Server Environment**: **Gunicorn** serves as the production WSGI HTTP Server, ensuring stable concurrency.

## 4. Modelling Classes (Database Logic)
The application architecture is centered around four primary data models, each managed via SQLAlchemy:
- **User Model**: Storehouse for identity data. It includes a `password_hash` field to ensure no plain-text credentials are ever stored. A one-to-many relationship links users to their specific tasks.
- **Task Model**: The primary entity featuring advanced attributes like `due_date`, `priority`, and `status`. It uses a custom `utcnow` helper to ensure all timestamps are stored in a standardized timezone-agnostic format, preventing synchronization issues.
- **Comment Model**: Facilitates interaction by linking users and tasks. It includes a `cascade="all, delete-orphan"` rule to ensure that when a task is deleted, all associated comments are cleaned up, maintaining database integrity.
- **Attachment Model**: Manages file metadata. To prevent file name collisions and security risks, original filenames are sanitized and mapped to unique `stored_name` identifiers (UUIDs).

## 5. Progress Assessment/Review (Weeks 14 & 15)
- **Week 14 (Backend & Security)**: Focused on securing the API. We implemented strict input validation and integrated **Flask-JWT-Extended** to protect all task and attachment endpoints. Multi-part form handling was refined to support secure file uploads up to 10MB.
- **Week 15 (Infrastructure & Automation)**: The focus shifted to the production environment. We developed Kubernetes manifests for persistent storage (PVC) and configured the **Horizontal Pod Autoscaler (HPA)** to target 50% CPU utilization. The CI/CD pipeline was enhanced with a `workflow_dispatch` trigger for controlled Kubernetes deployments.

## 6. Implementation and Output
The project is structured into distinct modules:
- `/backend`: Contains the Flask application logic and Dockerfile.
- `/frontend`: Holds the static assets served via Nginx.
- `/k8s`: Houses the complete set of Kubernetes resources for a full-stack deployment.
- `/scripts`: Includes utility scripts like `rolling-update.ps1` which provides a safe, scriptable way to update the Kubernetes cluster with automated rollback logic on failure.

## 7. Observations and Learnings
- **Container Hardening**: Running containers as non-root users (UID 1000) significantly improves the security posture by limiting the potential blast radius of an application-level breach.
- **Kubernetes Probes**: The implementation of `readinessProbe` and `livenessProbe` ensures that the cluster only sends traffic to healthy pods and automatically restarts those that have entered an unrecoverable state.
- **Environmental Parity**: Using `postgresql+psycopg` for both local (via Docker Compose) and production (via K8s) environments minimizes "compatibility drift."

## 8. Future Scope
- **Real-Time Synergy**: Integration of **Flask-SocketIO** or **WebSockets** to provide live, multi-user task updates without manual page refreshes.
- **OAuth2 Delegation**: Implementing third-party authentication providers (Google, GitHub, Microsoft) to simplify user onboarding.
- **Advanced Monitoring**: Deployment of the **Prometheus/Grafana** stack to visualize real-time application metrics and server health.
- **Intelligent Search**: Integration of full-text search capabilities using PostgreSQL's native `tsvector` support for even more powerful task filtering.

## 9. Conclusion
The **Smart ToDo Manager (Advanced DevOps Edition)** project successfully demonstrates that even simple applications can benefit from a disciplined, DevOps-centered approach. By focusing on automation, security, and scalability from the outset, the project provides a reliable foundation for any modern cloud-native application.
