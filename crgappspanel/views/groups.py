from django.utils.translation import ugettext as _

from crgappspanel.forms import GroupForm
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.models import GAGroup
#from crgappspanel.sample_data import get_sample_groups
from crgappspanel.views.utils import ctx, get_sortby_asc, render
from auth.decorators import login_required
from settings import APPS_DOMAIN


_groupFields = [
    Column(_('Name'), 'name', link=True),
    Column(_('Email address'), 'email', getter=lambda x: x.id),
    Column(_('Email permission'), 'email_permission'),
]
_groupId = Column(None, 'id', getter=lambda x: x.id.partition('@')[0])
_groupWidths = ['%d%%' % x for x in (5, 40, 40, 15)]


@login_required
def groups(request):
    sortby, asc = get_sortby_asc(request, [f.name for f in _groupFields])
    
    groups = GAGroup.all().fetch(1000000)
    table = Table(_groupFields, _groupId, sortby=sortby, asc=asc)
    table.sort(groups)
    
    return render(request, 'groups_list.html', ctx({
        'table': table.generate(groups, widths=_groupWidths, singular='group'),
        'scripts': ['table'],
    }, 2, 1))


@login_required
def group_details(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    group = GAGroup.all().filter('id', '%s@%s' % (name, APPS_DOMAIN)).get()
    if not group:
        return redirect('groups')
    
    if request.method == 'POST':
        form = GroupForm(request.POST, auto_id=True)
        if form.is_valid():
            # TODO do sth
            pass
    else:
        form = GroupForm(initial={
            'id': group.id.partition('@')[0],
            'name': group.name,
            'description': group.description,
            'email_permission': group.email_permission,
        }, auto_id=True)
        form.fields['id'].help_text = '@%s' % APPS_DOMAIN
    
    return render(request, 'group_details.html', ctx({
        'group': group,
        'form': form,
        'saved': request.GET.get('saved'),
    }, 2, 1, 1, back_link=True, sections_args=dict(group=name)))


@login_required
def group_members(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    group = GAGroup.all().filter('id', '%s@%s' % (name, APPS_DOMAIN)).get()
    if not group:
        return redirect('groups')
    
    owners = ('[email=%s, type=%s]' % (owner.email, owner.type) for owner in group.owners)
    members = ('[id=%s, direct_member=%s, type=%s]' % (member.id, member.direct_member, member.type) for member in group.members)
    
    return render(request, 'group_members.html', ctx({
        'group': group,
        'owners': owners,
        'members': members,
    }, 2, 1, 2, back_link=True, sections_args=dict(group=name)))
