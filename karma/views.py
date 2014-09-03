import logging
import json

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseBadRequest
from django.http.response import HttpResponseNotAllowed
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from . import settings
from .models import Instance, KarmicEntity, Karma


logger = logging.getLogger(__name__)


# Views

def index(request):
    """Main page"""
    # Todo Provide a nice status page, maybe some karma statistics
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    return HttpResponse('HipKarma is running.')


def capabilities(request):
    """Capabilities descriptor for addon"""
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

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
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

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

    # Install instance
    try:
        instance = Instance.install(oauth_client_id, oauth_secret, room_id, capabilities_url)
    except Instance.InvalidCapabilities:
        logger.error('Invalid capabilities')
        return HttpResponseBadRequest('Invalid capabilities')

    # Send notification to room announcing installation
    instance.send_room_notification(
        'The {addon_name} addon has been installed in this room.\n'
        'Say "@{addon_chat_name} help" for help on using karma.'
        .format(
            addon_name=settings.ADDON_CHAT_NAME,
            addon_chat_name=settings.ADDON_CHAT_NAME,
        )
    )

    return HttpResponse('Installed successfully')


@csrf_exempt
def uninstall(request, client_id=None):
    """Callback to uninstall an instance of HipKarma"""
    if request.method != 'DELETE':
        return HttpResponseNotAllowed(['DELETE'])

    if not client_id:
        logger.error('Client ID not provided')
        return HttpResponseBadRequest('Client ID not provided')
    instance = Instance.objects.get(oauth_client_id=client_id)
    instance.delete()
    return HttpResponse('Installed successfully')


@csrf_exempt
def give_hook(request):
    """Callback for give karma webhook

    Applies karma to an entity.
    Triggered by a message in chat like "@phone++ #comment".
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # Load the webhook payload from JSON
    try:
        payload = json.loads(request.body.decode())
    except ValueError:
        logger.error('Invalid JSON')
        return HttpResponseBadRequest('Invalid JSON')

    # Get the necessary data out of the payload
    try:
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
        oauth_client_id = payload['oauth_client_id']
    except KeyError:
        logger.error('Invalid payload data')
        return HttpResponseBadRequest('Invalid payload data')

    # Get the instance from the OAuth ID
    instance = Instance.objects.get(oauth_client_id=oauth_client_id)

    # Apply the regex to get each part of the message
    match_result = settings.COMPILED_REGEXES['give_karma'].match(message_text)
    if not match_result:
        logger.error('Message does not match regex')
        return HttpResponseBadRequest('Message does not match regex')
    groups = match_result.groups()
    mention = groups[0] or ''
    recipient_name = groups[1] or groups[2]
    karma_operator = groups[3]
    comment = groups[4]

    # Determine if recipient_name is a valid mention and set recipient_id and recipient_type accordingly
    matching_mention = {}
    if mention:
        try:
            for m in mentions:
                if m['mention_name'].lower() == recipient_name.lower():
                    matching_mention = m
                    break
        except KeyError:
            logger.error('Invalid payload data')
            return HttpResponseBadRequest('Invalid payload data')

    if matching_mention:
        recipient_type = KarmicEntity.USER
        recipient_id = matching_mention['id']
    else:
        recipient_type = KarmicEntity.STRING
        recipient_id = mention + recipient_name

    # Get the karma value from the operator
    value = {
        '++': Karma.GOOD,
        '--': Karma.BAD,
    }[karma_operator]

    # Process the new karma
    try:
        karma = Karma.apply_new(instance=instance,
                                sender=sender_id,
                                recipient=recipient_id,
                                recipient_type=recipient_type,
                                value=value,
                                comment=comment)
    except Karma.SelfKarma:
        instance.send_room_notification('Nice try, @{name}.'.format(name=sender_mention_name))
        logger.info('Foiling dastardly narcissism')
        return HttpResponse('Karma was invalid due to narcissism')

    # Notify room about the karma
    instance.send_room_notification(
        '{recipient} has {total} total karma.'
        .format(
            recipient=karma.recipient.get_name(),
            total=karma.recipient.karma
        )
    )

    # Update any mentions we can
    KarmicEntity.update_mentions(instance.group, mentions + [sender])
    return HttpResponse('Applied karma successfully')


@csrf_exempt
def show_hook(request):
    """Callback for show karma webhook

    Sends a room notification with some karma info about an entity.
    Triggered by a message like "@karma for @phone".
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

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
        oauth_client_id = payload['oauth_client_id']
        sender = message['from']
    except KeyError:
        logger.error('Invalid payload data')
        return HttpResponseBadRequest('Invalid payload data')

    # Get the instance from the OAuth ID, and the group from the instance
    instance = Instance.objects.get(oauth_client_id=oauth_client_id)
    group = instance.group

    # Check that the regex is matched and use it to extract the name
    match_result = settings.COMPILED_REGEXES['show_karma'].match(message_text)
    if not match_result:
        logger.error('Message does not match regex')
        return HttpResponseBadRequest('Message does not match regex')
    groups = match_result.groups()
    mention = groups[0] or ''
    name = groups[1] or groups[2]

    # Determine if recipient_name is a valid mention and set recipient_id and recipient_type accordingly
    matching_mention = {}
    if mention:
        try:
            for m in mentions:
                if m['mention_name'].lower() == name.lower():
                    matching_mention = m
                    break
        except KeyError:
            logger.error('Invalid payload data')
            return HttpResponseBadRequest('Invalid payload data')

    if matching_mention:
        type_ = KarmicEntity.USER
        id_ = matching_mention['id']
    else:
        type_ = KarmicEntity.STRING
        id_ = mention + name

    try:
        entity = KarmicEntity.objects.get(group=group, type=type_, name=id_)
    except KarmicEntity.DoesNotExist:
        # Notify room that entity does not exist
        instance.send_room_notification(
            '{symbol}{name} has never received any karma.'
            .format(
                symbol=mention,
                name=name,
            )
        )
        return HttpResponse('Target did not exist, notified room.')

    # Get a sample of karma for the entity
    good_sample, bad_sample = entity.get_karma_sample(3)

    KarmicEntity.update_mentions(instance.group, mentions + [sender])

    # Build strings showing sample of karma comments
    good_sample_string = ''
    for karma in good_sample:
        string = '@{name}: {comment}\n'.format(name=karma.sender.get_name(), comment=karma.comment)
        good_sample_string += string

    bad_sample_string = ''
    for karma in bad_sample:
        string = '@{name}: {comment}\n'.format(name=karma.sender.get_name(), comment=karma.comment)
        bad_sample_string += string

    # Notify room about the karma
    instance.send_room_notification(
        '{name} has {karma} total karma. The highest it has ever been is {max} and the lowest it has ever been '
        'is {min}.\n\n'
        'Good:\n'
        '{good_sample}\n'
        'Bad:\n'
        '{bad_sample}'
        .format(
            name=entity.get_name(),
            karma=entity.karma,
            min=entity.min_karma,
            max=entity.max_karma,
            good_sample=good_sample_string or 'None!\n',
            bad_sample=bad_sample_string or 'None!\n',
        )
    )
    return HttpResponse('Showed karma successfully')


@csrf_exempt
def help_hook(request):
    """Callback for help webhook

    Sends a room notification with some help info.
    Triggered by a message like "@karma help".
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # Load the webhook payload from JSON
    try:
        payload = json.loads(request.body.decode())
    except ValueError:
        logger.error('Invalid JSON')
        return HttpResponseBadRequest('Invalid JSON')

    # Get the necessary data out of the payload
    try:
        if payload['event'] != 'room_message':
            logger.error('Unexpected event type ({type})').format(type=payload['event'])
            return HttpResponseBadRequest('')
        item = payload['item']
        message = item['message']
        message_text = message['message']
        oauth_client_id = payload['oauth_client_id']
        sender = message['from']
        mentions = message['mentions']
    except KeyError:
        logger.error('Invalid payload data')
        return HttpResponseBadRequest('Invalid payload data')

    # Get the instance from the OAuth ID, and the group from the instance
    instance = Instance.objects.get(oauth_client_id=oauth_client_id)

    # Check that the regex is matched and use it to extract the name
    match_result = settings.COMPILED_REGEXES['help'].match(message_text)
    if not match_result:
        logger.error('Message does not match regex')
        return HttpResponseBadRequest('Message does not match regex')

    # Send the help notification
    instance.send_room_notification(
        'Give karma like this: "target++ #comment"\n'
        'Remember to use an @mention for the target if the target is a person!\n'
        'Use "++" for good karma and "--" for bad karma.\n'
        'The comment can start with either "//" or "#" and is optional.\n'
        'If your target has whitespace in it, surround it with parentheses, like this: "(two words)++"\n'
        'To check the karma for someone (or something), use: "@{addon_chat_name} for target"\n'
        'For more information, see {index_url}.'
        .format(
            index_url=request.build_absolute_uri(reverse(index)),
            addon_chat_name=settings.ADDON_CHAT_NAME,
        )
    )
    # Update any mentions we can
    KarmicEntity.update_mentions(instance.group, mentions + [sender])
    return HttpResponse('Showed help successfully')