# Set up the webhooks
from utils import setup_webhook


def initialize():
    """Performs some setup that should run when the application starts."""
    setup_webhook()