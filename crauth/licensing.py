import urllib
from django.conf import settings
import atom.data
import atom.core
from gdata.client import GDClient
from gdata.gauth import TwoLeggedOAuthHmacToken
from gdata.data import GDEntry, GDFeed


STATE_PENDING = 'PENDING'
STATE_ACTIVE = 'ACTIVE'
STATE_UNLICENSED = 'UNLICENSED'
LICENSE_STATES = (
    STATE_PENDING, STATE_ACTIVE, STATE_UNLICENSED,
)


_BASE_URL = 'http://feedserver-enterprise.googleusercontent.com/'
_LIC_URL = _BASE_URL + 'license?bq='
_NOT_URL = _BASE_URL + 'licensenotification?bq='


class Id(atom.data.Text):
    _qname = atom.data.ATOM_TEMPLATE % 'id'


class DomainName(atom.data.Text):
    _qname = atom.data.ATOM_TEMPLATE % 'domainname'


class InstallerEmail(atom.data.Text):
    _qname = atom.data.ATOM_TEMPLATE % 'installeremail'


class TOSAcceptanceTime(atom.data.Text):
    _qname = atom.data.ATOM_TEMPLATE % 'tosacceptancetime'


class LastChangeTime(atom.data.Text):
    _qname = atom.data.ATOM_TEMPLATE % 'lastchangetime'


class State(atom.data.Text):
    _qname = atom.data.ATOM_TEMPLATE % 'state'


class Enabled(atom.data.Text):
    _qname = atom.data.ATOM_TEMPLATE % 'enabled'


class Entity(atom.core.XmlElement):
    _qname = atom.data.ATOM_TEMPLATE % 'entity'
    id = Id
    domain_name = DomainName
    installer_email = InstallerEmail
    tos_acceptance_time = TOSAcceptanceTime
    last_change_time = LastChangeTime
    state = State
    enabled = Enabled


class Content(atom.core.XmlElement):
    _qname = atom.data.ATOM_TEMPLATE % 'content'
    entity = Entity


class LicenseEntry(GDEntry):
    content = Content


class LicenseFeed(GDFeed):
    entry = [LicenseEntry]


def _default_oauth_token():
    from gdata.gauth import TwoLeggedOAuthHmacToken
    return TwoLeggedOAuthHmacToken(
        settings.OAUTH_CONSUMER, settings.OAUTH_SECRET, '')


class LicensingClient(GDClient):
    def __init__(self, app_id=settings.OAUTH_APP_ID, *args, **kwargs):
        self.app_id = app_id
        if not kwargs.has_key('auth_token'):
            kwargs['auth_token'] = _default_oauth_token()
        super(LicensingClient, self).__init__(*args, **kwargs)

    def get_domain_info(self, domain):
        lic_url = _LIC_URL + urllib.quote('[appid=%s][domain=%s]' % (
            self.app_id, domain))
        return self.get_feed(lic_url, desired_class=LicenseFeed)

    def get_notifications(self, start_datetime, max_results=100):
        start_datetime = start_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        not_url = _NOT_URL + urllib.quote(
            '[appid=%s][startdatetime=%s][max-results=%d]' % (
                self.app_id, start_datetime, max_results))
        return self.get_feed(not_url, desired_class=LicenseFeed)

