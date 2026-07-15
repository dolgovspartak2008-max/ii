from pathlib import Path


def test_compose_declares_required_services() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    for service in ("app:", "postgres:", "redis:"):
        assert service in compose


def test_dockerignore_excludes_environment_file() -> None:
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8")

    assert ".env" in dockerignore
