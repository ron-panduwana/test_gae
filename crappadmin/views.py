from google.appengine.api import users
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from crauth.models import AppsDomain
from crlib.navigation import render_with_nav, Section
from crappadmin.tables import domains_table


def navigation(request):
    if not users.is_current_user_admin():
        return
    return (
        Section('appadmin', _('Superadmin Panel'), reverse('all_domains'), (
            Section('all_domains', _('All Domains'), reverse('all_domains')),
            Section('docs', _('Documentation'), '/appadmin/docs/index.html'),
            Section('admin_logout', _('Logout'), users.create_logout_url('/')),
        )),
    )


def all_domains(request, template='all_domains.html'):
    domains = AppsDomain.all().fetch(1000)
    ctx = {
        'table': domains_table(request, domains),
    }
    return render_with_nav(request, template, ctx)

