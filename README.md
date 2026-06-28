# Django & React Custom Boilerplate (`custom_bp`)

This is a comprehensive, production-ready backend boilerplate built with Django, Django REST Framework (DRF), and Celery, designed for rapid API development. It utilizes **uv** for lightning-fast package management and **Docker Compose** for local development.

---

## 🚀 Key Features
* **Package Management**: Powered by [uv](https://github.com/astral-sh/uv) (standards-compliant, extremely fast PEP 621 environment).
* **API Framework**: Django REST Framework (DRF) with custom JSON responders, simplejwt authentication, and API schema decorators.
* **Authentication**: JWT-based login/logout, OTP verification, password reset workflows, and TOTP/2FA support.
* **Task Queues & Caching**: Celery + Celery Beat + Redis setup for handling asynchronous tasks and periodic schedules.
* **Database**: PostgreSQL integration with pre-configured health checks.
* **Email Testing**: Outbox mail redirection captured by Mailhog.
* **Development Tooling**: Ruff for linting, Pre-commit hooks for git standards, and Adminer for visual database inspection.

---

## 🛠️ Tech Stack & Services
* **Backend**: Django 5.x, DRF, Gunicorn, Whitenoise
* **Database**: PostgreSQL 16
* **Task Broker & Cache**: Redis
* **Database UI**: Adminer (Port `8000`)
* **Email Capture**: Mailhog (Port `8025` / SMTP `1025`)
* **Package Manager**: UV (0.11+)

---

## 📦 Getting Started

### Prerequisites
1. Install [uv](https://astral.sh/uv/install.sh) (Python package manager).
2. Install [Docker](https://www.docker.com/) and Docker Compose.
3. Use a Linux-based terminal or WSL (Windows Subsystem for Linux).

---

### Local Development Setup (Using `uv`)

If you want to run or check code formatting/typing locally without containers:

1. **Install dependencies and create a virtual environment:**
   ```bash
   uv sync
   ```

2. **Activate the virtual environment:**
   - On Linux/macOS:
     ```bash
     source .venv/bin/activate
     ```
   - On Windows (PowerShell):
     ```powershell
     .venv\Scripts\Activate.ps1
     ```

3. **Install Pre-commit hooks:**
   ```bash
   uv run pre-commit install
   ```

4. **Run Code Linting / Formatting:**
   ```bash
   uv run ruff check
   ```

---

### Run using Docker Compose (Recommended)

Running via Docker Compose spins up PostgreSQL, Redis, Mailhog, Adminer, Celery, and the Django app itself.

1. **Build the Docker images:**
   ```bash
   docker compose -f docker-compose-local.yml build
   ```

2. **Start the environment:**
   ```bash
   docker compose -f docker-compose-local.yml up
   ```
   *(Add `-d` at the end to run in detached background mode).*

3. **Accessing Services:**
   * **Django API Backend**: [http://localhost:8001/](http://localhost:8001/)
   * **Django Admin**: [http://localhost:8001/admin/](http://localhost:8001/admin/)
   * **Adminer (Database UI)**: [http://localhost:8000/](http://localhost:8000/)
     * *Server*: `db`
     * *Username / Password*: Defined in `.envs/local/.django`
   * **Mailhog (Captured Emails)**: [http://localhost:8025/](http://localhost:8025/)

4. **Seed Database / Migrations:**
   The `django-entrypoint.sh` script automatically handles the database setup on start:
   * Runs migrations.
   * Loads groups & user permission fixtures (`roles.json`, `group_permissions.json`).
   * Populates geographical data.
   * Auto-creates a superuser with `--noinput`.

---

## 🧪 Testing & Shell Access

To run tests and interact with Django inside the running containers:

* **Run Backend Unit Tests:**
  ```bash
  docker compose -f docker-compose-local.yml exec django python manage.py test
  ```

* **Interactive Django Shell:**
  ```bash
  docker compose -f docker-compose-local.yml exec django python manage.py shell
  ```

* **Inspect Container Logs:**
  ```bash
  docker compose -f docker-compose-local.yml logs -f django
  ```

---

## 🛑 Stopping the Environment

To stop and remove running containers:
```bash
docker compose -f docker-compose-local.yml down
```

To tear down all containers and delete database volumes (resets PostgreSQL database):
```bash
docker compose -f docker-compose-local.yml down -v
```
