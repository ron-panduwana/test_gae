from __future__ import with_statement

import logging
import os
import unittest
from appengine_django.models import BaseModel
from google.appengine.ext import db
from gdata.apps.service import AppsForYourDomainException
from crgappspanel.models import GAUser, GANickname, Role, TestModel
from crlib.gdata_wrapper import GDataQuery
from crlib.users import _set_testing_user


os.environ['SERVER_NAME'] = 'localhost'
os.environ['SERVER_PORT'] = '8000'
os.environ['USER_EMAIL'] = 'test@example.com'
os.environ['USER_IS_ADMIN'] = '1'


with open('google_apps.txt') as f:
    lines = f.readlines()
credentials = [line.strip() for line in lines[:2]]
_set_testing_user(*credentials)


class GDataTestCase(unittest.TestCase):
    USER_NAME = 'skymail'
    USER_GIVEN_NAME = 'sky'
    USER_FAMILY_NAME = 'mail'
    NUMBER_OF_USERS = 5

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
        new_user = GAUser(
            user_name='test',
            given_name='Test',
            family_name='Account',
            password='some_password',
        )
        self.assertRaises(AppsForYourDomainException, new_user.put)

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

    def testReferencePropertyOnNormalModel(self):
        user = GAUser.get_by_key_name(self.USER_NAME)
        test_model = TestModel(user=user)
        test_model.put()

        test_model = TestModel.all().get()
        self.assertEqual(user, test_model.user)

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
        self.assertEqual(len(users), 4)
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


class RoleCreationTestCase(unittest.TestCase):
    def setUp(self):
        db.delete(Role.all().fetch(100))

    def testCreateRole(self):
        Role.create('test_role', 'Some description')
        roles = Role.all().fetch(2)
        self.assertEqual(len(roles), 1)
        role = roles[0]
        self.assertEqual(role.name, 'test_role')

    def testGetByName(self):
        role_a = Role.create('test_role', 'Some description')
        role_b = Role.get_by_name('test_role')
        self.assertEqual(role_a, role_b)

