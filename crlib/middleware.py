from django.utils.cache import patch_vary_headers
from django.utils import translation
from django.http import HttpResponseRedirect
from crlib.gdata_wrapper import RetryError
from crgappspanel.models import Preferences


class PrecacheRetryMiddleware(object):
    def process_exception(self, request, exception):
        if isinstance(exception, RetryError):
            return HttpResponseRedirect(request.get_full_path())


class LocaleMiddleware(object):
    """
    This is a very simple middleware that parses a request
    and decides what translation object to install in the current
    thread context. This allows pages to be dynamically
    translated to the language the user desires (if the language
    is available, of course).
    """

    def process_request(self, request):
        prefs = Preferences.for_current_user()
        if prefs:
            language = prefs.language
        else:
            language = translation.get_language_from_request(request)
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        patch_vary_headers(response, ('Accept-Language',))
        if 'Content-Language' not in response:
            response['Content-Language'] = translation.get_language()
        translation.deactivate()
        return response
