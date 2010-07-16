import logging
import re
from google.appengine.api import memcache
from django.utils.translation import ugettext as _
from django.conf import settings
from gdata import contacts, data
from gdata.contacts import data as contacts_data
from gdata.calendar_resource import data as calendar_resource
from gdata.apps import PropertyEntry
from gdata.apps.groups import service as groups
from atom import AtomBase
from crlib.gdata_wrapper import AtomMapper, simple_mapper, StringProperty
from crlib.signals import gauser_renamed
from crlib.errors import apps_for_your_domain_exception_wrapper


# Constants

MAIN_TYPES = (
    (contacts.REL_HOME, _('Home')),
    (contacts.REL_WORK, _('Work')),
    (contacts.REL_OTHER, _('Other')),
)


ORGANIZATION_TYPES = (
    (contacts.REL_WORK, _('Work')),
    (contacts.REL_OTHER, _('Other')),
)


WEBSITE_TYPES = (
    ('home-page', _('Home Page')),
    ('blog', _('Blog')),
    ('profile', _('Profile')),
    ('home', _('Home Page')),
    ('work', _('Work')),
    ('other', _('Other')),
    ('ftp', _('FTP')),
)


PHONE_TYPES = (
    (contacts.PHONE_CAR, _('Car')),
    (contacts.PHONE_FAX, _('Fax')),
    (contacts.PHONE_GENERAL, _('General')),
    (contacts.PHONE_HOME, _('Home')),
    (contacts.PHONE_HOME_FAX, _('Home Fax')),
    (contacts.PHONE_INTERNAL, _('Internal')),
    (contacts.PHONE_MOBILE, _('Mobile')),
    (contacts.PHONE_OTHER, _('Other')),
    (contacts.PHONE_PAGER, _('Pager')),
    (contacts.PHONE_SATELLITE, _('Satellite')),
    (contacts.PHONE_VOIP, _('VOIP')),
    (contacts.PHONE_WORK, _('Work')),
    (contacts.PHONE_WORK_FAX, _('Work Fax')),
    (contacts.PHONE_WORK_MOBILE, _('Work Mobile')),
    (contacts.PHONE_WORK_PAGER, _('Work Pager')),
    (contacts.PHONE_MAIN, _('Main')),
    (contacts.PHONE_ASSISTANT, _('Assistant')),
    (contacts.PHONE_CALLBACK, _('Callback')),
    (contacts.PHONE_COMPANY_MAIN, _('Company Main')),
    (contacts.PHONE_ISDN, _('ISDN')),
    (contacts.PHONE_OTHER_FAX, _('Other Fax')),
    (contacts.PHONE_RADIO, _('Radio')),
    (contacts.PHONE_TELEX, _('Telex')),
    (contacts.PHONE_TTY_TDD, _('TTY TDD')),
)


GROUP_EMAIL_PERMISSIONS = (
    (groups.PERMISSION_OWNER, _('Owner')),
    (groups.PERMISSION_MEMBER, _('Member')),
    (groups.PERMISSION_DOMAIN, _('Domain')),
    (groups.PERMISSION_ANYONE, _('Anyone')),
)


# Mappers

class UserEntryMapper(AtomMapper):
    @classmethod
    def create_service(cls, domain):
        from gdata.apps import service
        service = service.AppsService()
        service.domain = domain
        return service

    def empty_atom(self):
        from gdata import apps
        return apps.UserEntry(
            login=apps.Login(),
            name=apps.Name(),
            quota=apps.Quota(),
        )

    @apps_for_your_domain_exception_wrapper
    def create(self, atom):
        return self.service.CreateUser(
            atom.login.user_name, atom.name.family_name,
            atom.name.given_name, atom.login.password,
            atom.login.suspended, password_hash_function='SHA-1')

    @apps_for_your_domain_exception_wrapper
    def update(self, atom, old_atom):
        atom.login.hash_function_name = 'SHA-1'
        new_atom = self.service.UpdateUser(old_atom.login.user_name, atom)
        if old_atom.login.user_name != atom.login.user_name:
            gauser_renamed.send(sender=self.service.domain,
                                old_name=old_atom.login.user_name,
                                new_name=atom.login.user_name)
        return new_atom

    def retrieve_page(self, cursor=None):
        if cursor:
            from gdata.apps import UserFeedFromString
            feed = self.service.Get(cursor, converter=UserFeedFromString)
        else:
            feed = self.service.RetrievePageOfUsers()
        cursor = feed.GetNextLink()
        cursor = cursor and cursor.href
        return (feed, cursor)

    def retrieve(self, user_name):
        return self.service.RetrieveUser(user_name)

    def key(self, atom):
        return atom.login.user_name

    def delete(self, atom):
        self.service.DeleteUser(atom.login.user_name)


class _DictAtom(dict):
    """Helper class making a dictionary act as an Atom object.

    Which basically means obj['key'] is equivalent to obj.key.

    """

    def __hash__(self):
        return hash(unicode(self))

    def __getattr__(self, key):
        if self.has_key(key):
            return self[key]
        raise AttributeError

    def __setattr__(self, key, value):
        self[key] = value


class MemberEntry(_DictAtom):
    def __hash__(self):
        return hash(self.memberId)


class MemberEntryMapper(AtomMapper):
    def key(self, atom):
        return atom.memberId

    def empty_atom(self):
        return MemberEntry()

    def clone_atom(self, atom):
        return MemberEntry(atom)


class OwnerEntry(_DictAtom):
    def __hash__(self):
        return hash(self.email)


class OwnerEntryMapper(AtomMapper):
    def key(self, atom):
        return atom.email

    def empty_atom(self):
        return OwnerEntry()

    def clone_atom(self, atom):
        return OwnerEntry(atom)


class GroupEntry(_DictAtom):
    def __init__(self, mapper, *args, **kwargs):
        self._mapper = mapper
        super(GroupEntry, self).__init__(*args, **kwargs)

    @property
    def members(self):
        if self.has_key('members'):
            return self['members']
        _members = self._mapper.service.RetrieveAllMembers(self.groupId)
        self['members'] = [MemberEntry(member) for member in _members]
        return self['members']

    @property
    def owners(self):
        if self.has_key('owners'):
            return self['owners']
        _owners = self._mapper.service.RetrieveAllOwners(self.groupId)
        self['owners'] = [OwnerEntry(owner) for owner in _owners]
        return self['owners']


class GroupEntryMapper(AtomMapper):
    def key(self, atom):
        return atom.groupId

    def create_service(self, domain):
        from gdata.apps.groups import service
        service = service.GroupsService()
        service.domain = domain
        return service

    def empty_atom(self):
        return GroupEntry(self)

    def clone_atom(self, atom):
        return GroupEntry(self, atom)

    @apps_for_your_domain_exception_wrapper
    def create(self, atom):
        new_group = self.service.CreateGroup(
            atom.groupId, atom.groupName, atom.description,
            atom.emailPermission)
        return GroupEntry(self, new_group)

    def _update_members(self, atom, old_atom):
        old_members = set(old_atom.members)
        new_members = set(atom.members)

        for member in old_members - new_members:
            self.service.RemoveMemberFromGroup(member.memberId, atom.groupId)

        for member in new_members - old_members:
            self.service.AddMemberToGroup(member.memberId, atom.groupId)

    def _update_owners(self, atom, old_atom):
        old_owners = set(old_atom.owners)
        new_owners = set(atom.owners)

        for owner in old_owners - new_owners:
            self.service.RemoveOwnerFromGroup(owner.email, atom.groupId)

        for owner in new_owners - old_owners:
            self.service.AddOwnerToGroup(owner.email, atom.groupId)

    def update(self, atom, old_atom):
        self._update_members(atom, old_atom)
        self._update_owners(atom, old_atom)

        if atom != old_atom:
            updated_group = self.service.UpdateGroup(
                atom.groupId, atom.groupName, atom.description,
                atom.emailPermission)
            return GroupEntry(self, updated_group)
        else:
            return atom

    def delete(self, atom):
        self.service.DeleteGroup(atom.groupId)

    def retrieve_all(self, use_cache=True):
        entries = super(GroupEntryMapper, self).retrieve_all(use_cache)
        properties_list = []
        for property_entry in entries:
            properties_list.append(
                self.service._PropertyEntry2Dict(property_entry))
        return [GroupEntry(self, entry) for entry in properties_list]

    def retrieve_page(self, previous=None):
        if previous:
            next = previous.GetNextLink()
            if next:
                from gdata.apps import PropertyFeedFromString
                return self.service.Get(
                    next.href, converter=PropertyFeedFromString)
            else:
                return False
        else:
            uri = self.service._ServiceUrl('group', True, '', '', '')
            return self.service._GetPropertyFeed(uri)

    def retrieve(self, group_id):
        return GroupEntry(self, self.service.RetrieveGroup(group_id))

    def filter_by_members(self, member):
        groups = self.service.RetrieveGroups(member, 'false')
        return [GroupEntry(self, entry) for entry in groups]


class NicknameEntryMapper(AtomMapper):
    create_service = UserEntryMapper.create_service

    def empty_atom(self):
        from gdata import apps
        return apps.NicknameEntry(
            nickname=apps.Nickname(),
            login=apps.Login(),
        )

    @apps_for_your_domain_exception_wrapper
    def create(self, atom):
        return self.service.CreateNickname(
            atom.login.user_name, atom.nickname.name)

    def retrieve_page(self, cursor=None):
        if cursor:
            from gdata.apps import NicknameFeedFromString
            feed = self.service.Get(cursor, converter=NicknameFeedFromString)
        else:
            feed = self.service.RetrievePageOfNicknames()
        cursor = feed.GetNextLink()
        cursor = cursor and cursor.href
        return (feed, cursor)

    def retrieve(self, nickname):
        return self.service.RetrieveNickname(nickname)

    def key(self, atom):
        return atom.nickname.name

    def filter_by_user_name(self, user_name):
        return self.service.RetrieveNicknames(user_name).entry

    def delete(self, atom):
        self.service.DeleteNickname(atom.nickname.name)


PhoneNumberMapper = simple_mapper(data.PhoneNumber, 'text')
EmailMapper = simple_mapper(data.Email, 'address')
PostalAddressMapper = simple_mapper(data.PostalAddress, 'text')
ExtendedPropertyMapper = simple_mapper(data.ExtendedProperty, 'name')
WebsiteMapper = simple_mapper(contacts_data.Website, 'href')
BirthdayMapper = simple_mapper(contacts_data.Birthday, 'when')


class OrganizationMapper(AtomMapper):
    optional = {
        'name': data.OrgName,
        'title': data.OrgTitle,
        'job_description': data.OrgJobDescription,
        'department': data.OrgDepartment,
        'symbol': data.OrgSymbol,
    }

    def empty_atom(self):
        return data.Organization()

    def key(self, atom):
        if hasattr(atom, 'org_name') and atom.org_name is not None:
            return atom.org_name.text
        return 'unnamed_organization'


class NameMapper(AtomMapper):
    optional = {
        'given_name': data.GivenName,
        'additional_name': data.AdditionalName,
        'family_name': data.FamilyName,
        'name_prefix': data.NamePrefix,
        'name_suffix': data.NameSuffix,
        'full_name': data.FullName,
    }

    def empty_atom(self):
        return data.Name()

    def key(self, atom):
        return atom.full_name.text


class SharedContactEntryMapper(AtomMapper):
    from atom.data import Content
    optional = {
        'content': Content,
        'birthday': contacts_data.Birthday,
    }
    RE_SELF_LINK = re.compile(
        r'http://www.google.com/m8/feeds/contacts/'
        r'(?:[^/]+)/full/(?P<id>[a-f0-9]+)$')
    SELF_LINK = 'http://www.google.com/m8/feeds/contacts/%s/full/%s'
    ITEMS_PER_PAGE = 100

    @classmethod
    def create_service(cls, domain):
        from gdata.contacts import client
        client = client.ContactsClient()
        client.contact_list = domain
        return client

    def empty_atom(self):
        return contacts.data.ContactEntry()

    def key(self, atom):
        link = atom.find_self_link()
        match = self.RE_SELF_LINK.match(link)
        return match.groups(0)[0]

    def create(self, atom):
        return self.service.create_contact(atom)

    def update(self, atom, old_atom):
        return self.service.update(atom)

    def delete(self, atom):
        self.service.delete(atom)

    def retrieve(self, key):
        link = self.SELF_LINK % (self.service.contact_list, key)
        return self.service.get_entry(
            link, desired_class=contacts.data.ContactEntry)

    def retrieve_page(self, cursor=None):
        if cursor:
            feed = self._retrieve_subset(
                limit=self.ITEMS_PER_PAGE, offset=cursor)
        else:
            feed = self._retrieve_subset(limit=self.ITEMS_PER_PAGE)
        total_results = int(feed.total_results.text)
        start_index = int(feed.start_index.text)
        if start_index - 1 + len(feed.entry) < total_results:
            cursor = start_index + self.ITEMS_PER_PAGE
        else:
            cursor = None
        return (feed, cursor)

    def _retrieve_subset(self, limit=1000, offset=1):
        from gdata.contacts.client import ContactsQuery
        query = ContactsQuery()
        query.max_results = limit
        query.start_index = offset
        feed = self.service.get_contacts(query=query)
        return feed


class RelProperty(StringProperty):
    def __init__(self, choices=MAIN_TYPES, **kwargs):
        super(RelProperty, self).__init__(
            'rel', required=False, choices=choices, **kwargs)


class _EmailSettingsWrapper(object):
    _OPERATIONS = {
        'create_label': 'CreateLabel',
        'create_filter': 'CreateFilter',
        'create_send_as_alias': 'CreateSendAsAlias',
        'update_web_clip_settings': 'UpdateWebClipSettings',
        'update_forwarding': 'UpdateForwarding',
        'update_pop': 'UpdatePop',
        'update_imap': 'UpdateImap',
        'update_vacation': 'UpdateVacation',
        'update_signature': 'UpdateSignature',
        'update_language': 'UpdateLanguage',
        'update_general': 'UpdateGeneral',
    }
    KEEP = 'KEEP'
    ARCHIVE = 'ARCHIVE'
    DELETE = 'DELETE'
    ALL_MAIL = 'ALL_MAIL'
    MAIL_FROM_NOW_ON = 'MAIL_FROM_NOW_ON'

    def __init__(self, user_name):
        from crauth import users
        from gdata.apps.emailsettings.service import EmailSettingsService

        self._user_name = user_name
        user = users.get_current_user()
        self._service = EmailSettingsService()
        self._service.domain = user.domain_name
        user.client_login(self._service)

    def __getattr__(self, name):
        if name in self._OPERATIONS:
            @apps_for_your_domain_exception_wrapper
            def fun(*args, **kwargs):
                _orig_fun = getattr(self._service, self._OPERATIONS[name])
                return _orig_fun(self._user_name, *args, **kwargs)
            fun.__name__ = name
            return fun
        raise AttributeError


class EmailSettingsProperty(object):
    def __get__(self, model_instance, model_class):
        if model_instance is None or not hasattr(model_instance, 'user_name'):
            raise Exception(
                'EmailSettingsProperty may only be used with model instances '
                'defining user_name property.')
        return _EmailSettingsWrapper(model_instance.user_name)


class CalendarResourceEntryMapper(AtomMapper):
    @classmethod
    def create_service(cls, domain):
        from gdata.calendar_resource import client
        client = client.CalendarResourceClient(domain=domain)
        client.ssl = True
        return client

    def empty_atom(self):
        return calendar_resource.CalendarResourceEntry()

    def key(self, atom):
        return atom.resource_id

    def create(self, atom):
        from gdata.client import RequestError
        try:
            return self.service.create_resource(
                atom.resource_id, atom.resource_common_name,
                atom.resource_description, atom.resource_type,
            )
        except RequestError, e:
            if 'EntityExists' in e.body:
                raise EntityExistsError()
            raise

    def update(self, atom, old_atom):
        # There is a bug in Calendar Resources GData API: if
        # resource_description is set to non-empty value and then we try to
        # set it to '' or None - the change is not permanent -
        # resource_description returns to its previous non-empty value. To
        # fix this behaviour for now we simply delete the resource and then
        # recreate it with empty resource_description.
        if not atom.resource_description:
            self.delete(old_atom)
            return self.create(atom)
        return self.service.update_resource(
            old_atom.resource_id, atom.resource_common_name,
            atom.resource_description, resource_type=atom.resource_type)

    def delete(self, atom):
        self.service.delete_resource(atom.resource_id)

    def retrieve(self, resource_id):
        try:
            return self.service.get_resource(resource_id=resource_id)
        except Exception, e:
            if not 'EntityDoesNotExist' in e.body:
                logging.exception('CalendarResourceEntryMapper.resource')
            return None

    def retrieve_all(self):
        return self.service.get_resource_feed().entry


