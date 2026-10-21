import pytest

from app import DEFAULT_APP_VERSION, DEFAULT_ENV_NAME, app


@pytest.fixture
def client(monkeypatch):
    # Start every test from a known state, regardless of the caller's shell environment.
    monkeypatch.delenv("ENV_NAME", raising=False)
    monkeypatch.delenv("APP_VERSION", raising=False)
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


# --- GET / ---------------------------------------------------------------


def test_index_returns_html_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    body = response.get_data(as_text=True)
    assert "<title>LW_releaseGuard</title>" in body
    assert "/health" in body
    assert "/release" in body


def test_index_shows_defaults_when_env_missing(client):
    body = client.get("/").get_data(as_text=True)
    assert DEFAULT_APP_VERSION in body
    assert DEFAULT_ENV_NAME in body
    assert "Ready for release" in body


def test_index_shows_configured_values(client, monkeypatch):
    monkeypatch.setenv("ENV_NAME", "staging")
    monkeypatch.setenv("APP_VERSION", "3.2.1")
    body = client.get("/").get_data(as_text=True)
    assert "staging" in body
    assert "3.2.1" in body


def test_index_shows_blocked_status_for_prerelease(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "3.2.1-rc1")
    body = client.get("/").get_data(as_text=True)
    assert "Not ready for release" in body


def test_index_escapes_environment_values(client, monkeypatch):
    monkeypatch.setenv("ENV_NAME", "<script>alert(1)</script>")
    body = client.get("/").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;" in body


# --- GET /health ---------------------------------------------------------


def test_health_returns_healthy(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {"status": "healthy"}


def test_health_is_independent_of_env_vars(client, monkeypatch):
    monkeypatch.setenv("ENV_NAME", "staging")
    monkeypatch.setenv("APP_VERSION", "not-a-version")
    assert client.get("/health").get_json() == {"status": "healthy"}


def test_health_rejects_post(client):
    assert client.post("/health").status_code == 405


# --- GET /release --------------------------------------------------------


def test_release_uses_defaults_when_env_missing(client):
    response = client.get("/release")
    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {
        "app_name": "LW_releaseGuard",
        "version": "1.0.0",
        "env": "production",
        "release_readiness": True,
    }


def test_release_uses_env_vars_when_present(client, monkeypatch):
    monkeypatch.setenv("ENV_NAME", "staging")
    monkeypatch.setenv("APP_VERSION", "2.5.0")
    assert client.get("/release").get_json() == {
        "app_name": "LW_releaseGuard",
        "version": "2.5.0",
        "env": "staging",
        "release_readiness": True,
    }


def test_release_with_only_env_name_set(client, monkeypatch):
    monkeypatch.setenv("ENV_NAME", "qa")
    data = client.get("/release").get_json()
    assert data["env"] == "qa"
    assert data["version"] == DEFAULT_APP_VERSION


def test_release_with_only_app_version_set(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "4.0.0")
    data = client.get("/release").get_json()
    assert data["version"] == "4.0.0"
    assert data["env"] == DEFAULT_ENV_NAME


@pytest.mark.parametrize("value", ["", "   "])
def test_release_falls_back_to_defaults_for_blank_values(client, monkeypatch, value):
    monkeypatch.setenv("ENV_NAME", value)
    monkeypatch.setenv("APP_VERSION", value)
    data = client.get("/release").get_json()
    assert data["env"] == DEFAULT_ENV_NAME
    assert data["version"] == DEFAULT_APP_VERSION


def test_release_strips_surrounding_whitespace(client, monkeypatch):
    monkeypatch.setenv("ENV_NAME", "  staging  ")
    monkeypatch.setenv("APP_VERSION", " 1.2.3 ")
    data = client.get("/release").get_json()
    assert data["env"] == "staging"
    assert data["version"] == "1.2.3"
    assert data["release_readiness"] is True


@pytest.mark.parametrize("version", ["1.0.0", "0.1.0", "10.20.30"])
def test_release_ready_for_final_versions(client, monkeypatch, version):
    monkeypatch.setenv("APP_VERSION", version)
    assert client.get("/release").get_json()["release_readiness"] is True


@pytest.mark.parametrize(
    "version",
    ["1.0.0-rc1", "2.0.0-beta.1", "1.0.0+build.5", "1.0", "v1.0.0", "01.0.0", "latest"],
)
def test_release_not_ready_for_prerelease_or_invalid_versions(client, monkeypatch, version):
    monkeypatch.setenv("APP_VERSION", version)
    data = client.get("/release").get_json()
    assert data["version"] == version
    assert data["release_readiness"] is False


def test_release_readiness_is_boolean(client):
    assert isinstance(client.get("/release").get_json()["release_readiness"], bool)


# --- Misc ----------------------------------------------------------------


def test_unknown_route_returns_404(client):
    assert client.get("/does-not-exist").status_code == 404
