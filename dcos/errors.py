import abc


class Error(object):

    @abc.abstractmethod
    def error(self):
        raise NotImplementedError
