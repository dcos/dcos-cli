from dcos import util
from dcos.errors import DCOSException

import pytest


def test_render_mustache_json():
    # x's value expands to a JSON array
    # y's value expands to a JSON object
    # z's value expands to a JSON string
    template = '{ "x": {{{xs}}}, "y": {{{ys}}}, "z": "{{{z}}}"}'
    xs = [1, 2, 3]
    ys = {'y1': 1, 'y2': 2}
    z = 'abc'
    data = {'xs': xs, 'ys': ys, 'z': z}
    result = util.render_mustache_json(template, data)

    assert type(result) is dict
    assert result.get('x') == xs
    assert result.get('y') == ys
    assert result.get('z') == z


def test_open_file():
    path = 'nonexistant_file_name.txt'
    with pytest.raises(DCOSException) as excinfo:
        with util.open_file(path):
            pass
    assert 'Error opening file [{}]: No such file or directory'.format(path) \
        in str(excinfo.value)
