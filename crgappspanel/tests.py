import unittest
from appengine_django.models import BaseModel
from google.appengine.ext import db
from crgappspanel.models import Role


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

