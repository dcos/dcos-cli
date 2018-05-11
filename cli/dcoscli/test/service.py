import collections
import json

from .common import assert_command, exec_command


def wait_for_service(service_name, number_of_services=1, max_count=300):
    """Wait for service to register with Mesos

    :param service_name: name of service
    :type service_name: str
    :param number_of_services: number of services with that name
    :type number_of_services: int
    :param max_count: max number of seconds to wait
    :type max_count: int
    :rtype: None
    """

    count = 0
    while count < max_count:
        services = get_services()

        if (len([service for service in services
                 if service['name'] == service_name]) >= number_of_services):
            return

        count += 1


def get_services(expected_count=None, args=[]):
    """Get services

    :param expected_count: assert exactly this number of services are
        running
    :type expected_count: int | None
    :param args: cli arguments
    :type args: [str]
    :returns: services
    :rtype: [dict]
    """

    returncode, stdout, stderr = exec_command(
        ['dcos', 'service', '--json'] + args)

    assert returncode == 0
    assert stderr == b''

    services = json.loads(stdout.decode('utf-8'))
    assert isinstance(services, collections.Sequence)
    if expected_count is not None:
        assert len(services) == expected_count

    return services


def service_shutdown(service_id):
    """Shuts down a service using the command line program

    :param service_id: the id of the service
    :type: service_id: str
    :rtype: None
    """

    assert_command(['dcos', 'service', 'shutdown', service_id])
