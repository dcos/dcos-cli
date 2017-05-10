import json
import os
import urllib

from dcos import config
from dcos import emitting
from dcos import http
from dcos import util

from dcoscli import tables

from dcos.errors import DCOSException
from dcos.errors import DCOSHTTPException

emitter = emitting.FlatEmitter()
logger = util.get_logger(__name__)


class DCOSBackupException(DCOSHTTPException):
    def __init__(self, exception):
        self.exception = exception

    def __str__(self):
        try:
            errors = self.exception.response.json()['errors']
        except:
            return str(self.exception)

        string = ""
        for error in errors:
            string += "{}\n".format(error)

        return string.rstrip()


def _get_endpoint_url(endpoint, version=''):
    endpoint_url = 'system/v1/backup/{}/{}'.format(version, endpoint)

    dcos_url = config.get_config_val('core.dcos_url')
    if not dcos_url:
        raise config.missing_config_exception(['core.dcos_url'])

    return urllib.parse.urljoin(dcos_url, endpoint_url)


def save(label):
    url = _get_endpoint_url('save')
    parameters = { "label" : label }
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    try:
        response = http.post(
            url=url,
            data=json.dumps(parameters),
            headers=headers)
    except DCOSHTTPException as exception:
        raise DCOSBackupException(exception)


def restore(backup_id):
    url = _get_endpoint_url('restore')
    parameters = { "id" : backup_id }
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    try:
        response = http.post(
            url=url,
            data=json.dumps(parameters),
            headers=headers)
    except DCOSHTTPException as exception:
        raise DCOSBackupException(exception)


def list(prefix, _json):
    url = _get_endpoint_url('list')
    parameters = { "prefix" : prefix }
    headers = {
        'Accept': 'application/json',
    }

    try:
        data = http.get(
            url=url,
            params=parameters,
            timeout=1)
    except DCOSHTTPException as exception:
        raise DCOSBackupException(exception)

    if _json == True:
        emitter.publish(data.json())
    else:
        emitter.publish(tables.backup_table(data.json()))


def remove(backup_id):
    url = _get_endpoint_url('remove')
    parameters = { "id" : backup_id }
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    try:
        response = http.delete(
            url=url,
            data=json.dumps(parameters),
            headers=headers,
            timeout=1)
    except DCOSHTTPException as exception:
        raise DCOSBackupException(exception)

def download(backup_id, backup_path):
    url = _get_endpoint_url('download')
    parameters = { "id" : backup_id }
    headers = {
        'Accept': 'application/json',
    }

    try:
        data = http.get(
            url=url,
            params=parameters,
            timeout=1)
    except DCOSHTTPException as exception:
        raise DCOSBackupException(exception)

    abspath = os.path.abspath(backup_path)

    if not os.path.exists(os.path.dirname(abspath)):
        raise DCOSException(
            "The dirname for '{}' does not exist".format(backup_path))

    with open(abspath, 'wb') as f:
        f.write(data.content)

def upload(backup_path):
    url = _get_endpoint_url('upload')
    headers = {
        'Content-Type': 'application/octet-stream',
        'Accept': 'application/json',
    }

    abspath = os.path.abspath(backup_path)

    if not os.path.exists(abspath):
        raise DCOSException(
            "The file '{}' does not exist".format(backup_path))

    with open(abspath, 'rb') as f:
        data = f.read()

    try:
        response = http.post(
            url=url,
            data=data,
            headers=headers,
            timeout=1)
    except DCOSHTTPException as exception:
        raise DCOSBackupException(exception)
