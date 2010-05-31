from django.http import HttpResponse
from django.shortcuts import redirect

from crgappspanel.models import GAGroup, SharedContact
from crlib.navigation import render_with_nav
from crauth.decorators import login_required


def index(request):
    return redirect('users')


def language(request):
    return render(request, 'language.html', {'LANGUAGES': LANGUAGES})


@login_required
def test(request):
    sth = []
    for key, value in request.session.iteritems():
        sth.append('%s = %s (%s)' % (key, value, type(value)))
    
    sc = SharedContact.all().fetch(1)[0]
    sc = SharedContact.get_by_key_name(r'http://www.google.com/m8/feeds/contacts/moroccanholidayrental.com/full/10981388ab842a7')
    sth.append(sc.key())
    sth.append(str(sc.key()))
    return render_with_nav(request, 'test.html', {
        'something': sth,
        'scripts': ['test'],
    })
