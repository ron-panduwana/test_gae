from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from google.appengine.api import users, memcache

from crappadmin.forms import DomainForm
from crappadmin.tables import domains_table
from crauth.models import AppsDomain
from crgappspanel.views.utils import redirect_saved
from crlib.navigation import render_with_nav, Section


def navigation(request):
    if not users.is_current_user_admin():
        return
    return (
        Section('appadmin', _('Superadmin Panel'), reverse('domains'), (
            Section('domains', _('All Domains'), reverse('domains')),
            Section('tools', _('Tools'), reverse('tools')),
            Section('docs', _('Documentation'), '/appadmin/docs/index.html'),
            Section('admin_logout', _('Logout'), users.create_logout_url('/')),
        )),
    )


def domains(request):
    domains = AppsDomain.all().fetch(1000)
    ctx = {
        'table': domains_table(request, domains),
    }
    return render_with_nav(request, 'domains_list.html', ctx)


def domain_details(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    domain = AppsDomain.get_by_key_name(name)
    if not domain:
        return redirect('domains')
    
    if request.method == 'POST':
        form = DomainForm(request.POST, auto_id=True)
        if form.is_valid():
            form.populate(domain)
            domain.save()
            return redirect_saved('domain-details', request, name=domain.domain)
    else:
        form = DomainForm(initial=dict(domain=domain.domain,
            admin_email=domain.admin_email, license_state=domain.license_state,
            is_enabled=domain.is_enabled, is_independent=domain.is_independent),
            auto_id=True)
    
    return render_with_nav(request, 'domain_details.html', {
        'domain': domain,
        'form': form,
        'saved': request.session.pop('saved', None),
    }, in_section='appadmin/domains')


TOOLS_ACTIONS = {
    'memcache': lambda x: memcache.flush_all(),
}

def tools(request):
    if request.method == 'POST':
        for key, value in request.POST.iteritems():
            if key in TOOLS_ACTIONS:
                TOOLS_ACTIONS[key](request)
        return HttpResponseRedirect(request.path)
    return render_with_nav(request, 'tools.html')

