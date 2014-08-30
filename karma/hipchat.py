import json

import requests
from requests.auth import AuthBase, HTTPBasicAuth
from . import settings


class BearerAuth(AuthBase):
    """Authentication for OAuth bearer tokens as used by HipChat"""

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = ' '.join(['Bearer', self.token])
        return r


class HipChat:
    """Provides access to the HipChat API"""
    def __init__(self, token):
        """
        Args:
            token (str): The oauth token to use for accessing HipChat
        """
        self._token = token

    @classmethod
    def authenticate(cls, client_id, secret):
        """Authenticate to HipChat with a client ID and secret

        Args:
            client_id (str): The OAuth client ID
            secret (str): The OAuth secret
        Returns:
            (int, str): The group ID that you have authenticated for, and your access token
        Exceptions:
            HipChatApiError: If an error occurs with the authentication
        """
        url = '{api_url}/oauth/token'.format(api_url=settings.HIPCHAT_API_URL)
        payload = {
            'grant_type': 'client_credentials',
            'scope': settings.SCOPES
        }
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), auth=HTTPBasicAuth(client_id, secret), headers=headers)
        if response.status_code != 200:
            raise cls._exception_from_response(response)

        response_dict = json.loads(response.text)
        return response_dict['group_id'], response_dict['access_token']

    @classmethod
    def validate_capabilities(cls, url):
        """Validate the capabilities of HipChat itself

        Currently just checks that the url given is the url for hipchat.com's capabilities
        because HipKarma doesn't support self-hosted instances of hipchat.

        Args:
            url (str): The URL of the capabilities descriptor to validate
        Exceptions:
            HipChatApiError: If an error occurs sending the notification
        """
        return url == 'https://api.hipchat.com/v2/capabilities'

    def send_room_notification(self, room, message):
        """Sends a notification to a room

        Args:
            room (int, str): The ID or name of the room
            message (str): The text of the message
            token (str): The OAuth token to use
        Exceptions:
            HipChatApiError: If the request to send the notification is unsuccessful.
        """
        url = '{api_url}/room/{room}/notification'.format(api_url=settings.HIPCHAT_API_URL, room=room)
        payload = {
            'color': settings.NOTIFICATION_COLOR,
            'message': message,
            'message_format': 'text',
            'notify': False
        }
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), auth=BearerAuth(self._token), headers=headers)
        if response.status_code != 204:
            raise self._exception_from_response(response)

    class HipChatApiError(Exception):
        """Base class for HipChat API exceptions"""

        def __str__(self):
            return 'Unknown HipChat error occurred.'

    class BadRequest(HipChatApiError):
        """The request was invalid."""

        def __init__(self, error_message):
            self.error_message = error_message

        def __str__(self):
            return repr(self.error_message)

    class Unauthorized(HipChatApiError):
        """The authentication you provided is invalid."""

        def __str__(self):
            return 'The authentication you provided is invalid.'

    class RateLimit(HipChatApiError):
        """You have exceeded the rate limit."""

        def __str__(self):
            return 'You have exceeded the rate limit.'

    class NotFound(HipChatApiError):
        """You requested an invalid method."""

        def __str__(self):
            return 'You requested an invalid method.'

    class HipChatError(HipChatApiError):
        """Something is wrong with HipChat."""

        def __str__(self):
            return 'Something is wrong with HipChat.'

    class ServiceUnavailable(HipChatApiError):
        """HipChat is unavailable."""

        def __str__(self):
            return 'HipChat is unavailable.'

    _status_code_map = {
        400: BadRequest,
        401: Unauthorized,
        403: RateLimit,
        404: NotFound,
        500: HipChatError,
        503: ServiceUnavailable,
    }

    @classmethod
    def _exception_from_response(cls, response):
        exception_type = cls._status_code_map.get(response.status_code, cls.HipChatApiError)
        args = []
        if exception_type == cls.BadRequest:
            args.append(response.text)
        return exception_type(*args)