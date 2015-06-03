from dcoscli.marathon.main import _app_table
from dcoscli.task.main import _task_table

from ..fixtures.app import app_fixture
from ..fixtures.task import task_fixture


def test_task_table():
    table = _task_table([task_fixture()])
    with open('tests/unit/data/task.txt') as f:
        assert str(table) == f.read()


def test_app_table():
    table = _app_table([app_fixture()])
    with open('tests/unit/data/app.txt') as f:
        assert str(table) == f.read()
