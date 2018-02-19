import pytest

from dcos import jsonitem
from dcos.errors import DCOSException


@pytest.fixture(params=range(6))
def bad_object(request):
    return [
        '{"key":value}',
        'this is a string',
        '4.5',
        '4',
        'true',
        '[1,2,3]',
    ][request.param]


@pytest.fixture(params=range(4))
def bad_number(request):
    return [
        'this is a string',
        'true',
        '{"key":"value"}',
        '[1,2,3]',
    ][request.param]


@pytest.fixture(params=range(5))
def bad_integer(request):
    return [
        'this is a string',
        'true',
        '{"key":"value"}',
        '45.0',
        '[1,2,3]',
    ][request.param]


@pytest.fixture(params=range(5))
def bad_boolean(request):
    return [
        'this is a string',
        '45',
        '{"key":"value"}',
        '45.0',
        '[1,2,3]',
    ][request.param]


@pytest.fixture(params=range(6))
def bad_array(request):
    return [
        'this is a string',
        '45',
        '{"key":"value"}',
        '45.0',
        'true',
        '[1,2,3',
    ][request.param]


@pytest.fixture(params=[
    ('string', 'this is a string', 'this is a string'),
    ('string', 'null', None),
    ('object', '{"key":"value"}', {'key': 'value'}),
    ('object', 'null', None),
    ('number', '4.2', 4.2),
    ('number', 'null', None),
    ('integer', '42', 42),
    ('integer', 'null', None),
    ('boolean', 'true', True),
    ('boolean', 'True', True),
    ('boolean', 'FaLsE', False),
    ('boolean', 'false', False),
    ('boolean', 'null', None),
    ('array', '[1,2,3]', [1, 2, 3]),
    ('array', 'null', None),
    ('url', 'http://test.com', 'http://test.com')
    ])
def jsonitem_tuple(request):
    return request.param


@pytest.fixture(params=range(13))
def parse_tuple(request):
    return [
        ('string=null', ('"string"', None)),
        ('string="this is a string with ="',
         ('"string"', 'this is a string with =')),
        ("string='this is a string with ='",
         ('"string"', 'this is a string with =')),
        ('object=null', ('"object"', None)),
        ("""object='{"key":"value"}'""", ('"object"', {'key': 'value'})),
        ('number=null', ('"number"', None)),
        ('number=4.2', ('"number"', 4.2)),
        ('integer=null', ('"integer"', None)),
        ('integer=42', ('"integer"', 42)),
        ('boolean=null', ('"boolean"', None)),
        ('boolean=true', ('"boolean"', True)),
        ('array=null', ('"array"', None)),
        ("array='[1,2,3]'", ('"array"', [1, 2, 3])),
    ][request.param]


@pytest.fixture(params=range(6))
def bad_parse(request):
    return [
        "====",
        "no equals",
        "object=[]",
        "something=cool",
        "integer=",
        "integer=45.0",
    ][request.param]


@pytest.fixture
def schema():
    return {
        'type': 'object',
        'properties': {
            'integer': {
                'type': 'integer'
            },
            'number': {
                'type': 'number'
            },
            'string': {
                'type': 'string',
            },
            'object': {
                'type': 'object'
            },
            'array': {
                'type': 'array'

            },
            'boolean': {
                'type': 'boolean',
            },
            'url': {
                'type': 'string',
                'format': 'url',

            }
        }
    }


def test_parse_string():
    string = 'this is a string "'
    assert jsonitem._parse_string(string) == string


def test_parse_object():
    assert jsonitem._parse_object('{"key": "value"}') == {'key': 'value'}


def test_parse_invalid_objects(bad_object):
    with pytest.raises(DCOSException):
        jsonitem._parse_object(bad_object)


def test_parse_number():
    assert jsonitem._parse_number('45') == 45
    assert jsonitem._parse_number('45.0') == 45.0


def test_parse_invalid_numbers(bad_number):
    with pytest.raises(DCOSException):
        jsonitem._parse_number(bad_number)


def test_parse_integer():
    assert jsonitem._parse_integer('45') == 45


def test_parse_invalid_integers(bad_integer):
    with pytest.raises(DCOSException):
        jsonitem._parse_integer(bad_integer)


def test_parse_boolean():
    assert jsonitem._parse_boolean('true') is True
    assert jsonitem._parse_boolean('false') is False


def test_parse_invalid_booleans(bad_boolean):
    with pytest.raises(DCOSException):
        jsonitem._parse_boolean(bad_boolean)


def test_parse_array():
    assert jsonitem._parse_array('[1,2,3]') == [1, 2, 3]


def test_parse_invalid_arrays(bad_array):
    with pytest.raises(DCOSException):
        jsonitem._parse_array(bad_array)


def test_parse_url():
    assert jsonitem._parse_url('http://test.com:12') == 'http://test.com:12'


def test_find_parser(schema, jsonitem_tuple):
    key, string_value, value = jsonitem_tuple
    assert jsonitem.find_parser(key, schema)(string_value) == value


def test_parse_json_item(schema, parse_tuple):
    arg, result = parse_tuple
    assert jsonitem.parse_json_item(arg, schema) == result


def test_parse_bad_json_item(schema, bad_parse):
    with pytest.raises(DCOSException):
        jsonitem.parse_json_item(bad_parse, schema)
