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


def exception_from_response(response):
    """Get a HipchatApiException from an HTTP Response"""
    exception_type = _status_code_map.get(response.status_code, HipChatApiError)
    if exception_type == BadRequest:
        return exception_type(response.text)
    else:
        return exception_type()