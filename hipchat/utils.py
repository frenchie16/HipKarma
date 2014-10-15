from requests.auth import AuthBase


class BearerAuth(AuthBase):
    """HTTP authentication for OAuth bearer tokens as used by HipChat"""

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = ' '.join(['Bearer', self.token])
        return r


def validate_capabilities(url):
    """Validate the capabilities of HipChat itself

    Currently just checks that the url given is the url for hipchat.com's capabilities
    because we don't support self-hosted instances of hipchat.

    Args:
        url (str): The URL of the capabilities descriptor to validate
    Returns:
        bool: True if the URL is valid
    """
    return url == 'https://api.hipchat.com/v2/capabilities'