import json

import pystache
from jsonschema import validate


class Client(object):
    """Class for talking to the package server."""


class Package(object):
    """Representation of a software package."""


class PackageRegistry(object):
    """Representation of a package registry."""


def render_template(template, params):
    template = True
    params_json = True

    result = pystache.render(template, params_json)
    print("rendered result:")
    print(result)


def load_params_schema(params_schema_path):
    with open(params_schema_path) as params_schema_file:
        params_schema = json.load(params_schema_file)
    return params_schema


def validate_params(params, params_schema):
    for field in params:
        field_value = params[field]
        assert field in params_schema
        field_schema = params_schema[field]
        validate(field_value, field_schema)


def marshal_params(params_schema):
    return True


def marshal_params_from_config():
    return True


def marshal_params_from_stdin():
    return True
