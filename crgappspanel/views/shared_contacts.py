from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, redirect
from django.utils.translation import ugettext as _

from crgappspanel.forms import SharedContactForm
from crgappspanel.helpers.filters import SharedContactFilter, \
        SharedContactAdvancedFilter, NullFilter
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.models import SharedContact
from crgappspanel.views.utils import ctx, get_sortby_asc, list_attrs, \
        get_page, qs_wo_page, redirect_saved, QueryString, QuerySearch
from crlib.users import admin_required


def _get_company_role(x):
    company = x.extended_properties.get('company')
    if not company:
        return ''
    role = x.extended_properties.get('role')
    if not role:
        return company
    return '%s/%s' % (company, role)


_sharedContactFields = [
    Column(_('Name'), 'full_name', getter=lambda x: x.name.full_name, link=True),
    Column(_('Real name'), 'real_name',
        getter=lambda x: '%s %s' % (x.name.given_name or '', x.name.family_name or '')),
    Column(_('Company'), 'company', getter=lambda x: x.extended_properties.get('company', '')),
    #Column(_('Company/role'), 'company_role', getter=_get_company_role),
    #Column(_('Given name'), 'given_name', getter=lambda x: x.name.given_name),
    #Column(_('Family name'), 'family_name', getter=lambda x: x.name.family_name),
    Column(_('Phone numbers'), 'phone_numbers',
        getter=lambda x: list_attrs(x.phone_numbers, 'number')),
    Column(_('E-mails'), 'emails',
        getter=lambda x: list_attrs(x.emails, 'address'), email=True),
]
_sharedContactId = _sharedContactFields[0]
_sharedContactWidths = ['%d%%' % x for x in (5, 20, 20, 15, 10, 30)]


@admin_required
def shared_contacts(request):
    sortby, asc = get_sortby_asc(request, [f.name for f in _sharedContactFields])
    
    # getting queries
    query = request.GET.get('q', '')
    query_adv = QuerySearch()
    query_adv.add(request, 'name', 'name.full_name')
    query_adv.add(request, 'notes', 'notes')
    query_adv.add(request, 'email', 'emails.address')
    query_adv.add(request, 'phone', 'phone_numbers.number')
    query_adv.add(request, 'company', None)
    query_adv.add(request, 'role', None)
    
    shared_contacts = SharedContact.all().fetch(1000000)
    
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
    table = Table(_sharedContactFields, _sharedContactId, sortby=sortby, asc=asc)
    table.sort(shared_contacts)
    
    # selecting particular page
    page = get_page(request, shared_contacts, 20)
    
    return render_to_response('shared_contacts_list.html', ctx({
        'table': table.generate(
            page.object_list, page=page, qs_wo_page=qs_wo_page(request),
            widths=_sharedContactWidths, singular='shared contact'),
        'advanced_search': advanced_search,
        'filters': filters,
        'query': dict(general=query, advanced=query_adv.search_by),
        'styles': ['table-list'],
        'scripts': ['table', 'shared-contacts-list'],
    }, 3))


@admin_required
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
            return redirect_saved('shared-contact-details', name=shared_contact.name)
    else:
        form = SharedContactForm(auto_id=True)
    
    return render_to_response('shared_contact_add.html', ctx({
        'form': form,
        'styles': ['table-details'],
    }, 3, back_link=True))


@admin_required
def shared_contact_details(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    shared_contact = SharedContact.all().filter('title', name).get()
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
            
            company_str = new_objects.get('company_str', '')
            shared_contact.extended_properties['company'] = company_str
            
            role_str = new_objects.get('role_str', '')
            shared_contact.extended_properties['role'] = role_str
            
            shared_contact.save()
            return redirect_saved('shared-contact-details', name=shared_contact.name.full_name)
    else:
        real_name = [shared_contact.name.name_prefix,
                shared_contact.name.given_name, shared_contact.name.family_name]
        form = SharedContactForm(initial={
            'full_name': shared_contact.name.full_name,
            'real_name': real_name,
            'company': shared_contact.extended_properties.get('company', ''),
            'role': shared_contact.extended_properties.get('role', ''),
            'notes': shared_contact.notes,
            'emails': '',
        }, auto_id=True)
    
    def remove_email_link(x):
        kwargs = dict(name=shared_contact.title, email=x.address)
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
        kwargs = dict(name=shared_contact.title, phone=x.number)
        return reverse('shared-contact-remove-phone', kwargs=kwargs)
    full_phones = []
    for phone in shared_contact.phone_numbers:
        fmt = '%s &ndash; <a href="%s">Remove</a>'
        full_phones.append(fmt % (phone.number, remove_phone_link(phone)))
    
    return render_to_response('shared_contact_details.html', ctx({
        'shared_contact': shared_contact,
        'form': form,
        'full_emails': full_emails,
        'full_phones': full_phones,
        'saved': request.GET.get('saved', None),
        'styles': ['table-details'],
        'scripts': ['swap-widget'],
    }, 3, back_link=True))


@admin_required
def shared_contact_remove(request, names=None):
    if not names:
        raise ValueError('names = %s' % names)
    
    for name in names.split('/'):
        user = SharedContact.all().filter('title', name).get()
        user.delete()
    
    return redirect('shared-contacts')


@admin_required
def shared_contact_remove_email(request, name=None, email=None):
    if not all((name, email)):
        raise ValueError('name = %s, email = %s' % (name, email))
    
    shared_contact = SharedContact.all().filter('title', name).get()
    if not shared_contact:
        return redirect('shared-contacts')
    
    for index, elem in enumerate(shared_contact.emails):
        if elem.address == email:
            del shared_contact.emails[index]
            break
    shared_contact.save()
    
    return redirect_saved('shared-contact-details', name=name)


@admin_required
def shared_contact_remove_phone(request, name=None, phone=None):
    if not all((name, phone)):
        raise ValueError('name = %s, phone = %s' % (name, phone))
    
    shared_contact = SharedContact.all().filter('title', name).get()
    if not shared_contact:
        return redirect('shared-contacts')
    
    for index, elem in enumerate(shared_contact.phone_numbers):
        if elem.number == phone:
            del shared_contact.phone_numbers[index]
            break
    shared_contact.save()
    
    return redirect_saved('shared-contact-details', name=name)
