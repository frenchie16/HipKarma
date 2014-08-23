import json
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from .utils import *
from .models import *

# Create your views here.
def index(request):
    return HttpResponse('Hello from HipKarma!')

@csrf_exempt
def karma(request):

    getHypChat().get_room("Bot Testing").message("Loading json: " + request.body)
    
    req = json.loads(request.body)
    getHypChat().get_room("Bot Testing").message("Loaded")

    try:
        if req['event'] == 'room_message':

            item = req['item']
            message = item['message']
            getHypChat().get_room("Bot Testing").message("Parsing message")
            karma = parseMessage(message)
            getHypChat().get_room("Bot Testing").message("Parsed")
            if karma:
                getHypChat().get_room("Bot Testing").message("Yup, it's karma")
                hc = getHypChat()
                hc.get_room(item['room']['id']).message("Karma received! recipient: "
                                                        + str(karma.recipient.id) + ", sender: "
                                                        + str(karma.sender.id) + ", value: "
                                                        + karma.value + ", comment: "
                                                        + karma.comment)
                return HttpResponse()

    except LookupError:
        pass

    return HttpResponseBadRequest()
