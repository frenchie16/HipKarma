from django.db import models

# Create your models here.

"""
A Karmic Entity is a thing that can have karma. It could be a user, or just some string.
"""
class KarmicEntity(models.Model):

    """
    If this represents a user, the ID of the user (NOT their email nor mention name,
    as these can change), or else the string (for when people give inanimate objects
    karma)
    """    
    id = models.CharField('id', max_length=50, primary_key=True, db_index=True)
    
    """
    True if id is the ID of a user, false otherwise (if 'id' is just some string).
    """
    is_user = models.BooleanField('is user')
    
    

class Karma(models.Model):

    GOOD = 'G'
    BAD = 'B'

    KARMA_VALUES = (
        (GOOD, 'Good'),
        (BAD, 'Bad'),
    )

    """
    The recipient of this karma
    """
    recipient = models.ForeignKey('KarmicEntity', name='recipient', related_name='received', db_index=True)

    """
    The sender of this karma
    """
    sender = models.ForeignKey('KarmicEntity', name='sender', related_name='sent', db_index=True)

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
