from django.shortcuts import render_to_response, redirect

from crgappspanel.views.utils import ctx
from crlib.users import admin_required


def index(request):
    return redirect('users')


def language(request):
    return render_to_response('language.html', {'LANGUAGES': LANGUAGES})


@admin_required
def test(request):
    return render_to_response('test.html', ctx({
        'scripts': ['test'],
    }, 2, 4))
