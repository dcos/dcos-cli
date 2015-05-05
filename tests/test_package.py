import collections

from dcos import package

import pytest

MergeData = collections.namedtuple(
    'MergeData',
    ['first', 'second', 'expected'])


@pytest.fixture(params=[
    MergeData(
        first={},
        second={'a': 1},
        expected={'a': 1}),
    MergeData(
        first={'a': 'a'},
        second={'a': 1},
        expected={'a': 1}),
    MergeData(
        first={'b': 'b'},
        second={'a': 1},
        expected={'b': 'b', 'a': 1}),
    MergeData(
        first={'b': 'b'},
        second={},
        expected={'b': 'b'}),
    MergeData(
        first={'b': {'a': 'a'}},
        second={'b': {'c': 'c'}},
        expected={'b': {'c': 'c', 'a': 'a'}}),
    ])
def merge_data(request):
    return request.param


def test_extract_default_values():
    config_schema = {
        "type": "object",
        "properties": {
            "foo": {
                "type": "object",
                "properties": {
                    "bar": {
                        "type": "string",
                        "description": "A bar name."
                    },
                    "baz": {
                        "type": "integer",
                        "description": "How many times to do baz.",
                        "minimum": 0,
                        "maximum": 16,
                        "required": False,
                        "default": 4
                    }
                }
            },
            "fiz": {
                "type": "boolean",
                "default": True,
            },
            "buz": {
                "type": "string"
            }
        }
    }

    expected = {'foo': {'baz': 4}, 'fiz': True}

    result = package._extract_default_values(config_schema)

    assert result == expected


def test_option_merge(merge_data):
    assert merge_data.expected == package._merge_options(
        merge_data.first,
        merge_data.second)
