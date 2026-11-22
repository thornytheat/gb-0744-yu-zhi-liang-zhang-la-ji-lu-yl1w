import pytest
from app.config import BASE
from app.main import create_app
from app.modules.m7_runs.service import calculate


@pytest.fixture(scope="session")
def yard():
    return (BASE / "sample_data" / "yard.json").read_bytes()


@pytest.fixture(scope="session")
def checked():
    return (BASE / "sample_data" / "checked.json").read_bytes()


@pytest.fixture(scope="session")
def report(yard):
    return calculate(yard)


@pytest.fixture(scope="session")
def check(checked):
    return calculate(checked)


@pytest.fixture
def client(tmp_path):
    return create_app({"TESTING": True, "DATABASE": tmp_path / "runs.sqlite"}).test_client()
