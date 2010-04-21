import logging
from django.utils.translation import ugettext as _
from django.conf import settings
from gdata import contacts, data
from gdata.contacts import data as contacts_data
from crlib.gdata_wrapper import AtomMapper, simple_mapper, StringProperty


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


class UserEntryMapper(AtomMapper):
    @classmethod
    def create_service(cls):
        from gdata.apps import service
        service = service.AppsService()
        service.domain = settings.APPS_DOMAIN
        return service

    def empty_atom(self):
        from gdata import apps
        return apps.UserEntry(
            login=apps.Login(),
            name=apps.Name(),
            quota=apps.Quota(),
        )

    def create(self, atom):
        return self.service.CreateUser(
            atom.login.user_name, atom.name.family_name,
            atom.name.given_name, atom.login.password,
            atom.login.suspended, password_hash_function='SHA-1')

    def update(self, atom, old_atom):
        atom.login.hash_function_name = 'SHA-1'
        return self.service.UpdateUser(old_atom.login.user_name, atom)

    def retrieve_all(self):
        return self.service.RetrieveAllUsers().entry

    def retrieve(self, user_name):
        return self.service.RetrieveUser(user_name)

    def key(self, atom):
        return atom.login.user_name

    def delete(self, atom):
        self.service.DeleteUser(atom.login.user_name)


class NicknameEntryMapper(AtomMapper):
    create_service = UserEntryMapper.create_service

    def empty_atom(self):
        from gdata import apps
        return apps.NicknameEntry(
            nickname=apps.Nickname(),
            login=apps.Login(),
        )

    def create(self, atom):
        return self.service.CreateNickname(
            atom.login.user_name, atom.nickname.name)

    def retrieve_all(self):
        return self.service.RetrieveAllNicknames().entry

    def retrieve(self, nickname):
        return self.service.RetrieveNickname(nickname)

    def key(self, atom):
        return atom.nickname.name

    def filter_by_user_name(self, user_name):
        return self.service.RetrieveNicknames(user_name).entry

    def delete(self, atom):
        self.service.DeleteNickname(atom.nickname.name)

    #@filter('user')
    #def filter_by_user(self, user_name):
    #    return self.service.RetrieveNicknames(user_name).entry


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
        if atom.org_name is not None:
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

    @classmethod
    def create_service(cls):
        from gdata.contacts import client
        client = client.ContactsClient()
        client.contact_list = settings.APPS_DOMAIN
        return client

    def empty_atom(self):
        return contacts.data.ContactEntry()

    def key(self, atom):
        return atom.find_self_link()

    def create(self, atom):
        return self.service.create_contact(atom)

    def update(self, atom, old_atom):
        return self.service.update(atom)

    def delete(self, atom):
        self.service.delete(atom)

    def retrieve(self, key):
        return self.service.get_entry(
            key, desired_class=contacts.data.ContactEntry)

    def retrieve_all(self):
        return self.retrieve_subset()

    def retrieve_subset(self, limit=1000, offset=0):
        from gdata.contacts.client import ContactsQuery
        query = ContactsQuery()
        query.max_results = limit
        query.start_index = offset + 1
        feed = self.service.get_contacts(query=query)
        return feed.entry


class RelProperty(StringProperty):
    def __init__(self, choices=MAIN_TYPES):
        super(RelProperty, self).__init__('rel', required=False, choices=choices)


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
        from crlib import users
        from gdata.apps.emailsettings.service import EmailSettingsService

        self._user_name = user_name
        user = users.get_current_user()
        self._service = EmailSettingsService()
        self._service.domain = settings.APPS_DOMAIN
        user.client_login(self._service)

    def __getattr__(self, name):
        if name in self._OPERATIONS:
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

