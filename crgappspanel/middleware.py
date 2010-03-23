class CaptchaRequiredMiddleware(object):
    def process_exception(self, request, exception):
        import hashlib
        from django.http import HttpResponseRedirect, HttpResponse
        from django.core.urlresolvers import reverse
        from google.appengine.api import memcache
        from crlib.gdata_wrapper import GDataCaptchaRequiredError

        if isinstance(exception, GDataCaptchaRequiredError):
            captcha_hash = hashlib.sha1(exception.captcha_token).hexdigest()[:10]
            captcha_info = {
                'token': exception.captcha_token,
                'url': exception.captcha_url,
                'email': exception.email,
            }
            memcache.set('captcha:%s' % captcha_hash, captcha_info, 5 * 60)
            redirect_to = '?redirect_to=%s' % request.path
            return HttpResponseRedirect(
                reverse('captcha', args=(captcha_hash,)) + redirect_to)

