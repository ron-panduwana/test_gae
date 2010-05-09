from django.http import HttpResponse
from django.shortcuts import redirect

from crgappspanel.models import GAGroup
from crgappspanel.views.utils import ctx, render
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
    return render(request, 'test.html', ctx({
        'something': sth,
        'scripts': ['test'],
    }, 2, 4))
