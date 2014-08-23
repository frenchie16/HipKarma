import os
import re
from hypchat import HypChat
from hypchat.requests import HttpNotFound

from .models import *

KARMA_REGEX=r'^(\([^)]+\)|[^ ]+)([+]{2}|[-]{2})(.*)?$'

"""
Takes a message dict from the json from a room_message post and tries to parse it as a karma.
Returns a karma if the message was valid, otherwise None.
"""
def parseMessage(message):

    sender = message['from']['id']
    text = message['message']

    regex = re.compile(KARMA_REGEX)
    result = regex.match(text)

    if result:

        groups = result.groups()
        
        recipient = groups[0]

        # check if the karma recipient is a user and if so, use their ID instead of name
        recipient_id = getUserId(recipient)
        is_user = bool(recipient_id)
        if(is_user):
            recipient = recipient_id
        # get or create the karmicentity for the recipient
        try:
            recipient_entity = KarmicEntity.objects.get(id=str(recipient))
        except KarmicEntity.DoesNotExist:
            # will be saved below when we update karma totals
            recipient_entity = KarmicEntity(id=recipient, is_user=is_user)

        # and for sender
        try:
            sender_entity = KarmicEntity.objects.get(id=str(sender))
        except KarmicEntity.DoesNotExist:
            sender_entity = KarmicEntity(id=sender, is_user=True)
            sender_entity.save()

        if groups[1] == '++':
            value = Karma.GOOD

        elif groups[1] == '--':
            value = Karma.BAD

        else:
            return None        

        # update karma totals on recipient
        recipientEntity.applyKarma(value)
        recipient_entity.save()


        comment = groups[2]

        karma = Karma(recipient=recipient_entity, sender=sender_entity,
                      value=value, comment=comment)
        karma.save()
        return karma

    return None

"""
Gets the ID of a user given some other handle for them (email, @mention, display name).
If the user is not found, returns None.
"""
def getUserId(name):

    hc = getHypChat()

    try:
        user = hc.get_user(name)
    except HttpNotFound:
        return None

    return user.id


def getMentionName(id):

    hc = getHypChat()

    try:
        user = hc.get_user(id)
    except HttpNotFound:
        return None

    return user.mention_name


"""
Gets a HypChat with the right token
"""
def getHypChat():
    return HypChat(os.environ['HIPCHAT_TOKEN'])
