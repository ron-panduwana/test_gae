from django.utils.translation import ugettext as _

from crgappspanel.helpers.tables import Table, Column
from crgappspanel.models import CalendarResource
from crgappspanel.views.utils import get_sortby_asc, random_password, \
        redirect_saved, render
from crlib.navigation import render_with_nav


_table_fields = [
    Column(_('Name'), 'common_name'),
    Column(_('Type'), 'type'),
    Column(_('Description'), 'description'),
]

_table_field_widths = ['%d%%' % x for x in (5, 30, 20, 45)]


def calendar_resources(request):
    sortby, asc = get_sortby_asc(request, [f.name for f in _table_fields])
    
    resources = CalendarResource.all().fetch(1000)
    
    table = Table(_table_fields, _table_fields[0], sortby='common_name', asc=True)
    table.sort(resources)
    
    return render_with_nav(request, 'calendar_resources_list.html', {
        'table': table.generate(resources, widths=_table_field_widths,
            singular='calendar resource'),
        'saved': request.session.pop('saved', False),
    })


def calendar_resource_add(request):
    # TODO implement this
    pass


def calendar_resource_details(request, name=None):
    # TODO implement this
    pass
