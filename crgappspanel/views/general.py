from django.http import HttpResponse
from django.shortcuts import redirect

from crgappspanel.models import GAGroup
from crlib.navigation import render_with_nav
from auth.decorators import login_required


def index(request):
    return redirect('users')


def language(request):
    return render(request, 'language.html', {'LANGUAGES': LANGUAGES})


@login_required
def test(request):
    sth = []
    for key, value in request.session.iteritems():
        sth.append('%s = %s (%s)' % (key, value, type(value)))
    return render_with_nav(request, 'test.html', {
        'something': sth,
        'scripts': ['test'],
    })
