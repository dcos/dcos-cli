import abc


class Error(object):
    """Abstract class for describing errors."""

    @abc.abstractmethod
    def error(self):
        """Creates an error message

        :returns: The error message
        :rtype: str
        """

        raise NotImplementedError
