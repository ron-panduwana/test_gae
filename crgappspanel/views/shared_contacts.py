from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

from crauth import users
from crauth.decorators import has_perm
from crgappspanel.forms import SharedContactForm
from crgappspanel.helpers.filters import SharedContactFilter, \
        SharedContactAdvancedFilter, NullFilter
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.models import Preferences, SharedContact, Organization
from crgappspanel.views.utils import get_sortby_asc, list_attrs, \
        get_page, qs_wo_page, redirect_saved, QueryString, QuerySearch, render
from crlib.navigation import render_with_nav


def _get_full_name(x):
    if x.name and hasattr(x.name, 'full_name'):
        return x.name.full_name
    return None

def _get_given_name(x):
    if x.name and hasattr(x.name, 'given_name'):
        return x.name.given_name
    return None

def _get_family_name(x):
    if x.name and hasattr(x.name, 'family_name'):
        return x.name.family_name
    return None

def _get_real_name(x):
    return '%s %s' % (_get_given_name(x) or '', _get_family_name(x) or '')

def _get_company_role(x):
    if x.organization:
        return '%s/%s' % (x.organization.name, x.organization.title)
    else:
        return ''


_table_fields = [
    Column(_('Display name'), 'full_name', getter=_get_full_name, link=True),
    Column(_('Real name'), 'real_name', getter=_get_real_name),
    Column(_('Company'), 'company', getter=lambda x: x.organization and
           x.organization.name or ''),
    Column(_('Phone numbers'), 'phone_numbers',
        getter=lambda x: list_attrs(x.phone_numbers, 'number')),
    Column(_('Emails'), 'emails',
        getter=lambda x: list_attrs(x.emails, 'address')),
]
_table_id = Column(None, 'key', getter=lambda x: x.key())
_table_widths = ['%d%%' % x for x in (5, 20, 20, 15, 10, 30)]


@has_perm('read_sharedcontact')
def shared_contacts(request):
    sortby, asc = get_sortby_asc(request, [f.name for f in _table_fields])
    
    # getting queries
    query = request.GET.get('q', '')
    query_adv = QuerySearch()
    query_adv.add(request, 'name', 'name.full_name')
    query_adv.add(request, 'notes', 'notes')
    query_adv.add(request, 'email', 'emails.address')
    query_adv.add(request, 'phone', 'phone_numbers.number')
    query_adv.add(request, 'company', None)
    query_adv.add(request, 'role', None)
    
    shared_contacts = SharedContact.all().fetch(1000)
    
    if query:
        advanced_search = False
        filter = SharedContactFilter(query)
        filters = ['%s:%s' % (_('query'), query)]
    elif not query_adv.is_empty():
        advanced_search = True
        filter = SharedContactAdvancedFilter(query_adv.filter_attrs,
            query_adv.search_by.get('company', ''), query_adv.search_by.get('role', ''))
        filters = ['%s:%s' % (_(key), value) for key, value in query_adv.search_by.iteritems()]
    else:
        advanced_search = False
        filter = NullFilter()
        filters = None
    
    # filtering shared contacts
    shared_contacts = [x for x in shared_contacts if filter.match(x)]
    
    # instantiating table and sorting shared contacts
    table = Table(_table_fields, _table_id, sortby=sortby, asc=asc)
    table.sort(shared_contacts)
    
    # selecting particular page
    per_page = Preferences.for_current_user().items_per_page
    page = get_page(request, shared_contacts, per_page)
    
    return render_with_nav(request, 'shared_contacts_list.html', {
        'table': table.generate(
            page.object_list, page=page, qs_wo_page=qs_wo_page(request),
            widths=_table_widths, singular='shared contact',
            delete_link_title=_('Delete shared contacts'),
            can_change=users.get_current_user().has_perm(
                'change_sharedcontact')),
        'advanced_search': advanced_search,
        'filters': filters,
        'query': dict(general=query, advanced=query_adv.search_by),
        'saved': request.session.pop('saved', False),
    })


@has_perm('add_sharedcontact')
def shared_contact_add(request):
    if request.method == 'POST':
        form = SharedContactForm(request.POST, auto_id=True)
        if form.is_valid():
            shared_contact = form.create()
            shared_contact.name.save()
            for email in shared_contact.emails:
                email.save()
            for phone in shared_contact.phone_numbers:
                phone.save()
            shared_contact.save()
            return redirect_saved('shared-contact-details',
                request, key=shared_contact.key())
    else:
        form = SharedContactForm(auto_id=True)
    
    return render_with_nav(request, 'shared_contact_add.html', {
        'form': form,
    }, in_section='shared_contacts')


@has_perm('change_sharedcontact')
def shared_contact_details(request, key=None):
    if not key:
        raise ValueError('key = %s' % key)
    
    shared_contact = SharedContact.get_by_key_name(key)
    if not shared_contact:
        return redirect('shared-contacts')
    
    if request.method == 'POST':
        form = SharedContactForm(request.POST, auto_id=True)
        if form.is_valid():
            new_objects = form.populate(shared_contact)
            shared_contact.name.save()
            
            for email in new_objects['emails']:
                email.save()
                shared_contact.emails.append(email)
            
            for phone_number in new_objects['phone_numbers']:
                phone_number.save()
                shared_contact.phone_numbers.append(phone_number)
            
            company = new_objects.get('company_str', '')
            role = new_objects.get('role_str', '')
            if company or role:
                if not shared_contact.organization:
                    shared_contact.organization = Organization(
                        name=company, title=role)
                else:
                    shared_contact.organization.name = company
                    shared_contact.organization.title = role
                shared_contact.organization.save()
            else:
                shared_contact.organization = None
            
            shared_contact.save()
            return redirect_saved('shared-contact-details',
                request, key=key)
    else:
        real_name = (shared_contact.name.given_name,
                     shared_contact.name.family_name)
        form = SharedContactForm(initial={
            'full_name': shared_contact.name.full_name,
            'real_name': real_name,
            'company': shared_contact.organization and \
                shared_contact.organization.name or '',
            'role': shared_contact.organization and \
                shared_contact.organization.title or '',
            'notes': shared_contact.notes,
            'emails': '',
        }, auto_id=True)
    
    def remove_email_link(x):
        kwargs = dict(key=key, email=x.address)
        return reverse('shared-contact-remove-email', kwargs=kwargs)
    full_emails = []
    for email in shared_contact.emails:
        idx = email.address.find('@')
        if idx != -1:
            fmt = '<span class="email-username">%s</span><span class="email-domain">@%s</span> &ndash; <a href="%s">Remove</a>'
            user_part = email.address[:idx]
            domain_part = email.address[idx+1:]
            full_emails.append(fmt % (user_part, domain_part, remove_email_link(email)))
        else:
            fmt = '%s &ndash; <a href="%s">Remove</a>'
            full_emails.append(fmt % (email.address, remove_email_link(email)))
    
    def remove_phone_link(x):
        kwargs = dict(key=key, phone=x.number)
        return reverse('shared-contact-remove-phone', kwargs=kwargs)
    full_phones = []
    for phone in shared_contact.phone_numbers:
        fmt = '%s &ndash; <a href="%s">Remove</a>'
        full_phones.append(fmt % (phone.number, remove_phone_link(phone)))
    
    return render_with_nav(request, 'shared_contact_details.html', {
        'shared_contact': shared_contact,
        'form': form,
        'full_emails': full_emails,
        'full_phones': full_phones,
        'saved': request.session.pop('saved', False),
    }, in_section='shared_contacts')


@has_perm('change_sharedcontact')
def shared_contact_remove(request, keys=None):
    if not keys:
        raise ValueError('keys = %s' % keys)
    
    for key in keys.split('/'):
        contact = SharedContact.get_by_key_name(key)
        if contact:
            contact.delete()
    
    return redirect_saved('shared-contacts', request)


@has_perm('change_sharedcontact')
def shared_contact_remove_email(request, key=None, email=None):
    if not all((key, email)):
        raise ValueError('key = %s, email = %s' % (key, email))
    
    shared_contact = SharedContact.get_by_key_name(key)
    if not shared_contact:
        return redirect('shared-contacts')
    
    for index, elem in enumerate(shared_contact.emails):
        if elem.address == email:
            del shared_contact.emails[index]
            break
    shared_contact.save()
    
    return redirect_saved('shared-contact-details', request, key=key)


@has_perm('change_sharedcontact')
def shared_contact_remove_phone(request, key=None, phone=None):
    if not all((key, phone)):
        raise ValueError('key = %s, phone = %s' % (key, phone))
    
    shared_contact = SharedContact.get_by_key_name(key)
    if not shared_contact:
        return redirect('shared-contacts')
    
    for index, elem in enumerate(shared_contact.phone_numbers):
        if elem.number == phone:
            del shared_contact.phone_numbers[index]
            break
    shared_contact.save()
    
    return redirect_saved('shared-contact-details', request, key=key)
