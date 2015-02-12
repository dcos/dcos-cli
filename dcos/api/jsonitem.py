import collections
import json

from dcos.api import errors


def parse_json_item(json_item, schema):
    """Parse the json item based on a schema.

    :param json_item: A JSON item in the form 'key=value'
    :type json_item: str
    :param schema: The JSON schema to use for parsing
    :type schema: dict
    :returns: A tuple for the parsed JSON item
    :rtype: ((str, any), Error) where any is one of str, int, float, bool,
            list or dict
    """

    terms = json_item.split('=', 1)
    if len(terms) != 2:
        return (
            None,
            errors.DefaultError(
                '{!r} is not a valid json-item'.format(json_item))
        )

    # Check that it is a valid key in our jsonschema
    key = terms[0]
    value_type, err = _check_key_with_schema(key, schema)
    if err is not None:
        return (None, err)

    value, err = value_type(terms[1])
    if err is not None:
        return (None, err)

    return ((key, value), None)


def _check_key_with_schema(key, schema):
    """
    :param key: JSON field
    :type key: str
    :param schema: The JSON schema to use
    :type schema: dict
    :returns: A callable capable of parsing a string to its type
    :rtype: (_ValueTypeParser, Error)
    """

    key_schema = schema['properties'].get(key)
    if key_schema is None:
        keys = ', '.join(schema['properties'].keys())
        return (
            None,
            errors.DefaultError(
                'The property {!r} does not conform to the expected format. '
                'Possible values are: {}'.format(key, keys))
        )
    else:
        return (_ValueTypeParser(key_schema['type']), None)


class _ValueTypeParser(object):
    """Callable for parsing a string against a known JSON type.

    :param value_type: The JSON type as a string
    :type value_type: str
    """

    def __init__(self, value_type):
        self._value_type = value_type

    def __call__(self, value):
        """
        :param value: String to try and parse
        :type value: str
        :returns: The parse value
        :rtype: (any, Error) where any is one of str, int, float, bool, list
                or dict
        """

        value = _clean_value(value)

        if self._value_type == 'string':
            return _parse_string(value)
        elif self._value_type == 'object':
            return _parse_object(value)
        elif self._value_type == 'number':
            return _parse_number(value)
        elif self._value_type == 'integer':
            return _parse_integer(value)
        elif self._value_type == 'boolean':
            return _parse_boolean(value)
        elif self._value_type == 'array':
            return _parse_array(value)
        else:
            return (
                None,
                errors.DefaultError(
                    'Unknown type {!r}'.format(self._value_type))
            )


def _clean_value(value):
    """
    :param value: String to try and clean
    :type value: str
    :returns: The cleaned string
    :rtype: str
    """

    if len(value) > 1 and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    elif len(value) > 1 and value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    else:
        return value


def _parse_string(value):
    """
    :param value: The string to parse
    :type value: str
    :returns: The parsed value
    :rtype: str
    """

    if value == 'null':
        return (None, None)
    else:
        return (value, None)


def _parse_object(value):
    """
    :param value: The string to parse
    :type value: str
    :returns: The parsed value
    :rtype: dict
    """

    try:
        json_object = json.loads(value)
        if json_object is None or isinstance(json_object, collections.Mapping):
            return (json_object, None)
        else:
            return (
                None,
                errors.DefaultError(
                    'Unable to parse {!r} as a JSON object'.format(value))
            )
    except ValueError as error:
        msg = 'Unable to parse {!r} as a JSON object: {}'.format(value, error)
        return (None, errors.DefaultError(msg))


def _parse_number(value):
    """
    :param value: The string to parse
    :type value: str
    :returns: The parsed value
    :rtype: float
    """

    try:
        if value == 'null':
            return (None, None)
        else:
            return (float(value), None)
    except ValueError as error:
        msg = 'Unable to parse {!r} as a float: {}'.format(value, error)
        return (None, errors.DefaultError(msg))


def _parse_integer(value):
    """
    :param value: The string to parse
    :type value: str
    :returns: The parsed value
    :rtype: int
    """

    try:
        if value == 'null':
            return (None, None)
        else:
            return (int(value), None)
    except ValueError as error:
        msg = 'Unable to parse {!r} as an int: {}'.format(value, error)
        return (None, errors.DefaultError(msg))


def _parse_boolean(value):
    """
    :param value: The string to parse
    :type value: str
    :returns: The parsed value
    :rtype: bool
    """

    try:
        boolean = json.loads(value)
        if boolean is None or isinstance(boolean, bool):
            return (boolean, None)
        else:
            return (
                None,
                errors.DefaultError(
                    'Unable to parse {!r} as a boolean'.format(value))
            )
    except ValueError as error:
        msg = 'Unable to parse {!r} as a boolean: {}'.format(value, error)
        return (None, errors.DefaultError(msg))


def _parse_array(value):
    """
    :param value: The string to parse
    :type value: str
    :returns: The parsed value
    :rtype: list
    """

    try:
        array = json.loads(value)
        if array is None or isinstance(array, collections.Sequence):
            return (array, None)
        else:
            return (
                None,
                errors.DefaultError(
                    'Unable to parse {!r} as an array'.format(value))
            )
    except ValueError as error:
        msg = 'Unable to parse {!r} as an array: {}'.format(value, error)
        return (None, errors.DefaultError(msg))
