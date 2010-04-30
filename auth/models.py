from appengine_django.models import BaseModel
from google.appengine.ext import db
from google.appengine.api import memcache
from auth.licensing import LICENSE_STATES, STATE_ACTIVE


DASHBOARD_URL = 'https://www.google.com/a/cpanel/%s/Dashboard'
INBOX_URL = 'https://mail.google.com/a/%s'
CALENDAR_URL = 'https://www.google.com/calendar/hosted/%s'
HELP_URL = 'http://www.google.com/support/a'


class Association(db.Model):
    url = db.LinkProperty()
    handle = db.StringProperty()
    association = db.TextProperty()


class AppsDomain(BaseModel):
    CACHE_TIME = 2 * 60 * 60 # we cache activity state for 2 hours
    domain = db.StringProperty(required=True)
    admin_email = db.StringProperty()
    # apparently it's only possible to send ClientLogin passwrods in clear text,
    # so no hashing
    admin_password = db.StringProperty()
    is_superadmin = db.BooleanProperty(default=False)
    license_state = db.StringProperty(choices=LICENSE_STATES)

    def dashboard_url(self):
        return DASHBOARD_URL % self.domain

    def inbox_url(self):
        return INBOX_URL % self.domain

    def calendar_url(self):
        return CALENDAR_URL % self.domain

    def is_active(self):
        return self.license_state == STATE_ACTIVE

    @classmethod
    def is_arbitrary_domain_active(cls, domain):
        from auth.licensing import LicensingClient
        apps_domain = AppsDomain.get_by_key_name(domain)
        if apps_domain is not None and apps_domain.is_active():
            return True
        client = LicensingClient()
        result = client.get_domain_info(domain).entry[0]
        return result.content.entity.state.text == STATE_ACTIVE


