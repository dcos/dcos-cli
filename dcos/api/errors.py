import abc


class Error(object):

    @abc.abstractmethod
    def error(self):
        """Creates an error message

        :returns: The error message
        :rtype: str
        """

        raise NotImplementedError
