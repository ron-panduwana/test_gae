from django.utils.translation import ugettext_lazy as _
from crgappspanel.helpers import tables


_DOMAINS_TABLE_COLUMNS = (
    tables.Column(_('Domain'), 'domain', getter=lambda x: x.domain, link=True),
    tables.Column(_('Administrator Email'), 'admin_email',
                  getter=lambda x: x.admin_email, link=True),
    tables.Column(_('Enabled?'), 'is_enabled', getter=lambda x: x.is_enabled,
                  link=True),
)


def domains_table(request, domains):
    table = tables.Table(_DOMAINS_TABLE_COLUMNS, tables.Column(None, 'domain'))
    return table.generate(domains)
