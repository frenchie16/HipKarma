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

    """
    Entity's current karma total
    """
    karma = models.IntegerField('karma', default=0)

    """
    Highest karma ever
    """
    max_karma = models.IntegerField('max karma', default=0)
    
    """
    Lowest karma ever
    """
    min_karma = models.IntegerField('min karma', default=0)
    
    def applyKarma(self, karma):
        new_karma = self.karma
        if karma == Karma.GOOD:
            new_karma += 1
        if karma == Karma.BAD:
            new_karma -= 1

        if new_karma > self.max_karma:
            self.max_karma = new_karma
        if new_karma < self.min_karma:
            self.min_karma = new_karma
        self.karma = new_karma

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
