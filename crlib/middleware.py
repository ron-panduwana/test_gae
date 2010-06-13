from django.http import HttpResponseRedirect
from crlib.mappers import RetryError


class PrecacheRetryMiddleware(object):
    def process_exception(self, request, exception):
        if isinstance(exception, RetryError):
            return HttpResponseRedirect(request.get_full_path())
