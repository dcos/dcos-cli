from dcos import util
from dcos.errors import DCOSException

import pytest


def test_open_file():
    path = 'nonexistant_file_name.txt'
    with pytest.raises(DCOSException) as excinfo:
        with util.open_file(path):
            pass
    assert 'Error opening file [{}]: No such file or directory'.format(path) \
        in str(excinfo.value)
