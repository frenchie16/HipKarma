from django.db import models

# Create your models here.
class Karma(models.Model):

    GOOD = 'G'
    BAD = 'B'

    KARMA_VALUES = (
        (GOOD, 'Good'),
        (BAD, 'Bad'),
    )

    """
    If the recipient is a user, the ID of the user (NOT their email nor mention name,
    as these can change), or else the string (for when people give inanimate objects
    karma)
    """
    recipient = models.CharField('recipient', max_length=50, db_index=True)

    """
    True if 'who' is the ID of a user, false otherwise (if 'who' is just some string).
    """
    is_user = models.BooleanField('is user')

    """
    The ID of the user (not email nor mention name) who gave the karma.
    """
    sender = models.CharField('sender', max_length=50)

    """
    The karma value, one of good or bad (could add others like neutral)
    """
    value = models.CharField('karma value', max_length=1, choices=KARMA_VALUES)

    """
    Timestamp when karma was awarded.
    """
    when = models.DateTimeField('date created', auto_now_add=True)

    """
    Optional comment explaining karma.
    """
    comment = models.CharField('comment', max_length=500, blank=True)
