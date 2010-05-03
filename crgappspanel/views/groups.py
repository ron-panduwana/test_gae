from django.shortcuts import render_to_response
from django.utils.translation import ugettext as _

from crgappspanel.helpers.tables import Table, Column
from crgappspanel.sample_data import get_sample_groups
from crgappspanel.views.utils import ctx, get_sortby_asc
from crlib.users import admin_required


_groupFields = [
    Column(_('Name'), 'title', link=True),
    Column(_('Email address'), 'name'),
    Column(_('Type'), 'kind'),
]
_groupId = _groupFields[1]
_groupWidths = ['%d%%' % x for x in (5, 40, 40, 15)]


@admin_required
def groups(request):
    sortby, asc = get_sortby_asc(request, [f.name for f in _groupFields])
    
    groups = get_sample_groups()
    table = Table(_groupFields, _groupId, sortby=sortby, asc=asc)
    table.sort(groups)
    
    return render_to_response('groups_list.html', ctx({
        'table': table.generate(groups, widths=_groupWidths, singular='group'),
        'scripts': ['table'],
    }, 2, 1))
