import pytest
from tests.build_fixture import build_fixture


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "test.duckdb"
    build_fixture(path)
    return path
