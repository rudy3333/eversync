from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
# Create your views here.
from django.contrib.auth import logout


def logout_view(request):
    logout(request)
    return redirect('index')


@login_required
def index(request):
    return render(request, "index.html")