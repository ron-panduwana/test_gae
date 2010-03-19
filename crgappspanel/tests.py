import os
import unittest
from appengine_django.models import BaseModel
from google.appengine.ext import db
from crgappspanel.models import GAUser, Role


os.environ['SERVER_NAME'] = 'localhost'
os.environ['SERVER_PORT'] = '8000'
os.environ['USER_EMAIL'] = 'test@example.com'
os.environ['USER_IS_ADMIN'] = '1'


class GDataTestCase(unittest.TestCase):
    USER_NAME = 'skymail'
    USER_GIVEN_NAME = 'sky'
    USER_FAMILY_NAME = 'mail'

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
        # We need additional test account to test such features
        self.assertTrue(False)
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
        new_user.put()

    def testRenameUser(self):
        # We need additional test account to test such features
        self.assertTrue(False)
        user = GAUser.get_by_key_name(self.USER_NAME)
        user.user_name = 'new_user'
        user.put()

    def testMultipleChanges(self):
        # We need additional test account to test such features
        self.assertTrue(False)
        user = GAUser.get_by_key_name(self.USER_NAME)
        user.user_name = 'new_user'
        user.given_name = 'Test'
        user.password = 'new_password'
        user.put()


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

