from django.utils.translation import ugettext_lazy as _

from gdata.apps.groups import service as groups


EMAIL_REL_HOME = 'http://schemas.google.com/g/2005#home'
EMAIL_REL_WORK = 'http://schemas.google.com/g/2005#work'
EMAIL_REL_OTHER = 'http://schemas.google.com/g/2005#other'

EMAIL_RELS = (
    EMAIL_REL_HOME,
    EMAIL_REL_WORK,
    EMAIL_REL_OTHER,
)


PHONE_REL_HOME = 'http://schemas.google.com/g/2005#home'
PHONE_REL_HOME_FAX = 'http://schemas.google.com/g/2005#home_fax'
PHONE_REL_WORK = 'http://schemas.google.com/g/2005#work'
PHONE_REL_WORK_FAX = 'http://schemas.google.com/g/2005#work_fax'
PHONE_REL_MOBILE = 'http://schemas.google.com/g/2005#mobile'
PHONE_REL_PAGER = 'http://schemas.google.com/g/2005#pager'
PHONE_REL_FAX = 'http://schemas.google.com/g/2005#fax'
PHONE_REL_OTHER = 'http://schemas.google.com/g/2005#other'

PHONE_RELS = (
    PHONE_REL_HOME,
    PHONE_REL_HOME_FAX,
    PHONE_REL_WORK,
    PHONE_REL_WORK_FAX,
    PHONE_REL_MOBILE,
    PHONE_REL_PAGER,
    PHONE_REL_FAX,
    PHONE_REL_OTHER,
)


EMAIL_ACTION_KEEP = 'KEEP'
EMAIL_ACTION_ARCHIVE = 'ARCHIVE'
EMAIL_ACTION_DELETE = 'DELETE'

EMAIL_ACTIONS = (
    EMAIL_ACTION_KEEP,
    EMAIL_ACTION_ARCHIVE,
    EMAIL_ACTION_DELETE,
)


EMAIL_ENABLE_FOR_ALL_MAIL = 'ALL_MAIL'
EMAIL_ENABLE_FOR_MAIL_FROM_NOW_ON = 'MAIL_FROM_NOW_ON'

EMAIL_ENABLE_FORS = (
    EMAIL_ENABLE_FOR_ALL_MAIL,
    EMAIL_ENABLE_FOR_MAIL_FROM_NOW_ON,
)


GROUP_EMAIL_PERMISSION_OWNER = groups.PERMISSION_OWNER
GROUP_EMAIL_PERMISSION_MEMBER = groups.PERMISSION_MEMBER
GROUP_EMAIL_PERMISSION_DOMAIN = groups.PERMISSION_DOMAIN
GROUP_EMAIL_PERMISSION_ANYONE = groups.PERMISSION_ANYONE

GROUP_EMAIL_PERMISSION_CHOICES = (
    (GROUP_EMAIL_PERMISSION_OWNER, _('Owner')),
    (GROUP_EMAIL_PERMISSION_MEMBER, _('Member')),
    (GROUP_EMAIL_PERMISSION_DOMAIN, _('Domain')),
    (GROUP_EMAIL_PERMISSION_ANYONE, _('Anyone')),
)


LANGUAGES = (
    ('in', u'Bahasa Indonesia'),
    ('ms', u'Bahasa Melayu'),
    ('ca', u'Catal\u00e0'),
    ('cs', u'\u010cesk\u00fd'),
    ('da', u'Dansk'),
    ('de', u'Deutsch'),
    ('et', u'Eesti keel'),
    ('en-GB', u'English (UK)'),
    ('en-US', u'English (US)'),
    ('es', u'Espa\u00f1ol'),
    ('eu', u'Euskara'), # not in documentation
    ('tl', u'Filipino'),
    ('fr', u'Fran\u00e7ais'),
    ('hr', u'Hrvatski'),
    ('it', u'Italiano'),
    ('is', u'\u00cdslenska'),
    ('lv', u'Latvie\u0161u'),
    ('lt', u'Lietuvi\u0173'),
    ('hu', u'Magyar'),
    ('nl', u'Nederlands'),
    ('no', u'Norsk (Bokm\u00e5l)'),
    ('pl', u'Polski'),
    ('pt-BR', u'Portugu\u00eas (Brasil)'),
    ('pt-PT', u'Portugu\u00eas (Portugal)'),
    ('ro', u'Rom\u00e2n\u0103'),
    ('sk', u'Slovensk\u00fd'),
    ('sl', u'Sloven\u0161\u010dina'),
    ('fi', u'Suomi'),
    ('sv', u'Svenska'),
    ('vi', u'Ti\u1ebfng Vi\u1ec7t'), # Vietnamese
    ('tr', u'T\u00fcrk\u00e7e'), # Turkish
    ('el', u'\u0395\u03bb\u03bb\u03b7\u03bd\u03b9\u03ba\u03ac'), # Greek
    ('ru', u'\u0420\u0443\u0441\u0441\u043a\u0438\u0439'), # Russian
    ('sr', u'\u0421\u0440\u043f\u0441\u043a\u0438'), # Serbian
    ('uk', u'\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430'), # Ukrainian
    ('bg', u'\u0411\u044a\u043b\u0433\u0430\u0440\u0441\u043a\u0438'), # Bulgarian
    ('iw', u'\u05e2\u05d1\u05e8\u05d9\u05ea'), # Hebrew
    ('ar', u'\u0627\u0644\u0639\u0631\u0628\u064a\u0629'), # Arabic
    ('ur', u'\u0627\u0631\u062f\u0648'), # Urdu
    ('mr', u'\u092e\u0930\u093e\u0920\u0940'), # Marathi
    ('hi', u'\u0939\u093f\u0928\u094d\u0926\u0940'), # Hindi
    ('bn', u'\u09ac\u09be\u0982\u09b2\u09be'), # Bengali
    ('gu', u'\u0a97\u0ac1\u0a9c\u0ab0\u0abe\u0aa4\u0ac0'), # Gujarati
    ('or', u'\u0b13\u0b21\u0b3f\u0b06 (Oriya)'), # Oriya
    ('ta', u'\u0ba4\u0bae\u0bbf\u0bb4\u0bcd'), # Tamil
    ('te', u'\u0c24\u0c46\u0c32\u0c41\u0c17\u0c41'), # Telugu
    ('kn', u'\u0c95\u0ca8\u0ccd\u0ca8\u0ca1'), # Kannada
    ('ml', u'\u0d2e\u0d32\u0d2f\u0d3e\u0d33\u0d02'), # Malayalam
    ('th', u'\u0e20\u0e32\u0e29\u0e32\u0e44\u0e17\u0e22'), # Thai
    ('zh-TW', u'\u4e2d\u6587\uff08\u7e41\u9ad4\uff09'), # Chinese (Traditional)
    ('zh-CN', u'\u4e2d\u6587\uff08\u7b80\u4f53\uff09'), # Chinese (Simplified)
    ('ja', u'\u65e5\u672c\u8a9e'), # Japanese
    ('ko', u'\ud55c\uad6d\uc5b4'), # Korean
    ('fa', u'\u0641\u0627\u0631\u0633\u06cc'), # Persian - not in GMail
)
