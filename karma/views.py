import logging
import json

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from . import settings, utils, models


logger = logging.getLogger(__name__)


# Views

def index(request):
    """Main page"""
    # Todo Provide a nice status page, maybe some karma statistics
    if request.method == 'GET':
        return HttpResponse('HipKarma is running.')


def capabilities(request):
    """Capabilities descriptor for addon"""
    if request.method == 'GET':
        return render(request,
                      'capabilities.json',
                      {'addon_name': json.dumps(settings.ADDON_NAME),
                       'addon_chat_name': json.dumps(settings.ADDON_CHAT_NAME),
                       'addon_key': json.dumps(settings.ADDON_KEY),
                       'homepage_url': json.dumps(request.build_absolute_uri(reverse(index))),
                       'capabilities_url': json.dumps(request.build_absolute_uri(reverse(capabilities))),
                       'install_url': json.dumps(request.build_absolute_uri(reverse(install))),
                       'give_hook_url': json.dumps(request.build_absolute_uri(reverse(give_hook))),
                       'give_hook_regex': json.dumps(settings.REGEXES['give_karma']),
                       'give_hook_name': json.dumps(settings.ADDON_KEY + '.hooks.give'),
                       'show_hook_url': json.dumps(request.build_absolute_uri(reverse(show_hook))),
                       'show_hook_regex': json.dumps(settings.REGEXES['show_karma']),
                       'show_hook_name': json.dumps(settings.ADDON_KEY + '.hooks.show'),
                       'help_hook_url': json.dumps(request.build_absolute_uri(reverse(help_hook))),
                       'help_hook_regex': json.dumps(settings.REGEXES['help']),
                       'help_hook_name': json.dumps(settings.ADDON_KEY + '.hooks.help')},
                      content_type='application/json')


@csrf_exempt
def install(request):
    """Callback to install or uninstall HipKarma in a room"""
    if request.method == 'POST':
        # Deserialize payload from JSON
        try:
            payload = json.loads(request.body.decode())
        except ValueError:
            logger.error('Invalid JSON')
            return HttpResponseBadRequest('Invalid JSON')

        # Get data out of payload
        try:
            capabilities_url = payload['capabilitiesUrl']
            oauth_client_id = payload['oauthId']
            oauth_secret = payload['oauthSecret']
            room_id = payload['roomId']
        except KeyError:
            logger.error('Invalid payload data')
            return HttpResponseBadRequest('Invalid payload data')

        # Confirm that the HipChat instance we are installing on is supported
        if not utils.validate_hipchat_capabilities(capabilities_url):
            logger.error('Invalid capabilities')
            return HttpResponseBadRequest('Invalid capabilities')

        # Exchange the OAuth secret for a token
        oauth_response = utils.get_oauth_token(oauth_client_id, oauth_secret)
        token = oauth_response['access_token']
        group_id = oauth_response['group_id']

        # Get or create group
        try:
            group = models.Group.objects.get(group_id=group_id)
        except models.Group.DoesNotExist:
            group = models.Group(group_id=group_id)
            group.save()

        # Create instance
        instance = models.Instance(oauth_client_id=oauth_client_id,
                                   oauth_secret=oauth_secret,
                                   oauth_token=token,
                                   group=group)
        instance.save()

        # Send notification to room
        utils.send_room_notification(room_id,
                                     "The {addon_name} addon has been installed in this room."
                                     .format(addon_name=settings.ADDON_CHAT_NAME),
                                     token)

        return HttpResponse('Installed successfully')


@csrf_exempt
def uninstall(request, client_id=None):
    """Callback to uninstall an instance of HipKarma"""
    if not client_id:
        logger.error('Client ID not provided')
        return HttpResponseBadRequest('Client ID not provided')
    instance = models.Instance.objects.get(oauth_client_id=client_id)
    instance.delete()
    return HttpResponse('Installed successfully')


@csrf_exempt
def give_hook(request):
    """Callback for give karma webhook

    Applies karma to an entity.
    Triggered by a message in chat like "@phone++ #comment".
    """
    if request.method == 'POST':
        # Load the webhook payload from JSON
        try:
            payload = json.loads(request.body.decode())
        except ValueError:
            logger.error('Invalid JSON')
            return HttpResponseBadRequest('Invalid JSON')

        try:
            # Get the necessary data out of the payload
            if payload['event'] != 'room_message':
                logger.error('Unexpected event type ({type})').format(type=payload['event'])
                return HttpResponseBadRequest('')
            item = payload['item']
            message = item['message']
            message_text = message['message']
            mentions = message['mentions']
            sender = message['from']
            sender_id = sender['id']
            sender_mention_name = sender['mention_name']
            room = item['room']
            room_id = room['id']
            oauth_client_id = payload['oauth_client_id']
        except KeyError:
            logger.error('Invalid payload data')
            return HttpResponseBadRequest('Invalid payload data')

        match_result = utils.give_regex.match(message_text)
        if not match_result:
            logger.error('Message does not match regex')
            return HttpResponseBadRequest('Message does not match regex')

        # Apply the regex to get each part of the message
        groups = match_result.groups()
        mention = groups[0] or ''
        recipient_name = groups[1] or groups[2]
        karma_operator = groups[3]
        comment = groups[4]

        try:
            # Determine if recipient_name is a valid mention
            if mention and mentions and mentions[0]['mention_name'] == recipient_name:
                recipient_type = models.KarmicEntity.USER
                recipient_id = mentions[0]['id']
            else:
                recipient_type = models.KarmicEntity.STRING
                recipient_id = mention + recipient_name
        except KeyError:
            logger.error('Invalid payload data')
            return HttpResponseBadRequest('Invalid payload data')

        # Get the instance from the OAuth ID, and the group from the instance
        instance = models.Instance.objects.get(oauth_client_id=oauth_client_id)
        group = instance.group

        # Disallow giving karma to oneself
        if sender_id == recipient_id:
            utils.send_room_notification(room_id,
                                         'Nice try, @{name}.'.format(name=sender_mention_name),
                                         instance.oauth_token)
            logger.info('Foiling dastardly narcissism')
            return HttpResponse('Karma was invalid due to narcissism')

        # Get the karma value from the operator
        value = {
            '++': models.Karma.GOOD,
            '--': models.Karma.BAD,
        }[karma_operator]

        # Get or create the KarmicEntity for the recipient
        try:
            recipient_entity = models.KarmicEntity.objects.get(group=group, name=recipient_id, type=recipient_type)
        except models.KarmicEntity.DoesNotExist:
            recipient_entity = models.KarmicEntity(group=group, name=recipient_id, type=recipient_type)

        # Update karma totals on recipient
        recipient_entity.give_karma(value)
        recipient_entity.save()

        # Get or create the KarmicEntity for the sender
        try:
            sender_entity = models.KarmicEntity.objects.get(group=group, name=sender_id, type=models.KarmicEntity.USER)
        except models.KarmicEntity.DoesNotExist:
            sender_entity = models.KarmicEntity(group=group, name=sender_id, type=models.KarmicEntity.USER)
            sender_entity.save()

        # Save a new karma with the data
        karma = models.Karma(recipient=recipient_entity,
                             sender=sender_entity,
                             room=room_id,
                             value=value,
                             comment=comment)
        karma.save()

        # Notify room about the karma
        utils.send_room_notification(room_id,
                                     '{symbol}{recipient} has {karma} total karma.'
                                     .format(symbol=mention,
                                             recipient=recipient_name,
                                             karma=recipient_entity.karma),
                                     instance.oauth_token)
        return HttpResponse('Applied karma successfully')


@csrf_exempt
def show_hook(request):
    """Callback for show karma webhook

    Sends a room notification with some karma info about an entity.
    Triggered by a message like "@karma for @phone".
    """
    if request.method == 'POST':
        # Load the webhook payload from JSON
        try:
            payload = json.loads(request.body.decode())
        except ValueError:
            logger.error('Invalid JSON')
            return HttpResponseBadRequest('Invalid JSON')

        try:
            # Get the necessary data out of the payload
            if payload['event'] != 'room_message':
                logger.error('Unexpected event type ({type})').format(type=payload['event'])
                return HttpResponseBadRequest('')
            item = payload['item']
            message = item['message']
            message_text = message['message']
            mentions = message['mentions']
            room = item['room']
            room_id = room['id']
            oauth_client_id = payload['oauth_client_id']
        except KeyError:
            logger.error('Invalid payload data')
            return HttpResponseBadRequest('Invalid payload data')

        # Get the instance from the OAuth ID, and the group from the instance
        instance = models.Instance.objects.get(oauth_client_id=oauth_client_id)
        group = instance.group

        match_result = utils.show_regex.match(message_text)
        if not match_result:
            logger.error('Message does not match regex')
            return HttpResponseBadRequest('Message does not match regex')

        groups = match_result.groups()
        mention = groups[0] or ''
        name = groups[1] or groups[2]

        try:
            # Determine if recipient_name is a valid mention
            if mention and mentions and mentions[0]['mention_name'] == name:
                type = models.KarmicEntity.USER
                id = mentions[0]['id']
            else:
                type = models.KarmicEntity.STRING
                id = (mention) + name
        except KeyError:
            logger.error('Invalid payload data')
            return HttpResponseBadRequest('Invalid payload data')

        entity = models.KarmicEntity.objects.get(group=group, type=type, name=id)

        # Notify room about the karma
        format_string = ('{symbol}{name} has {karma} total karma. '
                         'The highest it has ever been is {max} and the lowest it has ever been is {min}.')
        utils.send_room_notification(room_id,
                                     format_string.format(
                                         symbol=mention,
                                         name=name,
                                         karma=entity.karma,
                                         min=entity.min_karma,
                                         max=entity.max_karma),
                                     instance.oauth_token)
        return HttpResponse('Showed karma successfully')


@csrf_exempt
def help_hook(request):
    """Callback for help webhook

    Sends a room notification with some help info.
    Triggered by a message like "@karma help".
    """
    if request.method == 'POST':
        # Load the webhook payload from JSON
        try:
            payload = json.loads(request.body.decode())
        except ValueError:
            logger.error('Invalid JSON')
            return HttpResponseBadRequest('Invalid JSON')

        try:
            # Get the necessary data out of the payload
            if payload['event'] != 'room_message':
                logger.error('Unexpected event type ({type})').format(type=payload['event'])
                return HttpResponseBadRequest('')
            item = payload['item']
            oauth_client_id = payload['oauth_client_id']
            room = item['room']
            room_id = room['id']
        except KeyError:
            logger.error('Invalid payload data')
            return HttpResponseBadRequest('Invalid payload data')

        # Get the instance from the OAuth ID, and the group from the instance
        instance = models.Instance.objects.get(oauth_client_id=oauth_client_id)

        # Send the help notification
        utils.send_room_notification(room_id,
                                     'For help and more information, see {index_url}.'.format(
                                         index_url=request.build_absolute_uri(reverse(index))
                                     ),
                                     instance.oauth_token)
        return HttpResponse('Showed help successfully')