from django.db import models

# Create your models here.
class Karma(models.Model):

    KARMA_VALUES = (
        ('G', 'Good'),
        ('B', 'Bad'),
        ('N', 'Neutral')
    )

    """
    Either the ID of the user (NOT their email nor mention name, as these can change),
    or the string (for when people give inanimate objects karma)
    """
    who = models.CharField('recipient', max_length=50, db_index=True)

    """
    True if 'who' is the ID of a user, false otherwise (if 'who' is just some string).
    """
    is_user = models.BooleanField('recipient is user')

    """
    The karma value, one of good, bad, or neutral.
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
