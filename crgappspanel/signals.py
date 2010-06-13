import django.dispatch

gauser_renamed = django.dispatch.Signal(providing_args=['old_name', 'new_name'])
