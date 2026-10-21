# LW_releaseGuard

LW_releaseGuard is a small Flask microservice that tells DevOps teams whether an application build is ready for release. It reports the application name, version and target environment, and flags the build as release-ready only when its version is a final semantic version.

## Endpoints

| Method | Path       | Response |
|--------|------------|----------|
| GET    | `/`        | HTML dashboard describing the service and the current release status |
| GET    | `/health`  | `{"status": "healthy"}` |
| GET    | `/release` | `{"app_name": "LW_releaseGuard", "version": "1.0.0", "env": "production", "release_readiness": true}` |
| GET    | `/release/metadata` | `{"app_name": "LW_releaseGuard", "version": "1.0.0", "env": "production", "timestamp": "2026-10-21 14:05:09 IST"}` |

### Release readiness rule

`release_readiness` is `true` when `APP_VERSION` is a final semantic version of the form `MAJOR.MINOR.PATCH` (for example `2.3.1`). Pre-release, build-tagged or malformed versions such as `2.3.1-rc1`, `2.3.1+build.7`, `v2.3.1`, `2.3` or `latest` are reported as not ready.

### `GET /release/metadata`

Returns metadata about the running build together with the server's current time in India Standard Time. Use it to stamp deployment logs, release notes or audit records, or to confirm which version is live in an environment and when it was checked.

**Request**

No parameters, request body or headers are required.

```bash
curl http://localhost:5000/release/metadata
```

**Response** (`200 OK`, `Content-Type: application/json`)

```json
{
  "app_name": "LW_releaseGuard",
  "version": "1.0.0",
  "env": "production",
  "timestamp": "2026-10-21 14:05:09 IST"
}
```

| Field       | Type   | Description |
|-------------|--------|-------------|
| `app_name`  | string | Always `LW_releaseGuard` |
| `version`   | string | Value of `APP_VERSION` (default `1.0.0`) |
| `env`       | string | Value of `ENV_NAME` (default `production`) |
| `timestamp` | string | Time the request was served, in IST (UTC+05:30), formatted `YYYY-MM-DD HH:MM:SS IST` |

The timestamp is computed with a fixed UTC+05:30 offset from Python's standard library, so it is correct regardless of the host or container time zone and needs no extra dependencies. Unlike `/release`, this endpoint does not report `release_readiness`. Other methods such as `POST` return `405 Method Not Allowed`.

## Configuration

| Variable      | Default      | Description |
|---------------|--------------|-------------|
| `ENV_NAME`    | `production` | Name of the target environment |
| `APP_VERSION` | `1.0.0`      | Version of the application being released |

Blank or whitespace-only values fall back to the defaults.

## Project layout

```
.
├── app.py                    # Flask application
├── templates/index.html      # Dashboard served at /
├── test_app.py               # Pytest suite
├── requirements.txt          # Runtime and dev/test dependencies
├── Dockerfile                # Multi-stage, non-root production image
├── .dockerignore
├── .gitignore
└── .github/workflows/ci.yml  # GitHub Actions pipeline
```

## Install

Requires Python 3.11 or newer.

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run locally

Development server:

```bash
python app.py
# or with custom values
ENV_NAME=staging APP_VERSION=2.0.0-rc1 python app.py
```

Production-style server with gunicorn:

```bash
gunicorn --bind 0.0.0.0:5000 --workers 2 app:app
```

Then check it:

```bash
curl http://localhost:5000/health
curl http://localhost:5000/release
curl http://localhost:5000/release/metadata
```

Open http://localhost:5000/ in a browser for the dashboard.

## Run tests

```bash
pytest -v
```

## Scan dependencies for vulnerabilities

```bash
pip-audit -r requirements.txt
```

## Docker

Build the image:

```bash
docker build -t lw-releaseguard .
```

Run it:

```bash
docker run --rm -p 5000:5000 lw-releaseguard

# override the environment and version
docker run --rm -p 5000:5000 -e ENV_NAME=staging -e APP_VERSION=2.1.0 lw-releaseguard
```

The image is built in two stages: dependencies are installed into a virtual environment in a builder stage, and only that environment plus the application code are copied into a clean `python:3.11-slim` runtime stage. The container runs gunicorn as an unprivileged `app` user (UID 10001) and defines a `HEALTHCHECK` against `/health`.

## Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request targeting `main`. It:

1. Sets up Python 3.11, upgrades pip and installs `requirements.txt`.
2. Runs the test suite with `pytest`.
3. Scans dependencies with `pip-audit`.
4. Builds the Docker image without pushing it to any registry.

Each step runs with `bash -euo pipefail`, so any failing check stops the job and fails the build. The workflow has read-only repository permissions, does not persist the checkout token, and uses no secrets.
