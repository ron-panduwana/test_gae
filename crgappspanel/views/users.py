from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, redirect
from django.utils.translation import ugettext as _

from crgappspanel.forms import UserForm
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.models import GAUser, GANickname
from crgappspanel.views.utils import ctx, get_sortby_asc, random_password
from crlib.users import admin_required
from settings import APPS_DOMAIN


def _get_status(x):
    suspended, admin = getattr(x, 'suspended'), getattr(x, 'admin')
    return _('Suspended') if x.suspended else _('Administrator') if x.admin else ''

_userFields = [
    Column(_('Name'), 'name', getter=lambda x: x.get_full_name(), link=True),
    Column(_('Username'), 'username', getter=lambda x: '%s@%s' % (x.user_name or '', APPS_DOMAIN)),
    Column(_('Status'), 'status', getter=_get_status),
    Column(_('Email quota'), 'quota'),
    Column(_('Roles'), 'roles', getter=lambda x: ''),
    Column(_('Last signed in'), 'last_login', getter=lambda x: '')
]
_userId = Column(None, 'user_name')
_userWidths = ['%d%%' % x for x in (5, 15, 25, 15, 15, 15, 10)]


@admin_required
def users(request):
    sortby, asc = get_sortby_asc(request, [f.name for f in _userFields])
    
    users = GAUser.all().fetch(100)
    
    table = Table(_userFields, _userId, sortby=sortby, asc=asc)
    table.sort(users)
    
    return render_to_response('users_list.html', ctx({
        'table': table.generate(users, widths=_userWidths, singular='user'),
        'styles': ['table-list'],
        'scripts': ['table'],
    }, 2, 2))


@admin_required
def user_create(request):
    if request.method == 'POST':
        form = UserForm(request.POST, auto_id=True)
        if form.is_valid():
            user = form.create()
            user.save()
            return redirect('user-details', name=user.user_name)
    else:
        form = UserForm(auto_id=True)
        form.fields['user_name'].help_text = '@%s' % APPS_DOMAIN
    
    temp_password = random_password(6)
    
    return render_to_response('user_create.html', ctx({
        'form': form,
        'temp_password': temp_password,
    }, 2, 2, True))


@admin_required
def user_details(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    if request.method == 'POST':
        form = UserForm(request.POST, auto_id=True)
        if form.is_valid():
            form.populate(user)
            user.save()
            if form.get_nickname():
                GANickname(user=user, nickname=form.get_nickname()).save()
            return redirect('user-details', name=user.user_name)
    else:
        form = UserForm(initial={
            'user_name': user.user_name,
            'password': '',
            'change_password': user.change_password,
            'full_name': [user.given_name, user.family_name],
            'admin': user.admin,
            'nicknames': '',
        }, auto_id=True)
        form.fields['user_name'].help_text = '@%s' % APPS_DOMAIN
    
    fmt = '<b>%s</b>@%s - <a href="%s">Remove</a>'
    def remove_nick_link(x):
        kwargs = dict(name=user.user_name, nickname=x.nickname)
        return reverse('user-remove-nickname', kwargs=kwargs)
    full_nicknames = [fmt % (nick.nickname, APPS_DOMAIN, remove_nick_link(nick)) for nick in user.nicknames]
    return render_to_response('user_details.html', ctx({
        'user': user,
        'form': form,
        'full_nicknames': full_nicknames,
        'styles': ['table-details', 'user-details'],
        'scripts': ['expand-field', 'swap-widget', 'user-details'],
    }, 2, 2, True))


def user_suspend_restore(request, name=None, suspend=None):
    if not name or suspend is None:
        raise ValueError('name = %s, suspend = %s' % (name, str(suspend)))
    
    user = GAUser.get_by_key_name(name)
    user.suspended = suspend
    user.save()
    
    return redirect('user-details', name=user.user_name)


@admin_required
def user_suspend(request, name=None):
    return user_suspend_restore(request, name=name, suspend=True)


@admin_required
def user_restore(request, name=None):
    return user_suspend_restore(request, name=name, suspend=False)


@admin_required
def user_remove(request, names=None):
    if not names:
        raise ValueError('names = %s' % names)
    
    for name in names.split('/'):
        user = GAUser.get_by_key_name(name)
        user.delete()
    
    return redirect('users')


@admin_required
def user_remove_nickname(request, name=None, nickname=None):
    if not all((name, nickname)):
        raise ValueError('name = %s, nickname = %s' % (name, nickname))
    
    nickname = GANickname.get_by_key_name(nickname)
    nickname.delete()
    
    return redirect('user-details', name=name)
