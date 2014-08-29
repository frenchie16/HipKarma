import json

import re
import requests
from requests.auth import AuthBase, HTTPBasicAuth
from . import settings, hipchat_exceptions

# pre-compiled regexes for performance
give_regex = re.compile(settings.REGEXES['give_karma'])
show_regex = re.compile(settings.REGEXES['show_karma'])


class BearerAuth(AuthBase):
    """Authentication for OAuth bearer tokens as used by HipChat"""

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = ' '.join(['Bearer', self.token])
        return r


def send_room_notification(room, message, token):
    """Sends a notification to a room

    Args:
        room (int, str): The ID or name of the room
        message (str): The text of the message
        token (str): The OAuth token to use
    Exceptions:
        HipChatApiException: If the request to send the notification is unsuccessful.
    """
    url = '{api_url}/room/{id_or_name}/notification'.format(api_url=settings.HIPCHAT_API_URL, id_or_name=room)
    payload = {
        'color': settings.NOTIFICATION_COLOR,
        'message': message,
        'message_format': 'text',
        'notify': False
    }
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), auth=BearerAuth(token), headers=headers)
    if response.status_code != 204:
        raise hipchat_exceptions.exception_from_response(response)


def validate_hipchat_capabilities(url):
    """Validate the capabilities of a hipchat instance itself

    Currently just checks that the url given is the url for hipchat.com's capabilities
    because HipKarma doesn't support self-hosted instances of hipchat.
    """
    return url == 'https://api.hipchat.com/v2/capabilities'


def get_oauth_token(client_id, secret):
    """Exchange an OAuth secret for a bearer token

    Args:
        client_id (str): The OAuth client ID
        secret (str): The OAuth secret
    Returns:
        dict: The payload of the response to the request for an oauth token
    Exceptions:
        HipChatApiException: If an error occurs getting the token.
    """
    url = '{api_url}/oauth/token'.format(api_url=settings.HIPCHAT_API_URL)
    payload = {
        'grant_type': 'client_credentials',
        'scope': settings.SCOPES
    }
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), auth=HTTPBasicAuth(client_id, secret), headers=headers)
    if response.status_code != 200:
        raise hipchat_exceptions.exception_from_response(response)
    return json.loads(response.text)