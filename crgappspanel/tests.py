from __future__ import with_statement
import datetime
import logging
import os
import unittest
from appengine_django.models import BaseModel
from google.appengine.ext import db
from gdata.apps.service import AppsForYourDomainException
from crgappspanel.models import *
from crlib.gdata_wrapper import GDataQuery
from crlib.mappers import MAIN_TYPES, PHONE_TYPES, ORGANIZATION_TYPES, \
        WEBSITE_TYPES
from crlib import cache
from crlib.models import GDataIndex, UserCache
from crauth.models import AppsDomain
from crauth.users import _set_current_user


os.environ['SERVER_NAME'] = 'localhost'
os.environ['SERVER_PORT'] = '8000'
os.environ['USER_EMAIL'] = 'test@example.com'
os.environ['USER_IS_ADMIN'] = '1'

TEST_DOMAIN = 'red.lab.cloudreach.co.uk'


with open('google_apps.txt') as f:
    lines = f.readlines()
email, password, domain = [line.strip() for line in lines]
_set_current_user(email, domain)


class BaseGDataTestCase(unittest.TestCase):
    USER_NAME = 'test'
    USER_GIVEN_NAME = 'Test'
    USER_FAMILY_NAME = 'User2'
    NUMBER_OF_USERS = 4
    NUMBER_OF_ADMINS = 2

    def setUp(self):
        AppsDomain.get_or_insert(
            key_name=domain,
            domain=domain,
            admin_email=email,
            admin_password=password)


        idx = GDataIndex.get_by_key_name('%s:GAUser' % TEST_DOMAIN)
        if idx:
            return

        logging.info('Preparing cache...')

        cache.prepare_indexes(TEST_DOMAIN)
        indexes = GDataIndex.all().fetch(100)
        for index in indexes:
            key_parts = index.key().name().split(':')
            key_name = ':'.join(key_parts[:2])
            if len(key_parts) == 3:
                page = key_parts[2]
            else:
                page = 0
            cache.update_cache({
                'key_name': key_name,
                'page': page,
            })

        logging.info('Done.')


class ProvisioningAPITestCase(BaseGDataTestCase):
    def testGetAllUsers(self):
        for user in GAUser.all().fetch(100):
            print user

    def testGetUserByName(self):
        user = GAUser.get_by_key_name(self.USER_NAME)
        self.assertNotEqual(user, None)

    def testSaveUser(self):
        user = GAUser.get_by_key_name(self.USER_NAME)
        user.given_name = 'other_name'
        user.put()

        user.given_name = self.USER_GIVEN_NAME
        user.put()

    def testChangePassword(self):
        user = GAUser.get_by_key_name(self.USER_NAME)
        user.password = 'new_password'
        user.put()

    def testNewUser(self):
        from crlib.errors import DomainUserLimitExceededError
        new_user = GAUser(
            user_name=self.USER_NAME,
            given_name=self.USER_GIVEN_NAME,
            family_name=self.USER_FAMILY_NAME,
            password='some_password',
        )
        self.assertRaises(DomainUserLimitExceededError, new_user.put)

    def testCreateNickname(self):
        user = GAUser.get_by_key_name(self.USER_NAME)
        nickname = GANickname(
            nickname='testnick',
            user=user)
        nickname.put()

        nickname = GANickname.get_by_key_name('testnick')
        self.assertTrue(nickname is not None)
        self.assertEqual(nickname.user.user_name, user.user_name)

    def testDeleteNickname(self):
        user = GAUser.get_by_key_name(self.USER_NAME)
        nickname = GANickname(
            nickname='to_be_deleted',
            user=user)
        nickname.put()

        nickname.delete()

        nickname = GANickname.get_by_key_name('to_be_deleted')
        self.assertEqual(nickname, None)

    def testNicknamesCollection(self):
        user = GAUser.get_by_key_name(self.USER_NAME)
        for nickname in user.nicknames:
            print nickname

    def testRenameUser(self):
        # We need to handle nicknames first
        self.assertTrue(False)
        user = GAUser.get_by_key_name(self.USER_NAME)
        user.user_name = 'new_user'
        user.put()

    def testMultipleChanges(self):
        # We need to handle nicknames first
        self.assertTrue(False)
        user = GAUser.get_by_key_name(self.USER_NAME)
        user.user_name = 'new_user'
        user.given_name = 'Test'
        user.password = 'new_password'
        user.put()

    #def testReferencePropertyOnNormalModel(self):
    #    user = GAUser.get_by_key_name(self.USER_NAME)
    #    test_model = TestModel(user=user)
    #    test_model.put()

    #    test_model = TestModel.all().get()
    #    self.assertEqual(user, test_model.user)

    def testGDataQueryRE(self):
        regexp = GDataQuery._PROPERTY_RE
        correct_properties = (
            'property =', 'property=',
            'property', 'property_with_underscore =',
            'property >', 'property >=',
            'property <', 'property <=',
            'property in', 'property IN',
            'property !=', 'property',
        )
        for property in correct_properties:
            match = regexp.match(property)
            self.assertNotEqual(match, None)

        incorrect_properties = (
            'property with spaces', 'property <>',
        )
        for property in incorrect_properties:
            self.assertEqual(regexp.match(property), None)

    def testGDataQueryFilter(self):
        users = GAUser.all().filter('admin', True).fetch(100)
        self.assertEqual(len(users), self.NUMBER_OF_ADMINS)
        users = GAUser.all().filter('admin', True).filter(
            'user_name', 'kamil').fetch(100)
        self.assertEqual(len(users), 1)

    def testGDataQueryIter(self):
        i = 0
        for user in GAUser.all():
            i += 1
        self.assertEqual(i, self.NUMBER_OF_USERS)

    def testGDataQueryOrder(self):
        for user in GAUser.all().order('admin').order('user_name'):
            print user


class ProvisioningAPIGroupsTestCase(BaseGDataTestCase):
    def testCreateGroup(self):
        existing = GAGroup.all().filter(
            'id', 'some_group@red.lab.cloudreach.co.uk').get()
        if existing is not None:
            existing.delete()
        group = GAGroup(
            id='some_group@' + TEST_DOMAIN,
            name='some group',
            description='this is some group',
            email_permission='Owner').save()

    def testCreateGroupWithMissingProperties(self):
        existing = GAGroup.all().filter(
            'id', 'some_group@' + TEST_DOMAIN).get()
        if existing is not None:
            existing.delete()
        group = GAGroup(
            id='some_group@' + TEST_DOMAIN,
            name='some group',
            description='',
            email_permission='Owner').save()

    def testRetrieveAll(self):
        for group in GAGroup.all():
            print group

    def testRetrieveMembers(self):
        group = GAGroup.all().get()
        print group.key()
        for member in group.members:
            print member
            print member.to_user()
            print member.is_group()

    def testAddUserToGroups(self):
        user = GAUser.get_by_key_name(self.USER_NAME)
        group_ids = (
            'some_group@red.lab.cloudreach.co.uk',
            'sap@red.lab.cloudreach.co.uk',
        )
        GAGroup.add_user_to_groups(user, group_ids)
        member = GAGroupMember.from_user(user)
        for group_id in group_ids:
            group = GAGroup.get_by_key_name(group_id)
            self.assertTrue(member in group.members)

    def testRetrieveGroupsByMember(self):
        user = GAUser.get_by_key_name(self.USER_NAME)
        member = GAGroupMember.from_user(user)
        groups = GAGroup.all().filter('members', member).fetch(100)
        for group in groups:
            print group

    def testUpdateGroup(self):
        group = GAGroup.all().filter(
            'id', 'some_group@red.lab.cloudreach.co.uk').get()
        if group is None:
            group = GAGroup(
                id='some_group@' + TEST_DOMAIN,
                name='some group',
                description='this is some group',
                email_permission='Owner').save()
        group.name = 'new name'
        user = GAUser.get_by_key_name(self.USER_NAME)
        member = GAGroupMember.from_user(user)
        group.members.append(member)
        group.save()

        group = GAGroup.all().filter(
            'id', 'some_group@red.lab.cloudreach.co.uk').get()
        self.assertEqual(group.name, 'new name')
        self.assertTrue(member in group.members)

        group.name = 'some group'
        group.members = []
        group.save()

        group = GAGroup.all().filter(
            'id', 'some_group@red.lab.cloudreach.co.uk').get()
        self.assertEqual(len(group.members), 0)

    def testOwners(self):
        group = GAGroup.all().filter(
            'id', 'some_group@red.lab.cloudreach.co.uk').get()
        if group is None:
            group = GAGroup(
                id='some_group@' + TEST_DOMAIN,
                name='some group',
                description='this is some group',
                email_permission='Owner').save()

        user = GAUser.get_by_key_name(self.USER_NAME)
        owner = GAGroupOwner.from_user(user)
        group.owners.append(owner)
        group.save()

        group = GAGroup.all().filter(
            'id', 'some_group@red.lab.cloudreach.co.uk').get()
        self.assertTrue(owner in group.owners)
        group.owners = []
        group.save()

        group = GAGroup.all().filter(
            'id', 'some_group@red.lab.cloudreach.co.uk').get()
        self.assertEqual(len(group.owners), 0)


class SharedContactsAPITestCase(BaseGDataTestCase):
    def testCreateSharedContact(self):
        contact = SharedContact.all().filter('title', 'Test Contact').get()
        if contact:
            contact.delete()

        email = Email(
            address='test@example.com',
            rel=MAIN_TYPES[0][0],
            primary=True)
        email.save()

        phone_number = PhoneNumber(
            number='555-123-456',
            rel=PHONE_TYPES[0][0],
            primary=True)
        phone_number.save()

        name = Name(full_name='Test Contact')
        name.save()

        organization = Organization(
            name='Some Test Organization',
            rel=ORGANIZATION_TYPES[0][0],
            primary=True)
        organization.save()

        website = Website(
            href='http://www.cloudreach.co.uk/',
            primary=True,
            rel=WEBSITE_TYPES[0][0])
        website.save()

        contact = SharedContact(
            name=name,
            birthday=datetime.date(1990, 10, 10),
            emails=[email],
            phone_numbers=[phone_number],
            websites=[website],
            organization=organization)
        contact.save()

        contact.delete()

    def testGetByKeyName(self):
        contact_1 = SharedContact.all().get()
        key = contact_1.key()
        contact_2 = SharedContact.get_by_key_name(key)
        self.assertEqual(contact_1, contact_2)

    def testUpdateSharedContact(self):
        contact = SharedContact.all().filter('title', 'Updated Name').get()
        if contact:
            logging.warning('Had Updated Name contact')
            logging.warning('contact: %s' % str(contact))
            contact.delete()

        email = Email(
            address='updated@example.com',
            rel=MAIN_TYPES[0][0],
            primary=True)
        email.save()

        name = Name(full_name='Updated Contact')
        name.save()

        contact = SharedContact(
            name=name,
            emails=[email])
        contact.save()

        contact = SharedContact.all().filter('title', 'Updated Contact').get()
        self.assertFalse(contact is None)

        contact.name.full_name = 'Updated Name'
        contact.name.save()
        contact.save()

        contact.delete()

    def testIterSharedContacts(self):
        for contact in SharedContact.all():
            print contact
            self.assertTrue(isinstance(contact, SharedContact))

    def testSharedContactExtendedProperty(self):
        contact = SharedContact.all().filter(
            'title', 'ExtendedProperty Contact').get()
        if contact:
            contact.delete()

        email = Email(
            address='extended@example.com',
            rel=MAIN_TYPES[0][0],
            primary=True)
        email.save()

        name = Name(full_name='ExtendedProperty Contact')
        name.save()

        contact = SharedContact(
            name=name,
            emails=[email],
            extended_properties={
                'some_name': 'some_val',
            })
        contact.save()

        contact = SharedContact.all().filter(
            'title', 'ExtendedProperty Contact').get()
        self.assertEqual(contact.extended_properties['some_name'], 'some_val')


class EmailSettingsAPITestCase(BaseGDataTestCase):
    def testCreateLabel(self):
        user = GAUser.get_by_key_name(self.USER_NAME)
        self.assertNotEqual(user, None)

        response = user.email_settings.create_label('test_label')
        self.assertEqual(response, {'label': 'test_label'})

    def testDisableWebClip(self):
        user = GAUser.get_by_key_name(self.USER_NAME)
        self.assertNotEqual(user, None)

        response = user.email_settings.update_web_clip_settings(False)
        self.assertEqual(response, {'enable': 'false'})


class CalendarResourceAPITestCase(BaseGDataTestCase):
    def testCreateDuplicateResource(self):
        from crlib.errors import EntityExistsError
        def create_duplicate():
            for i in range(2):
                resource = CalendarResource(
                    id='DUPLICATE_RESOURCE',
                    common_name='Test Resource',
                    type='Meeting Room',
                    description='',
                ).save()
        self.assertRaises(EntityExistsError, create_duplicate)

    def testGetAllResources(self):
        resources = CalendarResource.all().fetch(100)
        for resource in resources:
            print resource
            print resource.id
            print resource.description
            print resource.common_name
            print resource.type

    def testCreateResource(self):
        resource = CalendarResource.get_by_key_name('TEST_RESOURCE')
        if resource is not None:
            resource.delete()

        resource = CalendarResource(
            id='TEST_RESOURCE',
            common_name='Test Resource',
            type='Meeting Room',
            description='',
        ).save()

        resource = CalendarResource.get_by_key_name('TEST_RESOURCE')
        self.assertNotEqual(resource, None)
        resource.delete()
        resource = CalendarResource.get_by_key_name('TEST_RESOURCE')
        self.assertEqual(resource, None)

    def testUpdateResource(self):
        resource = CalendarResource.get_by_key_name('TEST_RESOURCE')
        if resource is None:
            resource = CalendarResource(
                id='TEST_RESOURCE',
                common_name='Test Resource',
                type='Meeting Room',
                description='',
            ).save()

        resource.common_name = 'NEW_COMMON_NAME'
        resource.description = 'NEW_DESCRIPTION'
        resource.save()

        resource = CalendarResource.get_by_key_name('TEST_RESOURCE')
        self.assertEqual(resource.common_name, 'NEW_COMMON_NAME')
        self.assertEqual(resource.description, 'NEW_DESCRIPTION')
        resource.delete()

    def testUpdateResourceWithNoDescription(self):
        resource = CalendarResource.get_by_key_name('TEST_RESOURCE')
        if resource is None:
            resource = CalendarResource(
                id='TEST_RESOURCE',
                common_name='Test Resource',
                type='Meeting Room',
                description='',
            ).save()

        resource.description = 'SOME_DESCRIPTION'
        resource.save()

        resource = CalendarResource.get_by_key_name('TEST_RESOURCE')
        self.assertEqual(resource.description, 'SOME_DESCRIPTION')

        resource.description = ''
        resource.save()

        resource = CalendarResource.get_by_key_name('TEST_RESOURCE')
        self.assertNotEqual(resource, None)
        self.assertEqual(resource.description, None)

