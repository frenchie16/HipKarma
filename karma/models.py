from django.db import models


class KarmicEntity(models.Model):
    """A thing that can have karma. It could be a user, or just some string.

    Attributes:
        id (str): If this entity is a user, their ID, otherwise the string itself
        is_user (bool): True if this is a user and id is their id, otherwise False if this is some string
        karma (int): This entity's current karma
        max_karma (int): The highest value karma has ever reached
        min_karma (int): The lowest value karma has ever reached
    """

    id = models.CharField('id', max_length=50, primary_key=True, db_index=True)

    is_user = models.BooleanField('is user')

    karma = models.IntegerField('karma', default=0)

    max_karma = models.IntegerField('max karma', default=0)

    min_karma = models.IntegerField('min karma', default=0)

    def give_karma(self, karma):
        """Apply karma to this entity.

        Args:
            karma (str): The type of karma. One of Karma.KARMA_VALUES.
        """
        new_karma = self.karma
        if karma == Karma.GOOD:
            new_karma += 1
        elif karma == Karma.BAD:
            new_karma -= 1

        if new_karma > self.max_karma:
            self.max_karma = new_karma
        elif new_karma < self.min_karma:
            self.min_karma = new_karma
        self.karma = new_karma


class Karma(models.Model):
    """An instance of karma being given to some entity.

    Attributes:
        GOOD (str): Represents good karma (one option for value)
        BAD (str): Represents bad karma (another option for value)
        recipient (KarmicEntity): The entity which received the karma
        sender (KarmicEntity): The entity (always a user) who sent the karma
        room (str): The name of the room where the karma was awarded
        value (str): The type of karma, from KARMA_VALUES
        when (datetime): When the karma was awarded
        comment (str): Optional comment explaining the karma
    """

    GOOD = 'G'
    BAD = 'B'

    KARMA_VALUES = (
        (GOOD, 'Good'),
        (BAD, 'Bad'),
    )

    recipient = models.ForeignKey('KarmicEntity', name='recipient', related_name='received', db_index=True)

    sender = models.ForeignKey('KarmicEntity', name='sender', related_name='sent', db_index=True)

    room = models.CharField('room', max_length=50)

    value = models.CharField('karma value', max_length=1, choices=KARMA_VALUES)

    when = models.DateTimeField('date created', auto_now_add=True)

    comment = models.TextField('comment', blank=True)
