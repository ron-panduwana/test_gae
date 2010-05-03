from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, redirect
from django.utils.translation import ugettext as _

from crgappspanel.forms import UserForm, UserEmailSettingsForm
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.models import GAUser, GANickname
from crgappspanel.views.utils import ctx, get_sortby_asc, random_password, redirect_saved
from crlib.users import admin_required
from settings import APPS_DOMAIN


EMAIL_ACTION_KEEP = 'KEEP'
EMAIL_ACTION_ARCHIVE = 'ARCHIVE'
EMAIL_ACTION_DELETE = 'DELETE'

EMAIL_ENABLE_FOR_ALL_MAIL = 'ALL_MAIL'
EMAIL_ENABLE_FOR_MAIL_FROM_NOW_ON = 'MAIL_FROM_NOW_ON'

FORWARD_ACTIONS = dict(ek=EMAIL_ACTION_KEEP, ea=EMAIL_ACTION_ARCHIVE, ed=EMAIL_ACTION_DELETE)
POP3_ENABLE_FORS = dict(ea=EMAIL_ENABLE_FOR_ALL_MAIL, en=EMAIL_ENABLE_FOR_MAIL_FROM_NOW_ON)


def _get_status(x):
    suspended, admin = getattr(x, 'suspended'), getattr(x, 'admin')
    return _('Suspended') if x.suspended else _('Administrator') if x.admin else ''

_userFields = [
    Column(_('Name'), 'name', getter=lambda x: x.get_full_name(), link=True),
    Column(_('Username'), 'username', getter=lambda x: '%s@%s' % (x.user_name or '', APPS_DOMAIN), email=True),
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
    }, 2, 2, back_link=True))


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
            return redirect_saved('user-details', name=user.user_name)
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
        'saved': request.GET.get('saved', None),
        'styles': ['table-details'],
        'scripts': ['expand-field', 'swap-widget', 'user-details'],
    }, 2, 2, 1, back_link=True, sections_args=dict(user=name)))


@admin_required
def user_email_settings(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    if request.method == 'POST':
        form = UserEmailSettingsForm(request.POST, auto_id=True)
        if form.is_valid():
            data = form.cleaned_data
            
            forward = data['forward']
            forward_to = data['forward_to']
            forward_action = FORWARD_ACTIONS.get(forward, None)
            if forward_action is not None:
                user.email_settings.update_forwarding(True,
                    forward_to=forward_to, action=forward_action)
            elif forward == 'd':
                user.email_settings.update_forwarding(False)
            
            pop3 = data['pop3']
            pop3_enable_for = POP3_ENABLE_FORS.get(pop3, None)
            if pop3_enable_for is not None:
                user.email_settings.update_pop(True,
                    enable_for=pop3_enable_for, action=EMAIL_ACTION_KEEP)
            elif pop3 == 'd':
                user.email_settings.update_pop(False)
            
            imap = form.get_boolean('imap')
            if imap is not None:
                user.email_settings.update_imap(imap)
            
            messages_per_page = data['messages_per_page']
            if messages_per_page in ('25', '50', '100'):
                general['page_size'] = int(messages_per_page)
            
            web_clips = form.get_boolean('web_clips')
            if web_clips is not None:
                user.email_settings.update_web_clip_settings(web_clips)
            
            general = {}
            general['snippets'] = form.get_boolean('snippets')
            general['shortcuts'] = form.get_boolean('shortcuts')
            general['arrows'] = form.get_boolean('arrows')
            general['unicode'] = form.get_boolean('unicode')
            general = dict((key, value) for key, value in general.iteritems() if value is not None)
            
            if len(general) > 0:
                user.email_settings.update_general(**general)
            
            signature = form.get_boolean('signature')
            signature_new = data['signature_new']
            if signature is not None:
                user.email_settings.update_signature(signature_new if signature else '')
            
            return redirect_saved('user-email-settings', name=user.user_name)
    else:
        form = UserEmailSettingsForm(initial={}, auto_id=True)
    
    return render_to_response('user_email_settings.html', ctx({
        'user': user,
        'form': form,
        'saved': request.GET.get('saved'),
        'styles': ['table-details', 'user-email-settings'],
    }, 2, 2, 2, back_link=True, sections_args=dict(user=name)))


def user_email_filters(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    return render_to_response('user_email_filters.html', ctx({
        'user': user,
        'saved': request.GET.get('saved'),
        'styles': ['table-details'],
    }, 2, 2, 3, back_link=True, sections_args=dict(user=name)))


def user_email_aliases(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    return render_to_response('user_email_aliases.html', ctx({
        'user': user,
        'saved': request.GET.get('saved'),
        'styles': ['table-details'],
    }, 2, 2, 4, back_link=True, sections_args=dict(user=name)))


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
