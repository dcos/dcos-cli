from dcos.api import util


def test_render_mustache_json():
    # x's value expands to a JSON array
    # y's value expands to a JSON object
    # z's value expands to a JSON string
    template = '{ "x": {{{xs}}}, "y": {{{ys}}}, "z": "{{{z}}}"}'
    xs = [1, 2, 3]
    ys = {'y1': 1, 'y2': 2}
    z = 'abc'
    data = {'xs': xs, 'ys': ys, 'z': z}
    result, error = util.render_mustache_json(template, data)

    assert error is None
    assert type(result) is dict
    assert result.get('x') == xs
    assert result.get('y') == ys
    assert result.get('z') == z
