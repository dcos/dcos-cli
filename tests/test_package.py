import json

from dcos.api import package


def test_extract_default_values():

    config_schema = json.loads("""
    {
        "type": "object",
        "properties": {
            "foo.bar": {
                "type": "string",
                "description": "A bar name."
            },
            "foo.baz": {
                "type": "integer",
                "description": "How many times to do baz.",
                "minimum": 0,
                "maximum": 16,
                "required": false,
                "default": 4
            }
        }
    }
    """)

    expected = {'foo.baz': 4}

    result, error = package._extract_default_values(config_schema)

    assert error is None
    assert result == expected
