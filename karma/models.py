from django.db import models


class Group(models.Model):
    """A group for which HipKarma has at least one installation.

    This is used because while HipKarma is installed per room, it stores karma per group.

    Attributes:
        group_id (int): The ID of this HipChat group
    """
    group_id = models.IntegerField(primary_key=True)

    def __str__(self):
        return "Group {group_id}".format(group_id=str(self.group_id))


class Instance(models.Model):
    """An installed instance of HipKarma.

    Instances are installed one per room.

    Attributes:
        oauth_client_id (str): The OAuth client ID for this instance
        oauth-secret (str): The OAuth secret for this instance
        oauth_token (str): The OAuth token for this instance
    """
    oauth_client_id = models.CharField(max_length=50, primary_key=True)
    oauth_secret = models.CharField(max_length=50)
    oauth_token = models.CharField(max_length=50)
    group = models.ForeignKey(Group, related_name='instances')

    def __str__(self):
        return "Instance (Client ID: {client_id})".format(client_id=self.oauth_client_id)


class KarmicEntity(models.Model):
    """A thing that can have karma. It could be a user, or just some string.

    Attributes:
        USER (str): Type value for a KarmicEntity representing a user
        STRING (str): Type value for a KarmicEntity representing some arbitrary string
        KARMIC_ENTITY_TYPES ([(str, str)]): Possible values for type
        id (str): If this entity is a user, their ID, otherwise the string itself
        is_user (bool): True if this is a user and id is their id, otherwise False if this is some string
        karma (int): This entity's current karma
        max_karma (int): The highest value karma has ever reached
        min_karma (int): The lowest value karma has ever reached
    """
    USER = 'U'
    STRING = 'S'
    KARMIC_ENTITY_TYPES = [
        (USER, 'User'),
        (STRING, 'String'),
    ]

    class Meta:
        index_together = [
            ['group', 'name', 'type']
        ]

    group = models.ForeignKey(Group, related_name='karmic_entities')
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=1, choices=KARMIC_ENTITY_TYPES)
    karma = models.IntegerField(default=0)
    max_karma = models.IntegerField(default=0)
    min_karma = models.IntegerField(default=0)

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

    def __str__(self):
        return "User {id}".format(id=self.name) if self.type == KarmicEntity.USER else self.name


class Karma(models.Model):
    """An instance of karma being given to some entity.

    Attributes:
        GOOD (str): Value for good karma (one option for value)
        BAD (str): Value for bad karma (another option for value)
        KARMA_VALUES ([(str, str)]): Possible choices for value
        recipient (KarmicEntity): The entity which received the karma
        sender (KarmicEntity): The entity (always a user) who sent the karma
        room (str): The name of the room where the karma was awarded
        value (str): The type of karma, from KARMA_VALUES
        when (datetime): When the karma was awarded
        comment (str): Optional comment explaining the karma
    """
    GOOD = 'G'
    BAD = 'B'

    KARMA_VALUES = [
        (GOOD, 'Good'),
        (BAD, 'Bad'),
    ]

    recipient = models.ForeignKey(KarmicEntity, related_name='karma_received', db_index=True)
    sender = models.ForeignKey(KarmicEntity, related_name='karma_sent', db_index=True)
    room = models.IntegerField()
    value = models.CharField(max_length=1, choices=KARMA_VALUES, db_index=True)
    when = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return "{sender}->{recipient} ({value})".format(sender=str(self.sender),
                                                        recipient=str(self.recipient),
                                                        value=dict(Karma.KARMA_VALUES)[self.value])
