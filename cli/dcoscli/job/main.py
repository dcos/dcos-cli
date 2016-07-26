import json
import os
import sys

import dcoscli
import docopt
import pkg_resources
import six
from dcos import cmds, config, emitting, http, options, util
from dcos.errors import DCOSException, DCOSHTTPException
from dcoscli import tables
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import decorate_docopt_usage

from six.moves import urllib

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()

DEFAULT_TIMEOUT = 180
METRONOME_EMBEDDED='?embed=activeRuns&embed=schedules&embed=history'

def main(argv):
    try:
        return _main(argv)
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
def _main(argv):
    args = docopt.docopt(
        default_doc("job"),
        argv=argv,
        version='dcos-job version {}'.format(dcoscli.version))

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: all the supported commands
    :rtype: dcos.cmds.Command
    """

    return [

        cmds.Command(
            hierarchy=['job', 'run'],
            arg_keys=['<job-id>'],
            function=_run),

        cmds.Command(
            hierarchy=['job', 'kill'],
            arg_keys=['<job-id>', '<run-id>','--all'],
            function=_kill),

        cmds.Command(
            hierarchy=['job', 'schedule', 'add'],
            arg_keys=['<job-id>', '<schedule-file>'],
            function=_add_schedule),

        cmds.Command(
            hierarchy=['job', 'schedule', 'update'],
            arg_keys=['<job-id>', '<schedule-file>'],
            function=_update_schedules),

        cmds.Command(
            hierarchy=['job', 'schedule', 'show'],
            arg_keys=['<job-id>', '--json'],
            function=_show_schedule),

        cmds.Command(
            hierarchy=['job', 'show', 'runs'],
            arg_keys=['<job-id>', '<run-id>', '--q'],
            function=_show_runs),

        cmds.Command(
            hierarchy=['job', 'schedule', 'remove'],
            arg_keys=['<job-id>', '<schedule-id>'],
            function=_remove_schedule),

        cmds.Command(
            hierarchy=['job', 'list'],
            arg_keys=['--json'],
            function=_list),

        cmds.Command(
            hierarchy=['job', 'history'],
            arg_keys=['<job-id>','--json','--show-failures'],
            function=_history),

        cmds.Command(
            hierarchy=['job', 'remove'],
            arg_keys=['<job-id>','--stopCurrentJobRuns'],
            function=_remove),

        cmds.Command(
            hierarchy=['job', 'add'],
            arg_keys=['<job-file>'],
            function=_add_job),

        cmds.Command(
            hierarchy=['job', 'update'],
            arg_keys=['<job-file>'],
            function=_update_job),

        cmds.Command(
            hierarchy=['job', 'show'],
            arg_keys=['<job-id>'],
            function=_show),

        cmds.Command(
            hierarchy=['job'],
            arg_keys=['--config-schema', '--info'],
            function=_job)
    ]


def _job(config_schema=False, info=False):
    """
    :param config_schema: Whether to output the config schema
    :type config_schema: boolean
    :param info: Whether to output a description of this subcommand
    :type info: boolean
    :returns: process return code
    :rtype: int
    """

    if config_schema:
        schema = _cli_config_schema()
        emitter.publish(schema)
    elif info:
        _info()
    else:
        doc = default_command_info("job")
        emitter.publish(options.make_generic_usage_message(doc))
        return 1

    return 0


def _remove_schedule(job_id, schedule_id):
    """
    :param job_id: Id of the job
    :type job_id: str
    :param schedule_id: Id of the schedule
    :type schedule_id: str
    :returns: process return code
    :rtype: int
    """
    response = None

    try:
     response = _do_request("{}/{}/schedules/{}".format(_get_api_url('v1/jobs'),
        job_id, schedule_id), 'DELETE')
    except DCOSHTTPException as e:
        if e.response.status_code == 404:
            emitter.publish("Schedule or job ID does NOT exist.")
        return 1
    except DCOSException as e:
        emitter.publish("Unable to remove schedule ID '{}' for job ID '{}'".format(schedule_id, job_id))
        return 1

    if response.status_code == 200:
        emitter.publish("Schedule '{}' for job '{}' removed.".format(schedule_id, job_id))
    return 0


def _remove(job_id, stop_current_job_runs=False):
    """
    :param job_id: Id of the job
    :type job_id: str
    :param stop_current_job_runs: If job runs should be stop as part of the remove
    :type stop_current_job_runs: boolean
    :returns: process return code
    :rtype: int
    """
    response = None

    try:
     response = _do_request("{}/{}?stopCurrentJobRuns={}".format(_get_api_url('v1/jobs'),
        job_id, str(stop_current_job_runs).lower()), 'DELETE')
    except DCOSHTTPException as e:
        if(e.response.status_code == 500 and stop_current_job_runs):
            return _remove(job_id, False)
        else:
            emitter.publish("Unable to remove '{}'.  It may be running.".format(job_id))
            return 1
    except DCOSException as e:
        emitter.publish("Unable to remove '{}'.  It may be running.".format(job_id))
        return 1
    else:
        if response.status_code == 200:
            emitter.publish("{} removed.".format(job_id))
    return 0


def _kill(job_id, run_id, all=False):
    """
    :param job_id: Id of the job
    :type job_id: str
    :returns: process return code
    :rtype: int
    """
    response = None
    if (run_id is None and all):
        deadpool = _get_ids(_get_runs(job_id))
    else:
        deadpool = list()
        deadpool.append(run_id)

    for dead in deadpool:
        try:
            response = _do_request("{}/{}/runs/{}/actions/stop".format(_get_api_url('v1/jobs'),
                job_id, dead), 'POST')
        except DCOSHTTPException as e:
            if e.response.status_code == 404:
                emitter.publish("Job ID or Run ID does NOT exist.")
            return 1
        except DCOSException as e:
            emitter.publish("Unable stop run ID '{}' for job ID '{}'".format(dead, job_id))
            return 1

        if response.status_code == 200:
            emitter.publish("Run '{}' for job '{}' killed.".format(dead, job_id))
    return 0


def _list(json_flag=False):
    """
    :returns: process return code
    :rtype: int
    """
    response = None
    url = _get_api_url('v1/jobs' + METRONOME_EMBEDDED)
    try:
     response = _do_request(url, 'GET')
    except DCOSException as e:
        return 1

    json = _read_http_response_body(response)

    if json_flag:
        emitter.publish(json)
    else:
        table = tables.job_table(json)
        output = six.text_type(table)
        if output:
            emitter.publish(output)

    return 0


def _history(job_id, json_flag=False, show_failures=False):
    """
    :returns: process return code
    :rtype: int
    """
    response = None
    url = _get_api_url('v1/jobs/' + job_id + METRONOME_EMBEDDED)
    try:
     response = _do_request(url, 'GET')
    except DCOSException as e:
        return 1

    json = _read_http_response_body(response)

    if json_flag:
        emitter.publish(json)
    else:
        emitter.publish("'{}'  Successful runs: {} Last Success: {}".format(job_id, json['history']['successCount'], json['history']['lastSuccessAt']))
        table = tables.job_history_table(json['history']['successfulFinishedRuns'])
        output = six.text_type(table)
        if output:
            emitter.publish(output)

        if show_failures:
            emitter.publish("'{}'  Failure runs: {} Last Failure: {}".format(job_id, json['history']['failureCount'], json['history']['lastFailureAt']))
            table = tables.job_history_table(json['history']['failedFinishedRuns'])
            output = six.text_type(table)
            if output:
                emitter.publish(output)

    return 0


def _show(job_id):
    """
    :param job_id: Id of the job
    :type job_id: str
    :returns: process return code
    :rtype: int
    """

    response = None
    try:
     response = _do_request("{}/{}".format(_get_api_url('v1/jobs'), job_id), 'GET')
    except DCOSException as e:
        return 1

    json = _read_http_response_body(response)
    emitter.publish(json)

    return 0

def _show_runs(job_id, run_id=None, q=False):
    """
    :param job_id: Id of the job
    :type job_id: str
    :returns: process return code
    :rtype: int
    """

    json = _get_runs(job_id, run_id)
    if not q:
        emitter.publish(job_id)
        emitter.publish(json)
    else:
        emitter.publish(_get_ids(json))

    return 0


def _get_runs(job_id, run_id=None):
    """
    :param job_id: Id of the job
    :type job_id: str
    :returns: json of all running instance of a job_id
    :rtype: json
    """

    response = None
    url = "{}/{}/runs".format(_get_api_url('v1/jobs'), job_id)
    if run_id is not None:
        url = "{}/{}/runs/{}".format(_get_api_url('v1/jobs'), job_id, run_id)
    try:
     response = _do_request(url,'GET')
    except DCOSException as e:
        return 1

    json = _read_http_response_body(response)

    return json

def _run(job_id):
    """
    :param job_id: Id of the job
    :type job_id: str
    :returns: process return code
    :rtype: int
    """

    timeout = _get_timeout()
    url = "{}/{}/runs".format(_get_api_url('v1/jobs'), job_id)

    try:
        response = http.post(url, timeout=timeout)
    except DCOSHTTPException as e:
        if(e.response.status_code == 404):
            emitter.publish("Job ID: '{}' does not exist.".format(job_id))
        else:
            emitter.publish("Error running job: '{}'".format(job_id))

    return 0


def _show_schedule(job_id, json_flag=False):
    """
    :param job_id: Id of the job
    :type job_id: str
    :returns: process return code
    :rtype: int
    """

    response = None
    url = "{}/{}/schedules".format(_get_api_url('v1/jobs'), job_id)
    try:
     response = _do_request(url, 'GET')
    except DCOSException as e:
        return 1

    json = _read_http_response_body(response)
    if json_flag:
        emitter.publish(json)
    else:
        table = tables.schedule_table(json)
        output = six.text_type(table)
        if output:
            emitter.publish(output)

    return 0


def _add_schedules(job_id, schedules_json):
    """
    :param job_id: Id of the job
    :type job_id: str
    :param schedules_json: json for the schedules
    :type schedules_json: json
    :returns: process return code
    :rtype: int
    """

    if schedules_json is None:
        return 1

    for schedule in schedules_json:
        try:
            response = _post_schedule(job_id, schedule)
            emitter.publish("Schedule ID `{}` for job ID `{}` added".format(schedule['id'],job_id))
        except DCOSHTTPException as e:
            if e.response.status_code == 404:
                emitter.publish("Job ID: '{}' does NOT exist.".format(job_id))
            elif e.response.status_code == 409:
                emitter.publish("Schedule already exists.")
            else:
                return 1
        except DCOSException as e:
            return 1

    return 0


def _update_schedules(job_id, schedules_file):
    """
    :param job_id: Id of the job
    :type job_id: str
    :param schedule_id: Id of the schedule
    :type schedule_id: str
    :param schedule_file: filename for the schedule resource
    :type schedule_file: str
    :returns: process return code
    :rtype: int
    """
    schedules = _get_resource(schedules_file)
    schedule = schedules[0]  # 1 update
    schedule_id = schedule['id']

    return _update_schedule(job_id, schedule_id, schedule)


def _update_schedule(job_id, schedule_id, schedule_json):
    """
    :param job_id: Id of the job
    :type job_id: str
    :param schedule_id: Id of the schedule
    :type schedule_id: str
    :param schedules_json: json for the schedules
    :type schedules_json: json
    :returns: process return code
    :rtype: int
    """

    if schedule_json is None:
        return 1

    try:
        response = _put_schedule(job_id, schedule_id, schedule_json)
        emitter.publish("Schedule ID `{}` for job ID `{}` updated.".format(schedule_id, job_id))
    except DCOSException as e:
        emitter.publish(e)
        return 1

    return 0


def _add_schedule(job_id, schedule_file):
    """
    :param job_id: Id of the job
    :type job_id: str
    :param schedule_file: filename for the schedule resource
    :type schedule_file: str
    :returns: process return code
    :rtype: int
    """

    schedules = _get_resource(schedule_file)
    return _add_schedules(job_id, schedules)


def _add_job(job_file):
    """
    :param job_file: optional filename for the application resource
    :type job_file: str
    :returns: process return code
    :rtype: int
    """

    full_json = _get_resource(job_file)
    if full_json is None:
        return 1

    job_id = full_json['id']
    schedules = None

    if 'schedules' in full_json:
        schedules = full_json['schedules']
        del full_json['schedules']

    # iterate and post each schedule
    job_added = False
    try:
        response = _post_job(full_json)
        job_added = True
        emitter.publish("Job ID: '{}' added.".format(job_id))
    except DCOSHTTPException as e:
        if(e.response.status_code == 409):
            emitter.publish("Job ID: '{}' already exists".format(job_id))
        else:
            emitter.publish("Error running job: '{}'".format(job_id))

    if (schedules is not None and job_added):
        return _add_schedules(job_id, schedules)

    return 0


def _update_job(job_file):
    """
    :param job_file: filename for the application resource
    :type job_file: str
    :returns: process return code
    :rtype: int
    """
    # only updates the job (does NOT update schedules)
    full_json = _get_resource(job_file)
    if full_json is None:
        return 1

    job_id = full_json['id']
    schedules = None

    if 'schedules' in full_json:
        schedules = full_json['schedules']
        del full_json['schedules']

    job_added = False
    try:
        response = _put_job(job_id, full_json)
        job_added = True
        emitter.publish("Job ID: '{}' updated.".format(job_id))
    except DCOSHTTPException as e:
        emitter.publish("Error updating job: '{}'".format(job_id))

    return 0


def _info():
    """
    :returns: process return code
    :rtype: int
    """

    emitter.publish(default_command_info("job"))
    return 0


def _cli_config_schema():
    """
    :returns: schema for metronome cli config
    :rtype: dict
    """
    return json.loads(
        pkg_resources.resource_string(
            'dcoscli',
            'data/config-schema/job.json').decode('utf-8'))


def _post_job(job_json):
    """
    :param job_json: json object representing a job
    :type job_file: json
    :returns: response json
    :rtype: json
    """

    timeout = _get_timeout()
    url = _get_api_url('v1/jobs')

    response = http.post(url,
                         json=job_json,
                         timeout=timeout)

    return response.json()


def _put_job(job_id, job_json):
    """
    :param job_id: Id of the job
    :type job_id: str
    :param job_json: json object representing a job
    :type job_file: json
    :returns: response json
    :rtype: json
    """

    timeout = _get_timeout()
    url = "{}/{}".format(_get_api_url('v1/jobs'), job_id)

    response = http.put(url,
                         json=job_json,
                         timeout=timeout)

    return response.json()


def _put_schedule(job_id, schedule_id, schedule_json):
    """
    :param job_id: Id of the job
    :type job_id: str
    :param schedule_id: Id of the schedule
    :type schedule_id: str
    :param schedule_json: json object representing a job
    :type schedule_json: json
    :returns: response json
    :rtype: json
    """

    timeout = _get_timeout()
    url = "{}/{}/schedules/{}".format(_get_api_url('v1/jobs'), job_id, schedule_id)

    response = http.put(url,
                         json=schedule_json,
                         timeout=timeout)

    return response.json()


def _post_schedule(job_id, schedule_json):
    """
    :param job_id: id of the job
    :type job_id: str
    :param schedule_json: json object representing a schedule
    :type schedule_json: json
    :returns: response json
    :rtype: json
    """

    timeout = _get_timeout()
    url = "{}/{}/schedules".format(_get_api_url('v1/jobs'), job_id)

    response = http.post(url,
                         json=schedule_json,
                         timeout=timeout)

    return response.json()


def _do_request(url, method, timeout=None, stream=False, **kwargs):
    """
    make HTTP request

    :param url: url
    :type url: string
    :param method: HTTP method, GET or POST
    :type  method: string
    :param timeout: HTTP request timeout, default 3 seconds
    :type  timeout: integer
    :param stream: stream parameter for requests lib
    :type  stream: bool
    :return: http response
    :rtype: requests.Response
    """

    def _is_success(status_code):
        # consider 400 and 503 to be successful status codes.
        # API will return the error message.
        if status_code in [200, 400, 503]:
            return True
        return False

    if timeout is None:
        timeout = _get_timeout()

    url = urllib.parse.urljoin(_get_metronome_url(), url)
    if method.lower() == 'get':
        http_response = http.get(url, is_success=_is_success, timeout=timeout, **kwargs)
    elif method.lower() == 'post':
        http_response = http.post(url, is_success=_is_success, timeout=timeout, stream=stream, **kwargs)
    elif method.lower() == 'delete':
        http_response = http.delete(url, is_success=_is_success, timeout=timeout, stream=stream, **kwargs)
    else:
        raise DCOSException('Unsupported HTTP method: ' + method)
    return http_response


def _read_http_response_body(http_response):
    """
    Get an requests HTTP response, read it and deserialize to json.

    :param http_response: http response
    :type http_response: requests.Response onject
    :return: deserialized json
    :rtype: dict
    """

    data = b''
    try:
        for chunk in http_response.iter_content(1024):
            data += chunk
        bundle_response = util.load_jsons(data.decode('utf-8'))
        return bundle_response
    except DCOSException:
        raise


def _get_ids(json):
    """
    :param json: json array of elements with ids
    :type json: json
    :returns: set of ids
    :rtype: set
    """
    ids = list()
    for element in json:
        ids.append(element['id'])

    return ids


def _get_resource(resource):
    """
    :param resource: optional filename or http(s) url
    for the application or group resource
    :type resource: str
    :returns: resource
    :rtype: dict
    """
    if resource is not None:
        if os.path.isfile(resource):
            with util.open_file(resource) as resource_file:
                return util.load_json(resource_file)
        else:
            try:
                http.silence_requests_warnings()
                req = http.get(resource)
                if req.status_code == 200:
                    data = b''
                    for chunk in req.iter_content(1024):
                        data += chunk
                    return util.load_jsons(data.decode('utf-8'))
                else:
                    raise Exception
            except Exception:
                logger.exception('Cannot read from resource %s', resource)
                raise DCOSException(
                    "Can't read from resource: {0}.\n"
                    "Please check that it exists.".format(resource))

    # Check that stdin is not tty
    if sys.stdin.isatty():
        # We don't support TTY right now. In the future we will start an
        # editor
        raise DCOSException(
            "We currently don't support reading from the TTY. Please "
            "specify an application JSON.\n"
            "E.g.: dcos job add < app_resource.json")

    return util.load_json(sys.stdin)


def _get_metronome_url(toml_config=None):
    """
    :param toml_config: configuration dictionary
    :type toml_config: config.Toml
    :returns: metronome base url
    :rtype: str
    """
    if toml_config is None:
        toml_config = config.get_config()

    metronome_url = config.get_config_val('metronome.url', toml_config)
    if metronome_url is None:
        dcos_url = config.get_config_val('core.dcos_url', toml_config)
        if dcos_url is None:
            raise config.missing_config_exception(['core.dcos_url'])
        metronome_url = urllib.parse.urljoin(dcos_url, 'service/metronome/')

    return metronome_url


def _get_api_url(path):
    """
    :param path: service path
    :type path: str
    :returns: metronome base url
    :rtype: str
    """

    return urllib.parse.urljoin(_get_metronome_url(), path)


def _get_timeout():
    """
    :returns: timout value for API calls
    :rtype: str
    """

    # if timeout is not passed, try to read `core.timeout`
    # if `core.timeout` is not set, default to 3 min.
    timeout = config.get_config_val('core.timeout')
    if not timeout:
        timeout = DEFAULT_TIMEOUT

    return timeout
