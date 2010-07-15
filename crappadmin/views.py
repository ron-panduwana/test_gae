from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.http import HttpResponseRedirect, Http404
from django.utils.translation import ugettext_lazy as _
from google.appengine.api import users, memcache

from crappadmin.forms import DomainForm
from crappadmin.tables import domains_table
from crauth.models import AppsDomain
from crgappspanel.views.utils import redirect_saved
from crlib.navigation import render_with_nav, Section


def navigation(request):
    """Displays the navigation panel. 
    """
    if not users.is_current_user_admin():
        return
    return (
        Section('appadmin', _('Superadmin Panel'), reverse('domains'), (
            Section('domains', _('All Domains'), reverse('domains')),
            Section('tools', _('Tools'), reverse('tools')),
            Section('appengine', _('Appengine Dashboard'),
                    'http://appengine.google.com/dashboard?app_id=ga-powerpanel-dev'),
            Section('docs', _('Documentation'), '/appadmin/docs/index.html'),
            Section('admin_logout', _('Logout'), users.create_logout_url('/')),
        )),
    )


def domains(request):
    """Displays the list of domains. 
    """
    domains = AppsDomain.all().fetch(1000)
    
    return render_with_nav(request, 'domains_list.html', {
        'table': domains_table(request, domains),
        'saved': request.session.pop('saved', False),
        'delete_link_title': _('Delete domains'),
        'delete_question': _('Are you sure you want to delete selected '
                             'domains?'),
    })


def domain_create(request):
    """Displays the form for creating new domain. 
    """
    if request.method == 'POST':
        form = DomainForm(request.POST, auto_id=True)
        if form.is_valid():
            domain = form.create()
            domain.installation_token = AppsDomain.random_token()
            domain.save()
            return redirect_saved('domain-details', request, name=domain.domain)
    else:
        form = DomainForm(auto_id=True)
    
    return render_with_nav(request, 'domain_create.html', {
        'form': form,
    }, in_section='appadmin/domains')


def domain_change_installation_link(request, name):
    domain = AppsDomain.get_by_key_name(name)
    if not domain:
        raise Http404
    domain.installation_token = AppsDomain.random_token()
    domain.put()
    return HttpResponseRedirect(reverse(domain_details, args=(domain.domain,)))


def domain_details(request, name=None):
    """Displays the details of the selected domain. 
    """
    if not name:
        raise ValueError('name = %s' % name)
    
    domain = AppsDomain.get_by_key_name(name)
    if not domain:
        return redirect('domains')
    
    if not domain.installation_token:
        domain.installation_token = AppsDomain.random_token()
        domain.put()
    
    if request.method == 'POST':
        form = DomainForm(request.POST, auto_id=True)
        if form.is_valid():
            form.populate(domain)
            domain.save()
            return redirect_saved('domain-details', request, name=domain.domain)
    else:
        form = DomainForm(initial=dict(domain=domain.domain,
            admin_email=domain.admin_email, is_enabled=domain.is_enabled,
            is_independent=domain.is_independent), auto_id=True)
    
    return render_with_nav(request, 'domain_details.html', {
        'domain': domain,
        'installation_link': domain.installation_link(request),
        'form': form,
        'saved': request.session.pop('saved', None),
    }, in_section='appadmin/domains')


def domain_remove(request, names=None):
    """Removes the selected domain. 
    """
    if not names:
        raise ValueError('names = %s' % names)
    
    for name in names.split('/'):
        domain = AppsDomain.get_by_key_name(name)
        if domain:
            domain.delete()
    
    return redirect('domains')


TOOLS_ACTIONS = {
    'memcache': lambda x: memcache.flush_all(),
}

def tools(request):
    """Displays the tools panel.
    """
    if request.method == 'POST':
        for key, value in request.POST.iteritems():
            if key in TOOLS_ACTIONS:
                TOOLS_ACTIONS[key](request)
        return HttpResponseRedirect(request.path)
    return render_with_nav(request, 'tools.html')

