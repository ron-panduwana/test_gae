
class CaptchaRequiredMiddleware(object):
    def process_exception(self, request, exception):
        from django.http import HttpResponseRedirect, HttpResponse
        from crlib.gdata_wrapper import GDataCaptchaRequiredError

        if isinstance(exception, GDataCaptchaRequiredError):
            return HttpResponseRedirect(
                'https://www.google.com/a/%s/UnlockCaptcha' % exception.domain)
