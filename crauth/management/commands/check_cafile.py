import os
import sys
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Checks if GoogleInternetAuthority.crt is valid'

    def handle(self, *args, **kwargs):
        crt_file = os.path.join(
            sys.path[0], 'crauth/GoogleInternetAuthority.crt')
        ret = os.system('openssl verify %s' % crt_file)
        if ret != 0:
            raise CommandError(
                'GoogleInternetAuthority.crt verification failed.')

