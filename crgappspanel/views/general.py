from django.http import HttpResponse
from django.shortcuts import redirect

from crgappspanel.views.utils import ctx, render
from auth.decorators import login_required


def index(request):
    return redirect('users')


def language(request):
    return render(request, 'language.html', {'LANGUAGES': LANGUAGES})


@login_required
def test(request):
    return render(request, 'test.html', ctx({
        'scripts': ['test'],
    }, 2, 4))
