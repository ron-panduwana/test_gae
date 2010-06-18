import os
import shutil
import sys
from django.core.management.base import BaseCommand, CommandError


abs = lambda x: os.path.join(sys.path[0], x)
PATHS = {
    'calc_deps': abs('static/closure-library/closure/bin/calcdeps.py'),
    'closure_deps': abs('util/all-closure-deps.js'),
    'closure_dir': abs('static/closure-library'),
    'compiler_jar': abs('util/compiler.jar'),
    'output': abs('static/scripts/all-closure.js'),
    'scripts_dir': abs('static/scripts'),
}

COMMAND = ("""
python "%(calc_deps)s" -i "%(closure_deps)s" -p "%(closure_dir)s"
-p "%(scripts_dir)s" -f "--compilation_level=ADVANCED_OPTIMIZATIONS"
-o compiled -c "%(compiler_jar)s" --output_file="%(output)s"
""" % PATHS).strip().replace('\n', ' ')


class Command(BaseCommand):
    help = 'Compile ClosureJS files.'

    def handle(self, *args, **kwargs):
        ret_val = os.system(COMMAND.strip().replace('\n', ' '))
        if ret_val != 0:
            raise CommandError('calcdeps returned %d error code.' % ret_val)

