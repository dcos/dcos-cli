from dcos import emitting, http, util
from dcos.errors import DCOSAuthenticationException

from six.moves import urllib

logger = util.get_logger(__name__)

emitter = emitting.FlatEmitter()


class Cosmos:
    """Implementation of Package Manager using Cosmos"""

    def __init__(self, cosmos_url):
        self.cosmos_url = cosmos_url

    def enabled(self):
        """Returns whether or not cosmos is enabled on specified dcos cluter

        :rtype: bool
        """

        try:
            url = urllib.parse.urljoin(self.cosmos_url, 'capabilities')
            response = http.get(url,
                                headers=_get_capabilities_header())
        # return `Authentication failed` error messages, but all other errors
        # are treated as endpoint not available
        except DCOSAuthenticationException:
            raise
        except Exception as e:
            logger.exception(e)
            return False

        return response.status_code == 200


def _get_header(request_type):
    """Returns header str for talking with cosmos

    :param request_type: name of specified request (ie uninstall-request)
    :type request_type: str
    :returns: header information
    :rtype: str
    """

    return ("application/vnd.dcos.package.{}+json;"
            "charset=utf-8;version=v1").format(request_type)


def _get_cosmos_header(request_name):
    """Returns header fields needed for a valid request to cosmos

    :param request_name: name of specified request (ie uninstall)
    :type request_name: str
    :returns: dict of required headers
    :rtype: {}
    """

    return {"Accept": _get_header("{}-response".format(request_name)),
            "Content-Type": _get_header("{}-request".format(request_name))}


def _get_capabilities_header():
    """Returns header fields needed for a valid request to cosmos capabilities
    endpoint
    :returns: header information
    :rtype: dict
    """

    header = "application/vnd.dcos.capabilities+json;charset=utf-8;version=v1"
    return {"Accept": header}
