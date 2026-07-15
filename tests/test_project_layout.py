from pathlib import Path


def test_project_declares_python_312_or_newer() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'requires-python = ">=3.12"' in pyproject


def test_app_package_exists() -> None:
    assert Path("src/app/__init__.py").is_file()


def test_gitignore_excludes_secrets_and_test_cache() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert ".env" in gitignore
    assert ".pytest_cache/" in gitignore
