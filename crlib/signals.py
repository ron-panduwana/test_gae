import django.dispatch

class_prepared = django.dispatch.Signal()
gauser_renamed = django.dispatch.Signal(providing_args=['old_name', 'new_name'])
