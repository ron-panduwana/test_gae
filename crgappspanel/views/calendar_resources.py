from django.utils.translation import ugettext_lazy as _
from crauth import users
from crauth.decorators import has_perm
from crgappspanel.forms import CalendarResourceForm
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.models import Preferences, CalendarResource
from crgappspanel.views.utils import get_sortby_asc, get_page, qs_wo_page, \
        secure_random_chars, redirect_saved
from crlib.navigation import render_with_nav
from crlib import errors


_table_fields = [
    Column(_('Name'), 'common_name', link=True),
    Column(_('Type'), 'type'),
    Column(_('Description'), 'description'),
]
_table_id = Column(None, 'id')
_table_widths = ['%d%%' % x for x in (5, 30, 20, 45)]


@has_perm('read_calendarresource')
def calendar_resources(request):
    user = users.get_current_user()
    sortby, asc = get_sortby_asc(request, [f.name for f in _table_fields])
    
    resources = CalendarResource.all().fetch(1000)
    
    # instantiating table and sorting resources
    table = Table(_table_fields, _table_id, sortby=sortby, asc=asc)
    table.sort(resources)
    
    # selecting particular page
    per_page = Preferences.for_current_user().items_per_page
    page = get_page(request, resources, per_page);
    
    delete_link_title = _('Delete calendar resources')
    if user.has_perm('change_calendarresource'):
        details_link = 'calendar-resource-details'
    else:
        details_link = ''
    return render_with_nav(request, 'calendar_resources_list.html', {
        'table': table.generate(
            page.object_list, page=page, qs_wo_page=qs_wo_page(request),
            widths=_table_widths, singular='calendar resource',
            delete_link_title=delete_link_title, details_link=details_link,
            can_change=user.has_perm('change_calendarresource')),
        'saved': request.session.pop('saved', False),
        'delete_link_title': delete_link_title,
        'delete_question': _('Are you sure you want to delete selected '
                             'calendar resources?'),
    }, help_url='calendar-resources/list')


@has_perm('add_calendarresource')
def calendar_resource_add(request):
    if request.method == 'POST':
        form = CalendarResourceForm(request.POST, auto_id=True)
        if form.is_valid():
            resource = form.create(secure_random_chars(20))
            try:
                resource.save()
                return redirect_saved('calendar-resource-details', request,
                    id=resource.id)
            except errors.EntitySizeTooLarge:
                form.add_error(
                    '__all__',
                    _('One or more of the fields contains too many '
                      'characters.'))
    else:
        form = CalendarResourceForm(auto_id=True)
    
    return render_with_nav(request, 'calendar_resource_add.html', {
        'form': form,
    }, in_section='calendar_resources', help_url='calendar-resources/add')


@has_perm('change_calendarresource')
def calendar_resource_details(request, id=None):
    if not id:
        raise ValueError('id = %s' % id)
    
    resource = CalendarResource.get_by_key_name(id)
    if not resource:
        return redirect('calendar-resources')
    
    if request.method == 'POST':
        form = CalendarResourceForm(request.POST, auto_id=True)
        if form.is_valid():
            form.populate(resource)
            try:
                resource.save()
                return redirect_saved('calendar-resource-details', request,
                    id=resource.id)
            except errors.EntitySizeTooLarge:
                form.add_error(
                    '__all__',
                    _('One or more of the fields contains too many '
                      'characters.'))
    else:
        form = CalendarResourceForm(initial={
            'common_name': resource.common_name,
            'type': resource.type,
            'description': resource.description,
        }, auto_id=True)
    
    return render_with_nav(request, 'calendar_resource_details.html', {
        'calendar_resource': resource,
        'form': form,
        'saved': request.session.pop('saved', False),
    }, in_section='calendar_resources', help_url='calendar-resources/details')


@has_perm('change_calendarresource')
def calendar_resource_remove(request, ids=None):
    if not ids:
        raise ValueError('ids = %s' % ids)
    
    for id in ids.split('/'):
        resource = CalendarResource.get_by_key_name(id)
        if resource:
            resource.delete()
    
    return redirect_saved('calendar-resources', request)
