from django.http import HttpResponseRedirect
from crlib.gdata_wrapper import RetryError


class PrecacheRetryMiddleware(object):
    def process_exception(self, request, exception):
        if isinstance(exception, RetryError):
            return HttpResponseRedirect(request.get_full_path())
