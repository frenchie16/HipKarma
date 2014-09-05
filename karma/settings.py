"""
Settings for the Karma app.
"""

import os
import re

HIPCHAT_API_URL = 'https://api.hipchat.com/v2'

ADDON_NAME = os.environ.get('ADDON_NAME', 'Karma')
ADDON_CHAT_NAME = os.environ.get('ADDON_CHAT_NAME', 'karma')
ADDON_KEY = os.environ.get('ADDON_KEY', 'com.johnfrench.hipchat.karma')

NOTIFICATION_COLOR = 'green'

# Scopes to request when getting OAuth token.
# This should match the scopes listed in capabilities.json.
SCOPES = 'send_notification admin_room view_group view_messages'

REGEXES = {
    # Regex for chat command to give someone/something karma
    # Capture group 0 should contain an '@' character iff the karma target is in the form of a mention
    # Capture group 1 or 2 should contain the name of the recipient (the other should be empty).
    # Capture group 3 should contain either '++' or '--'.
    # Capture group 4 should contain an optional comment.
    'give_karma': r'^(?:(@)?(\S{1,50}) ?|\(([^)\r\n]{1,48})\))(\+\+|--)(?: *(?:#|\/\/)\s*(\S.*))?$',

    # Regex for chat command to show someone/something's karma
    # Capture group 0 or 1 should contain the name to show karma for (the other should be empty)
    'show_karma': r'^@{name} for (?:(@)?(\S{{1,50}}) ?|\(([^)\r\n]{{1,48}})\))$'.format(name=ADDON_CHAT_NAME),

    # Regex for chat command to show help
    'help': r'^@{name} help$'.format(name=ADDON_CHAT_NAME),
}

# Compiled version of REGEXES for performance
COMPILED_REGEXES = {k: re.compile(v) for k, v in REGEXES.items()}