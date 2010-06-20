# -*- coding: UTF-8 -*-
import logging
import unittest
from crlib import regexps


class RegexpsTestCase(unittest.TestCase):
    def testValidDomain(self):
        domains = (
            'cloudreach.co.uk',
            'test.com',
            'example.com',
            'google.com',
            'many.sub.domains.test.com',
        )
        for domain in domains:
            self.assertNotEqual(regexps.RE_DOMAIN.match(domain), None)

    def testInvalidDomain(self):
        domains = (
            'test.longtld',
            'invalid_domain',
        )
        for domain in domains:
            self.assertEqual(regexps.RE_DOMAIN.match(domain), None)

    def testValidUsernames(self):
        names = (
            'test',
            'letters098-_.\'',
            'Test',
        )
        for name in names:
            self.assertNotEqual(regexps.RE_USERNAME.match(name), None)

    def testInvalidUsernames(self):
        names = (
            u'invalidnąme',
            'user_name_with_equal_sign=',
            'user_name_with_brackets<>',
        )
        for name in names:
            self.assertEqual(regexps.RE_USERNAME.match(name), None)

    def testValidFirstLastNames(self):
        names = (
            'First',
            'Name',
            u'Michał', u'michał',
            u'Żebrowski',
            'Van Basten',
            'v. Basten',
            'Name-With-Dash',
            'Some/Name',
            'John 2',
        )
        for name in names:
            self.assertNotEqual(regexps.RE_FIRST_LAST_NAME.match(name), None)

    def testInvalidFirstLastNames(self):
        names = (
            'Name_With_Underscores',
            'NameWithEqualSign=',
            'NameWithBrackets<>',
            'NameWithQuestionMark?',
            'NameWithExclamationMark!',
            'Names Longer Than Fourty Letters Are Invalid Too',
        )
        for name in names:
            self.assertEqual(regexps.RE_FIRST_LAST_NAME.match(name), None)


