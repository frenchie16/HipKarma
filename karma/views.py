import logging

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest
from . import utils


logger = logging.getLogger(__name__)


def index(request):
    """Main page"""
    # Todo Provide a nice status page, maybe some karma statistics
    return HttpResponse('HipKarma is running.')


@csrf_exempt
def karma(request):
    """Callback for HipChat webhook"""
    # Parse the webhook payload into a RestObject
    payload = utils.parse_webhook_payload(request.body)
    if payload:
        # Handle the payload. If successful this will update the database to reflect the new karma.
        karma = utils.handle_webhook_payload(payload)

        if karma:
            utils.send_karma_notification(karma)
            logger.info('Successfully processed karma')
            return HttpResponse('Successfully processed karma')
        else:
            logger.error('Invalid payload')
            return HttpResponseBadRequest('Invalid payload')
    else:
        logger.error('Invalid karma message')
        return HttpResponseBadRequest('Invalid karma message')
