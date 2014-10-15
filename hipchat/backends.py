from django.contrib.auth.models import User


class HipchatBackend:
    """Django authentication backend for Hipchat accounts"""

    @staticmethod
    def authenticate(username=None, password=None):
        """Authenticate as a Hipchat user

        Args:
            username: the Hipchat username
            password: the password
        Returns:
            A Django user (or None if login failed)
        """
        pass

    @staticmethod
    def get_user(user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None