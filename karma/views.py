from django.shortcuts import render
from django.http import HttpResponse

from .models import Karma

# Create your views here.
def index(request):
    return HttpResponse('Hello from HipKarma!')

def 
