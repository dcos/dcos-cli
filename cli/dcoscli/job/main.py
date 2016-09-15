import json
import os
import sys

import docopt
import pkg_resources
import six
from six.moves import urllib

import dcoscli
from dcos import cmds, config, cosmospackage, emitting, http, options, util
from dcos.errors import DCOSException, DCOSHTTPException
from dcoscli import tables
from dcoscli.package.main import get_cosmos_url
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import decorate_docopt_usage


logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()

DEFAULT_TIMEOUT = 180
METRONOME_EMBEDDED = '?embed=activeRuns&embed=schedules&embed=history'


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


def _check_capability():
    """
    The function checks if cluster has metronome capability.

    :raises: DCOSException if cluster does not have metronome capability
    """

    cosmos = cosmospackage.Cosmos(get_cosmos_url())
    if not cosmos.has_capability('METRONOME'):
        raise DCOSException(
            'DC/OS backend does not support metronome capabilities in this '
            'version. Must be DC/OS >= 1.8')


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
            arg_keys=['<job-id>', '<run-id>', '--all'],
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
            arg_keys=['<job-id>', '<run-id>', '--json', '--q'],
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
            arg_keys=['<job-id>', '--json', '--show-failures'],
            function=_history),

        cmds.Command(
            hierarchy=['job', 'remove'],
            arg_keys=['<job-id>', '--stop-current-job-runs'],
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
        raise DCOSException(options.make_generic_usage_message(doc))

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

    try:
        _do_request("{}/{}/schedules/{}".format(_get_api_url('v1/jobs'),
                    job_id, schedule_id), 'DELETE')
    except DCOSHTTPException as e:
        if e.response.status_code == 404:
            raise DCOSException("Schedule or job ID does NOT exist.")
    except DCOSException as e:
        raise DCOSException("Unable to remove schedule ID '{}' for job ID '{}'"
                            .format(schedule_id, job_id))

    return 0


def _remove(job_id, stop_current_job_runs=False):
    """
    :param job_id: Id of the job
    :type job_id: str
    :param stop_current_job_runs: If job runs should be stop as
    part of the remove
    :type stop_current_job_runs: boolean
    :returns: process return code
    :rtype: int
    """

    try:
        _do_request("{}/{}?stopCurrentJobRuns={}"
                    .format(_get_api_url('v1/jobs'),
                            job_id,
                            str(stop_current_job_runs).lower()),
                    'DELETE')
    except DCOSHTTPException as e:
        if e.response.status_code == 500 and stop_current_job_runs:
            return _remove(job_id, False)
        else:
            raise DCOSException("Unable to remove '{}'.  It may be running."
                                .format(job_id))
    except DCOSException as e:
        raise DCOSException("Unable to remove '{}'.  It may be running."
                            .format(job_id))

    return 0


def _kill(job_id, run_id, all=False):
    """
    :param job_id: Id of the job
    :type job_id: str
    :returns: process return code
    :rtype: int
    """
    response = None
    deadpool = []
    if run_id is None and all is True:
        deadpool = _get_ids(_get_runs(job_id))
    else:
        deadpool.append(run_id)

    for dead in deadpool:
        try:
            response = _do_request("{}/{}/runs/{}/actions/stop".format(
                                    _get_api_url('v1/jobs'),
                                    job_id, dead), 'POST')
        except DCOSHTTPException as e:
            if e.response.status_code == 404:
                raise DCOSException("Job ID or Run ID does NOT exist.")
        except DCOSException as e:
            raise DCOSException("Unable stop run ID '{}' for job ID '{}'"
                                .format(dead, job_id))
        else:
            if response.status_code == 200:
                emitter.publish("Run '{}' for job '{}' killed."
                                .format(dead, job_id))
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
        raise DCOSException(e)

    json_list = _read_http_response_body(response)

    if json_flag:
        emitter.publish(json_list)
    else:
        table = tables.job_table(json_list)
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
    url = urllib.parse.urljoin(_get_api_url('v1/jobs/'),
                               job_id + METRONOME_EMBEDDED)
    try:
        response = _do_request(url, 'GET')
    except DCOSHTTPException as e:
        raise DCOSException("Job ID does NOT exist.")
    except DCOSException as e:
        raise DCOSException(e)
    else:

        if response.status_code is not 200:
            raise DCOSException("Job ID does NOT exist.")

        json_history = _read_http_response_body(response)

        if 'history' not in json_history:
            return 0

        if json_flag:
            emitter.publish(json_history)
        else:
            emitter.publish(_get_history_message(json_history, job_id))
            table = tables.job_history_table(
                json_history['history']['successfulFinishedRuns'])
            output = six.text_type(table)
            if output:
                emitter.publish(output)

            if show_failures:
                emitter.publish(_get_history_message(
                                json_history, job_id, False))
                table = tables.job_history_table(
                    json_history['history']['failedFinishedRuns'])
                output = six.text_type(table)
                if output:
                    emitter.publish(output)

    return 0


def _get_history_message(json_history, job_id, success=True):
    """
    :param json_history: json of history
    :type json_history: json
    :param job_id: Id of the job
    :type job_id: str
    :returns: history message
    :rtype: str
    """
    if success is True:
        return "'{}'  Successful runs: {} Last Success: {}".format(
                job_id, json_history['history']['successCount'],
                json_history['history']['lastSuccessAt'])
    else:
        return "'{}'  Failure runs: {} Last Failure: {}".format(
                job_id, json_history['history']['failureCount'],
                json_history['history']['lastFailureAt'])


def _show(job_id):
    """
    :param job_id: Id of the job
    :type job_id: str
    :returns: process return code
    :rtype: int
    """

    response = None
    try:
        response = _do_request("{}/{}".format(
            _get_api_url('v1/jobs'), job_id), 'GET')
    except DCOSHTTPException as e:
        if e.response.status_code == 404:
            raise DCOSException("Job ID: '{}' does NOT exist.".format(job_id))
        else:
            raise DCOSException(e)

    json_job = _read_http_response_body(response)
    emitter.publish(json_job)

    return 0


def _show_runs(job_id, run_id=None, json_flag=False, q=False):
    """
    :param job_id: Id of the job
    :type job_id: str
    :returns: process return code
    :rtype: int
    """

    json_runs = _get_runs(job_id, run_id)
    if q is True:
        ids = _get_ids(json_runs)
        emitter.publish(ids)
    elif json_flag is True:
        emitter.publish(json_runs)
    else:
        if json_flag:
            emitter.publish(json_runs)
        else:
            if _json_array_has_element(json_runs, 'id'):
                table = tables.job_runs_table(json_runs)
                output = six.text_type(table)
                if output:
                    emitter.publish(output)
            else:
                emitter.publish("Nothing running for '{}'".format(job_id))

    return 0


def _json_array_has_element(json_object, field):
    exists = False
    for element in json_object:
        if field in element:
            exists = True
            break
    return exists


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
        response = _do_request(url, 'GET')
    except DCOSException as e:
        raise DCOSException(e)

    json_runs = _read_http_response_body(response)

    return json_runs


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
        http.post(url, timeout=timeout)
    except DCOSHTTPException as e:
        if e.response.status_code == 404:
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
    except DCOSHTTPException as e:
        if e.response.status_code == 404:
            raise DCOSException("Job ID: '{}' does NOT exist.".format(job_id))
        else:
            raise DCOSException(e)
    except DCOSException as e:
        raise DCOSException(e)

    json_schedule = _read_http_response_body(response)
    if json_flag:
        emitter.publish(json_schedule)
    else:
        table = tables.schedule_table(json_schedule)
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
            _post_schedule(job_id, schedule)
        except DCOSHTTPException as e:
            if e.response.status_code == 404:
                emitter.publish("Job ID: '{}' does NOT exist.".format(job_id))
            elif e.response.status_code == 409:
                emitter.publish("Schedule already exists.")
            else:
                raise DCOSException(e)
        except DCOSException as e:
            raise DCOSException(e)

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
        raise DCOSException("No schedule to update.")

    try:
        _put_schedule(job_id, schedule_id, schedule_json)
        emitter.publish("Schedule ID `{}` for job ID `{}` updated."
                        .format(schedule_id, job_id))
    except DCOSHTTPException as e:
        if e.response.status_code == 404:
            emitter.publish("Job ID: '{}' or schedule ID '{}' does NOT exist."
                            .format(job_id, schedule_id))
    except DCOSException as e:
        raise DCOSException(e)

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
        raise DCOSException("No JSON provided.")

    if 'id' not in full_json:
        raise DCOSException("Jobs JSON requires an ID.")

    job_id = full_json['id']
    schedules = None

    if 'schedules' in full_json:
        schedules = full_json['schedules']
        del full_json['schedules']

    # iterate and post each schedule
    job_added = False
    try:
        _post_job(full_json)
        job_added = True
    except DCOSHTTPException as e:
        if e.response.status_code == 409:
            emitter.publish("Job ID: '{}' already exists".format(job_id))
        else:
            raise DCOSException(e)

    if schedules is not None and job_added is True:
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
        raise DCOSException("No JSON provided.")

    job_id = full_json['id']

    if 'schedules' in full_json:
        del full_json['schedules']

    try:
        _put_job(job_id, full_json)
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

    response = http.put(url, json=job_json, timeout=timeout)

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
    url = "{}/{}/schedules/{}".format(_get_api_url('v1/jobs'),
                                      job_id, schedule_id)

    response = http.put(url, json=schedule_json, timeout=timeout)

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

    response = http.post(url, json=schedule_json, timeout=timeout)

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
        http_response = http.get(url, is_success=_is_success,
                                 timeout=timeout, **kwargs)
    elif method.lower() == 'post':
        http_response = http.post(url, is_success=_is_success,
                                  timeout=timeout, stream=stream, **kwargs)
    elif method.lower() == 'delete':
        http_response = http.delete(url, is_success=_is_success,
                                    timeout=timeout, stream=stream, **kwargs)
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


def _get_ids(ids_json):
    """
    :param ids_json: json array of elements with ids
    :type ids_json: json
    :returns: set of ids
    :rtype: set
    """
    ids = list()
    for element in ids_json:
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
                    raise DCOSHTTPException("HTTP error code: {}"
                                            .format(req.status_code))
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
        # dcos must be capable to use dcos_url
        _check_capability()
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
