from django.shortcuts import render_to_response, redirect

from crgappspanel.models import GAGroup
from crgappspanel.views.utils import ctx
from crlib.users import admin_required


def index(request):
    return redirect('users')


def language(request):
    return render_to_response('language.html', {'LANGUAGES': LANGUAGES})


@admin_required
def test(request):
    groups = GAGroup.all()
    groups = ('[id=%s, name=%s, email_permission=%s]' % (group.id, group.name, group.email_permission) for group in groups)
    return render_to_response('test.html', ctx({
        'something': groups,
        'scripts': ['test'],
    }, 2, 4))
