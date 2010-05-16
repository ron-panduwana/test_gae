from django.utils.translation import ugettext as _

from crgappspanel.forms import CalendarResourceForm
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.models import CalendarResource
from crgappspanel.views.utils import get_sortby_asc, secure_random_chars, \
        redirect_saved
from crlib.navigation import render_with_nav


_table_fields = [
    Column(_('Name'), 'common_name', link=True),
    Column(_('Type'), 'type'),
    Column(_('Description'), 'description'),
]
_table_id = Column(None, 'id')
_table_field_widths = ['%d%%' % x for x in (5, 30, 20, 45)]


def calendar_resources(request):
    sortby, asc = get_sortby_asc(request, [f.name for f in _table_fields])
    
    resources = CalendarResource.all().fetch(1000)
    
    table = Table(_table_fields, _table_id, sortby='common_name', asc=True)
    table.sort(resources)
    
    return render_with_nav(request, 'calendar_resources_list.html', {
        'table': table.generate(resources, widths=_table_field_widths,
            singular='calendar resource'),
        'saved': request.session.pop('saved', False),
    })


def calendar_resource_add(request):
    if request.method == 'POST':
        form = CalendarResourceForm(request.POST, auto_id=True)
        if form.is_valid():
            resource = form.create(secure_random_chars(20))
            resource.save()
            return redirect_saved('calendar-resource-details', request,
                name=resource.id)
    else:
        form = CalendarResourceForm(auto_id=True)
    
    return render_with_nav(request, 'calendar_resource_add.html', {
        'form': form,
    }, in_section='calendar_resources')


def calendar_resource_details(request, name=None):
    # TODO implement this
    pass
