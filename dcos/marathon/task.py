
from . import util

class Task(util.ServerRequest):

    @property
    def _base_url(self):
        return "/v2/apps/{0}/tasks/{1}".format(self.app.id, self.id)

    @property
    def time(self):
        t = self.startedAt if self.startedAt != None else self.stagedAt
        return util.since(t)

    @property
    def healthy(self):
        if not hasattr(self, 'healthCheckResults'):
            return None
        elif len(self.healthCheckResults) == 0 or \
                None in self.healthCheckResults:
            return None
        elif len(filter(lambda x: not x["alive"], self.healthCheckResults)) > 0:
            return False
        else:
            return True

    @property
    def app(self):
        # Avoid circular imports
        from . import server
        return server.current.app(self.appId)

    # ----- Commands

    def kill(self):
        return self._req("delete")
