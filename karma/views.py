import json
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.http import HttpResponseBadRequest

from .utils import *
from .models import *

# Create your views here.
def index(request):
    return HttpResponse('Hello from HipKarma!')

@csrf_exempt
def karma(request):

    req = json.loads(request.body)

    try:
        if req['event'] == 'room_message':

            item = req['item']
            message = item['message']
            karma = parseMessage(message)
            if karma:
                if karma.recipient.is_user:
                    recipient_name = getMentionName(karma.recipient.id)
                else:
                    recipient_name = karma.recipient.id
                hc = getHypChat()
                hc.get_room(item['room']['id']).message(
                    format=True,
                    ''.join([recipient_name, "'s karma is now ", str(karma.recipient.karma), '.']))
                    
                return HttpResponse()

    except LookupError:
        pass

    return HttpResponseBadRequest()
