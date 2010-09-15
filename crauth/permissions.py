from django.utils.translation import ugettext_lazy as _


_MAPPER_PERMS = (
    # mapper attribute name, permission name
    ('create', 'add'),
    ('update', 'change'),
    ('retrieve_all', 'read'),
)


_PREDEFINED_PERMS = [
    ('admin', _('Is Administrator')),
    ('add_role', _('Can add Role objects')),
    ('change_role', _('Can change Role objects')),
    ('read_role', _('Can read Role objects')),
]


#: Permissions available only to domain administrators
ADMIN_PERMS = (
    'admin', 'add_role', 'change_role',
)


_permissions = _PREDEFINED_PERMS[:]


def class_prepared_callback(sender, **kwargs):
    if not hasattr(sender, '_mapper'):
        return

    model_name = sender.__name__.lower()
    perms = []
    if hasattr(sender._meta, 'permissions'):
        _permissions.extend(sender._meta.permissions)
    else:
        for attr, perm in _MAPPER_PERMS:
            if hasattr(sender._mapper, attr):
                perms.append(perm)
        for perm in perms:
            _permissions.append(
                ('%s_%s' % (perm, model_name),
                 _('Can %(perm)s %(model_name)s objects') % {
                     'perm': _(perm),
                     'model_name': sender.__name__,
                 }))


def permission_choices(with_admin_perms=True):
    return [perm for perm in _permissions
            if with_admin_perms or not perm[0] in ADMIN_PERMS]


def permission_names(with_admin_perms=True):
    return [perm[0] for perm in _permissions
            if with_admin_perms or not perm[0] in ADMIN_PERMS]


def permission_deps(with_admin_perms=True):
    for perm in _permissions:
        if with_admin_perms or not perm[0] in ADMIN_PERMS:
            if len(perm) == 3:
                yield (perm[0], perm[2])
            else:
                yield (perm[0], None)

