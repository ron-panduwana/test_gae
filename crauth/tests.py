import logging
import os
import unittest
import fudge
from google.appengine.ext import db
from crauth import users, models, permissions


os.environ['SERVER_NAME'] = 'localhost'
os.environ['SERVER_PORT'] = '8000'
os.environ['USER_EMAIL'] = 'test@example.com'
os.environ['USER_IS_ADMIN'] = '1'


FAKE_DOMAIN = 'fakedomain.com'
FAKE_EMAIL = 'fake@%s' % FAKE_DOMAIN


class PermissionsTestCase(unittest.TestCase):
    def setUp(self):
        if os.environ.has_key(users._ENVIRON_EMAIL):
            del os.environ[users._ENVIRON_EMAIL]
        if os.environ.has_key(users._ENVIRON_DOMAIN):
            del os.environ[users._ENVIRON_DOMAIN]
        domain = models.AppsDomain.get_or_insert(
            key_name=FAKE_DOMAIN,
            domain=FAKE_DOMAIN,
        )
        db.delete(models.UserPermissions.all().fetch(100))
        db.delete(models.Role.all().fetch(100))

    def set_testing_user(self):
        users._set_testing_user(FAKE_EMAIL, FAKE_DOMAIN)
        return users.get_current_user()

    def fake_is_admin(self, is_admin=True):
        fake_is_admin = fudge.Fake('users.User.is_admin',
                                   callable=True)
        fake_is_admin.returns(is_admin)
        return fudge.patched_context(users.User, 'is_admin',
                                     fake_is_admin)

    def testFakeIsAdmin(self):
        self.set_testing_user()
        with self.fake_is_admin(True):
            self.assertTrue(users.is_current_user_admin())
        with self.fake_is_admin(False):
            self.assertFalse(users.is_current_user_admin())

    def testHasPerm(self):
        user = self.set_testing_user()
        permissions = models.UserPermissions(
            key_name=user._email,
            user_email=user._email,
            permissions=['test_perm1', 'test_perm2'],
        )
        permissions.put()
        with self.fake_is_admin(False):
            self.assertTrue(user.has_perms(['test_perm1', 'test_perm2']))

    def testHasPerms(self):
        user = self.set_testing_user()
        permissions = models.UserPermissions(
            key_name=user._email,
            user_email=user._email,
            permissions=['test_perm'],
        )
        permissions.put()
        with self.fake_is_admin(False):
            self.assertTrue(user.has_perm('test_perm'))

    def testDoesntHavePerm(self):
        user = self.set_testing_user()
        permissions = models.UserPermissions(
            key_name=user._email,
            user_email=user._email,
            permissions=['some_perm'],
        )
        permissions.put()
        with self.fake_is_admin(False):
            self.assertFalse(user.has_perm('some_other_perm'))

    def testAdminHasAllPerms(self):
        user = self.set_testing_user()
        permissions = models.UserPermissions(
            key_name=user._email,
            user_email=user._email,
            permissions=['some_perm'],
        )
        permissions.put()
        with self.fake_is_admin(True):
            self.assertTrue(user.has_perm('some_perm'))
            self.assertTrue(user.has_perm('some_other_perm'))
            self.assertTrue(user.has_perms(['some_perm', 'some_other_perm']))

    def testDoesntHaveAllPerms(self):
        user = self.set_testing_user()
        permissions = models.UserPermissions(
            key_name=user._email,
            user_email=user._email,
            permissions=['some_perm'],
        )
        permissions.put()
        with self.fake_is_admin(False):
            self.assertFalse(user.has_perms(['some_perm', 'some_other_perm']))

    def testHasAdminPerm(self):
        user = self.set_testing_user()
        with self.fake_is_admin(True):
            for perm in permissions.ADMIN_PERMS:
                self.assertTrue(user.has_perm(perm))
            self.assertTrue(user.has_perms(permissions.ADMIN_PERMS))

    def testDoesntHaveAdminPerm(self):
        user = self.set_testing_user()
        permissions = models.UserPermissions(
            key_name=user._email,
            user_email=user._email,
            permissions=['admin'],
        )
        permissions.put()
        with self.fake_is_admin(False):
            self.assertFalse(user.has_perm('admin'))

    def testRoleForDomain(self):
        domain_1 = models.AppsDomain(domain='domain1')
        domain_1.put()
        domain_2 = models.AppsDomain(domain='domain2')
        domain_2.put()
        role = models.Role(
            name='Test Role',
            domain=domain_1,
        )
        role.put()
        role = models.Role(
            name='Test Role',
            domain=domain_2,
        )
        role.put()
        self.assertEqual(len(models.Role.for_domain(domain_1).fetch(2)), 1)

    def testHasPermThroughRole(self):
        user = self.set_testing_user()
        role = models.Role(
            name='Test Role',
            domain=user.domain(),
            permissions=['some_perm'],
        )
        role.put()
        permissions = models.UserPermissions(
            key_name=user._email,
            user_email=user._email,
            roles=[role.key()],
        )
        permissions.put()
        with self.fake_is_admin(False):
            self.assertTrue(user.has_perm('some_perm'))

