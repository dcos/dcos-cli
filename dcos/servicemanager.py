from dcos import cosmos, util


class ServiceManager(object):
    """A manager for DC/OS services"""

    def __init__(self, cosmos_url):
        self.cosmos_url = cosmos_url
        self.cosmos = cosmos.Cosmos(self.cosmos_url)

    def enabled(self):
        """
        Returns whether service manager is enabled.

        :return: true whether this service is enabled, false otherwise
        :rtype: bool
        """
        return self.cosmos.enabled()

    def start_service(self, package_name, package_version, options):
        """
        Starts a service that has been added to the cluster via
        cosmos' package/add endpoint.

        :param package_name: the name of the package to start
        :type package_name: str
        :param package_version: the version of the package to start
        :type package_version: None | str
        :param options: the options for the service
        :type options: None | str
        :param app_id: the app id for the service
        :type app_id: None | str
        :return: json encoded response of cosmos' service/start endpoint
        :rtype: dict
        """
        endpoint = 'service/start'
        json = util.remove_nones({
            'packageName': package_name,
            'packageVersion': package_version,
            'options': options
        })
        return self.cosmos.call_endpoint(endpoint, json=json)
