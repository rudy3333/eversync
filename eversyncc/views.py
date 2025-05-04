from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
# Create your views here.
from django.contrib.auth import logout


def logout_view(request):
    logout(request)
    return redirect('index')

def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("")
    else:
        form = UserCreationForm()
    return render(request, "register.html", {"form": form})

@login_required
def index(request):
    return render(request, "index.html")

