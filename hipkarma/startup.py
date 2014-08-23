import os
from hypchat import HypChat
from karma.utils import KARMA_REGEX

WEBHOOK_URL = 'http://hipkarma.heroku.com/karma'

def setupWebHook():
    hc = HypChat(os.environ['HIPCHAT_TOKEN'])
    found=False
    for room in os.environ['ROOMS'].split('|'):
        hooks = hc.get_room(room).webhooks()
        for hook in (hooks.contents()):
            if hook.name == 'HipKarma':
                found=True;
                break;
        if not found:
            hc.get_room(room).create_webhook(url=WEBHOOK_URL, event='room_message', pattern=KARMA_REGEX,
                         name='HipKarma')

def run():
    setupWebHook()
