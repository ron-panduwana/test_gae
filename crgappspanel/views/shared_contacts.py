from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _

from crauth import users
from crauth.decorators import has_perm
from crgappspanel.forms import SharedContactForm
from crgappspanel.helpers.filters import SharedContactFilter, \
        SharedContactAdvancedFilter, NullFilter
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.helpers.paginator import Paginator
from crgappspanel.models import Preferences, SharedContact, Organization
from crgappspanel.views.utils import get_sortby_asc, list_attrs, \
        get_page, qs_wo_page, redirect_saved, QueryString, QuerySearch, render
from crlib.navigation import render_with_nav
from crlib import errors


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
    Column(_('Display name'), 'title', getter=lambda x: x.title, link=True),
    Column(_('Real name'), 'name', getter=_get_real_name),
    Column(_('Company'), 'organization', getter=lambda x: x.organization and
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
    user = users.get_current_user()

    query = request.GET.get('q', '')
    if query:
        query = query.lower().split()[0]
        def query_gen():
            q = SharedContact.all()
            # This doesn't work as expected on development server, but is OK
            # on GAE instance.
            q.filter('search_index >=', query).filter(
                'search_index <', query + u'\ufffd')
            return q
    else:
        query_gen = None

    per_page = Preferences.for_current_user().items_per_page
    paginator = Paginator(SharedContact, request, (
        'title', 'name', 'organization', 'phone_numbers', 'emails',
    ), per_page, query=query_gen)
    
    table = Table(_table_fields, _table_id)
    
    delete_link_title = _('Delete shared contacts')
    return render_with_nav(request, 'shared_contacts_list.html', {
        'table': table.generate_paginator(
            paginator, widths=_table_widths,
            delete_link_title=delete_link_title,
            can_change=user.has_perm('change_sharedcontact')),
        'query': dict(general=query),
        'saved': request.session.pop('saved', False),
        'delete_question': _('Are you sure you want to delete selected '
                             'shared contacts?'),
        'delete_link_title': delete_link_title,
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
            try:
                shared_contact.save()
                return redirect_saved('shared-contact-details',
                    request, key=shared_contact.key())
            except errors.EntitySizeTooLarge:
                form.add_error('__all__',
                               _('One or more field is too long.'))
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
            
            try:
                shared_contact.save()
                return redirect_saved('shared-contact-details',
                    request, key=key)
            except errors.EntitySizeTooLarge:
                form.add_error('__all__',
                               _('One or more field is too long.'))
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
