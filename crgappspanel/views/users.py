from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

import auth
from auth.decorators import login_required
from crgappspanel import consts
from crgappspanel.forms import UserForm, UserEmailSettingsForm, \
    UserEmailFiltersForm, UserEmailAliasesForm
from crgappspanel.helpers.misc import ValueWithRemoveLink
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.models import GAUser, GANickname
from crgappspanel.views.utils import ctx, get_sortby_asc, random_password, \
        redirect_saved, render


FORWARD_ACTIONS = dict(
    ek=consts.EMAIL_ACTION_KEEP,
    ea=consts.EMAIL_ACTION_ARCHIVE,
    ed=consts.EMAIL_ACTION_DELETE)
POP3_ENABLE_FORS = dict(
    ea=consts.EMAIL_ENABLE_FOR_ALL_MAIL,
    en=consts.EMAIL_ENABLE_FOR_MAIL_FROM_NOW_ON)


def _get_status(x):
    suspended, admin = getattr(x, 'suspended'), getattr(x, 'admin')
    return _('Suspended') if x.suspended else _('Administrator') if x.admin else ''

def _userFieldsGen(domain):
    return [
        Column(_('Name'), 'name', getter=lambda x: x.get_full_name(), link=True),
        Column(_('Username'), 'username', getter=lambda x: '%s@%s' % (x.user_name or '', domain)),
        Column(_('Status'), 'status', getter=_get_status),
        Column(_('Email quota'), 'quota'),
        Column(_('Roles'), 'roles', getter=lambda x: ''),
        Column(_('Last signed in'), 'last_login', getter=lambda x: '')
    ]
_userId = Column(None, 'user_name')
_userWidths = ['%d%%' % x for x in (5, 15, 25, 15, 15, 15, 10)]


@login_required
def users(request):
    domain = auth.users.get_current_user().domain().domain
    _userFields = _userFieldsGen(domain)
    sortby, asc = get_sortby_asc(request, [f.name for f in _userFields])
    
    users = GAUser.all().fetch(100)
    
    table = Table(_userFields, _userId, sortby=sortby, asc=asc)
    table.sort(users)
    
    return render(request, 'users_list.html', ctx({
        'table': table.generate(users, widths=_userWidths, singular='user'),
        'scripts': ['table'],
    }, 2, 2))


@login_required
def user_create(request):
    domain = auth.users.get_current_user().domain().domain
    
    if request.method == 'POST':
        form = UserForm(request.POST, auto_id=True)
        if form.is_valid():
            user = form.create()
            user.save()
            return redirect('user-details', name=user.user_name)
    else:
        form = UserForm(auto_id=True)
        form.fields['user_name'].help_text = '@%s' % domain
    
    temp_password = random_password(6)
    
    return render(request, 'user_create.html', ctx({
        'form': form,
        'temp_password': temp_password,
    }, 2, 2, back_link=True))


@login_required
def user_details(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    domain = auth.users.get_current_user().domain().domain
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
            return redirect_saved('user-details', request, name=user.user_name)
    else:
        form = UserForm(initial={
            'user_name': user.user_name,
            'password': '',
            'change_password': user.change_password,
            'full_name': [user.given_name, user.family_name],
            'admin': user.admin,
            'nicknames': '',
        }, auto_id=True)
        form.fields['user_name'].help_text = '@%s' % domain
    
    def get_email(x):
        return '%s@%s' % (x, domain)
    def remove_nick_link(x):
        kwargs = dict(name=user.user_name, nickname=x.nickname)
        return reverse('user-remove-nickname', kwargs=kwargs)
    full_nicknames = [ValueWithRemoveLink(get_email(nick.nickname), remove_nick_link(nick)) for nick in user.nicknames]
    #full_nicknames = ['abc', 'def']
    return render(request, 'user_details.html', ctx({
        'user': user,
        'form': form,
        'full_nicknames': full_nicknames,
        'saved': request.session.pop('saved', False),
        'scripts': ['expand-field', 'swap-widget', 'user-details'],
    }, 2, 2, 1, back_link=True, sections_args=dict(user=name)))


@login_required
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
            general = {}
            
            language = data['language']
            if language:
                ret = user.email_settings.update_language(language)
            
            forward = data['forward']
            forward_to = data['forward_to']
            forward_action = FORWARD_ACTIONS.get(forward)
            if forward_action is not None:
                user.email_settings.update_forwarding(True,
                    forward_to=forward_to, action=forward_action)
            elif forward == 'd':
                user.email_settings.update_forwarding(False)
            
            pop3 = data['pop3']
            pop3_enable_for = POP3_ENABLE_FORS.get(pop3)
            if pop3_enable_for is not None:
                user.email_settings.update_pop(True,
                    enable_for=pop3_enable_for, action=consts.EMAIL_ACTION_KEEP)
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
                user.email_settings.update_signature(signature_new or '')
            
            return redirect_saved('user-email-settings',
                request, name=user.user_name)
    else:
        form = UserEmailSettingsForm(initial={}, auto_id=True)
    
    return render(request, 'user_email_settings.html', ctx({
        'user': user,
        'form': form,
        'saved': request.session.pop('saved', False),
    }, 2, 2, 2, back_link=True, sections_args=dict(user=name)))


def user_email_filters(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    if request.method == 'POST':
        form = UserEmailFiltersForm(request.POST, auto_id=True)
        if form.is_valid():
            data = dict((key, value) for key, value in form.cleaned_data.iteritems() if value)
            
            has_attachment = data.get('has_attachment')
            if has_attachment == 'e':
                data['has_attachment'] = True
            
            user.email_settings.create_filter(**data)
            return redirect_saved('user-email-filters',
                request, name=user.user_name)
    else:
        form = UserEmailFiltersForm(initial={}, auto_id=True)
    
    return render(request, 'user_email_filters.html', ctx({
        'user': user,
        'form': form,
        'saved': request.session.pop('saved', False),
    }, 2, 2, 3, back_link=True, sections_args=dict(user=name)))


def user_email_aliases(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    if request.method == 'POST':
        form = UserEmailAliasesForm(request.POST, auto_id=True)
        if form.is_valid():
            data = dict((key, value) for key, value in form.cleaned_data.iteritems() if value)
            
            user.email_settings.create_send_as_alias(**data)
            return redirect_saved('user-email-aliases',
                request, name=user.user_name)
    else:
        form = UserEmailAliasesForm(initial={}, auto_id=True)
    
    return render(request, 'user_email_aliases.html', ctx({
        'user': user,
        'form': form,
        'saved': request.session.pop('saved', False),
        'scripts': ['swap-widget']
    }, 2, 2, 4, back_link=True, sections_args=dict(user=name)))


def user_suspend_restore(request, name=None, suspend=None):
    if not name or suspend is None:
        raise ValueError('name = %s, suspend = %s' % (name, str(suspend)))
    
    user = GAUser.get_by_key_name(name)
    user.suspended = suspend
    user.save()
    
    return redirect('user-details', name=user.user_name)


@login_required
def user_suspend(request, name=None):
    return user_suspend_restore(request, name=name, suspend=True)


@login_required
def user_restore(request, name=None):
    return user_suspend_restore(request, name=name, suspend=False)


@login_required
def user_remove(request, names=None):
    if not names:
        raise ValueError('names = %s' % names)
    
    for name in names.split('/'):
        user = GAUser.get_by_key_name(name)
        user.delete()
    
    return redirect('users')


@login_required
def user_remove_nickname(request, name=None, nickname=None):
    if not all((name, nickname)):
        raise ValueError('name = %s, nickname = %s' % (name, nickname))
    
    nickname = GANickname.get_by_key_name(nickname)
    nickname.delete()
    
    return redirect('user-details', name=name)
