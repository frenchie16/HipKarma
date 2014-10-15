import json

from . import exceptions, utils
from django.db import models
import requests
from requests.auth import HTTPBasicAuth, AuthBase
from django.conf import settings


class Group(models.Model):
    """Represents a HipChat group/instance.

    Attributes:
        group_id (int): The ID of this HipChat group
    """
    group_id = models.IntegerField(primary_key=True)

    def __str__(self):
        return "Group {group_id}".format(group_id=str(self.group_id))


class Session(models.Model):
    """A HipChat OAuth session.

    Attributes:
        oauth_client_id (str): The OAuth client ID for this instance
        oauth-secret (str): The OAuth secret for this instance
        oauth_token (str): The OAuth token for this instance
        room_id (int): The ID of the room this instance is installed in
        group (Group): The HipChat group this instance is installed in
    """
    oauth_client_id = models.CharField(max_length=50, primary_key=True)
    oauth_secret = models.CharField(max_length=50)
    oauth_token = models.CharField(max_length=50)
    group = models.ForeignKey(Group, related_name='instances')

    class InvalidCapabilities(Exception):
        pass

    @classmethod
    def create(cls, client_id, secret, capabilities_url=None):
        """Create a new Session

        Note that the model created will automatically be saved to the database, no need to save it again.
        A Group may also be created and saved if one did not already exist for the group this instance serves.

        Args:
            client_id (str): The OAuth client ID
            secret (str): The OAuth secret
        Returns:
            Session: A newly-created session from the information provided
        """

        if capabilities_url is not None:
            if not utils.validate_capabilities(capabilities_url):
                raise cls.InvalidCapabilities

        session = Session(oauth_client_id=client_id, oauth_secret=secret)
        group_id = session.refresh_token(False)
        try:
            group = Group.objects.get(group_id=group_id)
        except Group.DoesNotExist:
            group = Group.objects.create(group_id=group_id)
        session.group = group
        session.save()
        return session

    def authenticate(self):
        """Authenticate to HipChat with a client ID and secret, updating token and group

        Args:
            client_id (str): The OAuth client ID
            secret (str): The OAuth secret
        Exceptions:
            HipChatApiError: If an error occurs with the authentication
        """
        url = '{api_url}/oauth/token'.format(api_url=settings.HIPCHAT_API_URL)
        payload = {
            'grant_type': 'client_credentials',
            'scope': settings.SCOPES
        }
        headers = {'content-type': 'application/json'}
        response = requests.post(url,
                                 data=json.dumps(payload),
                                 auth=HTTPBasicAuth(self.oauth_client_id, self.oauth_secret),
                                 headers=headers)
        if response.status_code != 200:
            raise exceptions.exception_from_response(response)

        response_dict = json.loads(response.text)
        self.group = Group.objects.get_or_create(group_id=response_dict['group_id'])
        self.token = response_dict['access_token']

    def send_room_notification(self, room_id, message, color, message_format='text', notify=False):
        """Sends a notification to a room

        Args:
            room (int, str): The ID or name of the room
            message (str): The text of the message
        Exceptions:
            HipChatApiError: If the request to send the notification is unsuccessful.
        """
        url = '{api_url}/room/{room}/notification'.format(api_url=settings.HIPCHAT_API_URL, room=room_id)
        payload = {
            'color': color,
            'message': message,
            'message_format': message_format,
            'notify': notify
        }
        headers = {'content-type': 'application/json'}
        response = self._do_request(requests.post,
                                    204,
                                    url,
                                    data=json.dumps(payload),
                                    auth=utils.BearerAuth(self._token),
                                    headers=headers)

    def _do_request(self, func, expected_status_code, *args, **kwargs):
        response = func(*args, **kwargs)
        if response.status_code == expected_status_code:
            return response
        else:
            self.authenticate()
            return func(*args, **kwargs)

    def __str__(self):
        return "Instance (Client ID: {client_id})".format(client_id=self.oauth_client_id)


