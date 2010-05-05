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
    groups = GAGroup.all()
    groups = ('[id=%s, name=%s, email_permission=%s]' % (group.id, group.name, group.email_permission) for group in groups)
    return render(request, 'test.html', ctx({
        'something': groups,
        'scripts': ['test'],
    }, 2, 4))
