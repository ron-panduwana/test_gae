import urllib
from django.conf import settings
import atom.data
import atom.core
from gdata.client import GDClient
from gdata.gauth import TwoLeggedOAuthHmacToken
from gdata.data import GDEntry, GDFeed


#: Application has just been installed and will soon be in the
#: :const:`STATE_ACTIVE` state.
STATE_PENDING = 'PENDING'
#: Application is installed and enabled.
STATE_ACTIVE = 'ACTIVE'
#: Application is uninstalled or disabled.
STATE_UNLICENSED = 'UNLICENSED'
#: Possible licensing states.
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
    """Wrapper around *Google Marketplace*
    `Licensing API
    <http://code.google.com/intl/pl/googleapps/marketplace/licensing.html>`_.

    :param app_id: Application ID for given Marketplace listing.
    :type app_id: str

    """
    def __init__(self, app_id=settings.OAUTH_APP_ID, *args, **kwargs):
        self.app_id = app_id
        if not kwargs.has_key('auth_token'):
            kwargs['auth_token'] = _default_oauth_token()
        super(LicensingClient, self).__init__(*args, **kwargs)

    def get_domain_info(self, domain):
        """Return licensing information about given domain.

        :param domain: Google Apps domain.
        :type domain: str
        :returns: :class:`LicenseEntry` object.
        :rtype: :class:`LicenseEntry`

        """
        lic_url = _LIC_URL + urllib.quote('[appid=%s][domain=%s]' % (
            self.app_id, domain))
        return self.get_feed(lic_url, desired_class=LicenseFeed)

    def get_notifications(self, start_datetime, max_results=100):
        """Get notifications about license state changes for all domain since
        given ``start_datetime``.

        :param start_datetime: Get notifications from this time on.
        :type start_datetime: datetime
        :param max_results: Get up to ``max_results`` results.
        :type max_results: int
        :returns: Feed of :class:`LicenseEntry`.
        :rtype: :class:`LicenseFeed`

        """
        start_datetime = start_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        not_url = _NOT_URL + urllib.quote(
            '[appid=%s][startdatetime=%s][max-results=%d]' % (
                self.app_id, start_datetime, max_results))
        return self.get_feed(not_url, desired_class=LicenseFeed)

