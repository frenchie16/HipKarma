import json
import keyword
import logging
from string import Template

import os
import re
import hypchat.requests
import hypchat.restobject
from hypchat import HypChat
from .models import Karma, KarmicEntity


logger = logging.getLogger(__name__)

# Todo Get WEBHOOK_URL from some configuration
WEBHOOK_URL = 'http://hipkarma.heroku.com/karma'
KARMA_REGEX = r'^(?:\(([^)]+)\)|([^ ]+))(\+\+|--)[\s]*(?:#|\/\/)?(.*)?$'


def get_hypchat():
    """Get a HypChat object with the correct token

    Returns:
        HypChat: a HypChat object using the correct token
    """
    return HypChat(os.environ['HIPCHAT_TOKEN'])


def setup_webhook():
    """Set up the HipKarma webhook"""
    hc = get_hypchat()
    rooms = map(lambda r: hc.get_room(r), os.environ['ROOMS'].split('|'))

    for room in rooms:
        hooks = room.webhooks()
        # delete any existing hipkarma webhooks
        for hook in (hooks.contents()):
            if hook.name == 'HipKarma':
                hook.delete()
        # create a new hipkarma webhook
        room.create_webhook(url=WEBHOOK_URL, event='room_message', pattern=KARMA_REGEX, name='HipKarma')


def get_user_id(name):
    """Get the ID of a user given some other handle for them

    Args:
        name (str): Some handle for the user, e.g. their @mention name or email

    Returns:
        str: The user's ID as a string, if the user was found
        None: if the user was not found
    """
    hc = get_hypchat()

    try:
        user = hc.get_user(name)
    except hypchat.requests.HttpNotFound:
        return None

    return str(user.id)


def get_mention_name(identifier):
    """Get the @mention name of a user given their id (or other handle)

    Args:
        identifier (str): Some handle for the user, e.g. their id or email

    Returns:
        str: The user's @mention name as a string, if the user was found
        None: if the user was not found
    """
    hc = get_hypchat()

    try:
        user = hc.get_user(identifier)
    except hypchat.requests.HttpNotFound:
        return None

    return user.mention_name


def send_message(room, message):
    """Send a message to a room with some default settings.

    Args:
        room (str, Room): The room to send to
        message (str): The message to send
    """
    if not hasattr(room, 'send_message'):
        room = get_hypchat().get_room(room)

    room.message(message, format='text')


def object_from_text(text):
    """Construct objects from JSON.

    Potentially unsafe as it uses protected attributes from HypChat.

    Args:
        text (str): the JSON text to construct objects from
        requests (Requests): the Requests object to use for expanding links

    Returns:
        RestObject: an object form of the data in the JSON
    """

    def _object_hook(obj):
        _class = RestObject
        if 'links' in obj:
            if 'self' in obj['links']:
                for p, c in hypchat.restobject._urls_to_objects.iteritems():
                    if p.match(obj['links']['self']):
                        _class = c
        rv = _class(obj)
        rv._requests = get_hypchat()._requests
        return rv

    return json.JSONDecoder(object_hook=_object_hook).decode(text)


class RestObject(hypchat.restobject.RestObject):
    """Extends HypChat's RestObject to fix name collisions which prevent it from working with WebHook payloads."""

    def __getattr__(self, name):
        # this allows us to access fields from the json whose names are reserved keywords in python.
        # for instance if the json had a field 'for' we can access it as 'for_'
        if name[-1] == '_' and keyword.iskeyword(name[:-1]):
            try:
                return self.__getattr__(name[:-1])
            except AttributeError:
                pass
        if name in self.get('links', {}):
            return hypchat.restobject.Linker(self['links'][name], parent=self, _requests=self._requests)
        elif name in self:
            return self[name]
        else:
            raise AttributeError("%r object has no attribute %r" % (type(self).__name__, name))


def parse_webhook_payload(payload_string):
    """Parse a webhook payload to get a nice object

    Args:
        payload_string (str): the raw payload string from a webhook

    Returns:
        RestObject: A RestObject representing the payload, if it was a room_message event
        None: If the payload could not be parsed, or was not of a supported event type
    """
    return object_from_text(payload_string)


def handle_webhook_payload(payload):
    """Handle a webhook payload, generating a Karma from it if possible.

    Args:
        payload (RestObject): The webhook payload to handle

    Returns:
        Karma: A Karma constructed from the payload, if everything checks out
        None: If there was some error, e.g. the message in the payload is not a valid karma message
    """
    if payload.event == 'room_message':
        item = payload.item
        message = item.message
        sender_id = str(message.from_.id)
        text = message.message
        room = item.room.name

        regex = re.compile(KARMA_REGEX)
        result = regex.match(text)

        if result:
            groups = result.groups()

            try:
                recipient_name = groups[0] or groups[1]
                operator = groups[2]
                comment = groups[3]
            except ValueError:
                logger.debug('Regex match did not produce enough groups')
                return None

            # Check if the karma recipient is a user and if so, get their ID
            recipient_id = get_user_id(recipient_name)
            is_user = bool(recipient_id)
            # If they're not a user use the name instead
            if not is_user:
                recipient_id = recipient_name

            # Don't let people give themselves karma
            logger.debug("Karma from " + sender_id + " to " + recipient_id)
            if recipient_id == sender_id:
                logger.debug('Someone tried to give themselves karma')
                return None

            # Parse the karma operator to get the value
            if operator == '++':
                value = Karma.GOOD
            elif operator == '--':
                value = Karma.BAD
            else:
                logger.debug('Karma operator was not ++ or --')
                return None

            # Get or create the KarmicEntity for the recipient
            try:
                recipient = KarmicEntity.objects.get(id=recipient_id)
            except KarmicEntity.DoesNotExist:
                recipient = KarmicEntity(id=recipient_id, is_user=is_user)

            # Update karma totals on recipient
            recipient.give_karma(value)
            recipient.save()

            # Get or create the KarmicEntity for the sender
            try:
                sender = KarmicEntity.objects.get(id=sender_id)
            except KarmicEntity.DoesNotExist:
                sender = KarmicEntity(id=sender_id, is_user=True)
                sender.save()

            karma = Karma(recipient=recipient, sender=sender, room=room, value=value, comment=comment)
            karma.save()
            return karma
        else:
            logger.debug('Regex did not match')
            return None
    else:
        logger.debug('Event was not room_message')
        return None


def send_karma_notification(karma):
    """Notify that karma has been received and processed successfully.

    Sends a message to the room the karma was awarded in with the new total karma of the recipient.

    Args:
        karma (Karma): The karma to send the notification about
    """
    recipient = ''.join(["@", get_mention_name(karma.recipient.id)]) if karma.recipient.is_user else karma.recipient.id
    template = Template("${recipient}'s karma is now ${karma}.")
    message = template.substitute(recipient=recipient, karma=karma.recipient.karma)

    send_message(karma.room, message)