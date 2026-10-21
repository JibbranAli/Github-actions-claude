"""LW_releaseGuard: a small service that reports whether an application is ready for release."""

import os
import re
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, render_template

APP_NAME = "LW_releaseGuard"
DEFAULT_ENV_NAME = "production"
DEFAULT_APP_VERSION = "1.0.0"

# India Standard Time is a fixed UTC+05:30 with no daylight saving, so a static offset is exact
# and avoids depending on the system tz database (absent from slim container images).
IST = timezone(timedelta(hours=5, minutes=30), name="IST")
IST_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S IST"

# Strict MAJOR.MINOR.PATCH with no pre-release or build suffix (e.g. "1.4.2", not "1.4.2-rc1").
_RELEASE_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

app = Flask(__name__)


def _read_env(name, default):
    """Return the stripped value of an environment variable, or the default if unset or blank."""
    value = os.environ.get(name, "").strip()
    return value or default


def get_release_info():
    """Build the release report from the current environment.

    Values are read on every call so that changes to the environment (and test
    monkeypatching) are reflected without restarting the process.
    """
    env_name = _read_env("ENV_NAME", DEFAULT_ENV_NAME)
    version = _read_env("APP_VERSION", DEFAULT_APP_VERSION)
    return {
        "app_name": APP_NAME,
        "version": version,
        "env": env_name,
        "release_readiness": is_release_ready(version),
    }


def get_release_metadata():
    """Build the release metadata: identity of the running build plus the current time in IST."""
    return {
        "app_name": APP_NAME,
        "version": _read_env("APP_VERSION", DEFAULT_APP_VERSION),
        "env": _read_env("ENV_NAME", DEFAULT_ENV_NAME),
        "timestamp": datetime.now(IST).strftime(IST_TIMESTAMP_FORMAT),
    }


def is_release_ready(version):
    """A build is release-ready when its version is a final semantic version (no pre-release tag)."""
    return bool(_RELEASE_VERSION_PATTERN.match(version))


@app.get("/")
def index():
    return render_template("index.html", release=get_release_info())


@app.get("/health")
def health():
    return jsonify(status="healthy")


@app.get("/release")
def release():
    return jsonify(get_release_info())


@app.get("/release/metadata")
def release_metadata():
    return jsonify(get_release_metadata())


if __name__ == "__main__":
    # Local development only; production runs under gunicorn (see Dockerfile).
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
