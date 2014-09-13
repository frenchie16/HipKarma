import random

from django.db import models
from karma.hipchat import HipChat


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
        room_id (int): The ID of the room this instance is installed in
        group (Group): The HipChat group this instance is installed in
    """
    oauth_client_id = models.CharField(max_length=50, primary_key=True)
    oauth_secret = models.CharField(max_length=50)
    oauth_token = models.CharField(max_length=50)
    room_id = models.IntegerField()
    group = models.ForeignKey(Group, related_name='instances')

    class InvalidCapabilities(Exception):
        pass

    @classmethod
    def install(cls, client_id, secret, room_id, capabilities_url=None):
        """Create a new Instance with the information provided by HipChat upon addon installation

        Note that the model created will automatically be saved to the database, no need to save it again.
        A Group may also be created and saved if one did not already exist for the group this instance serves.

        Args:
            client_id (str): The OAuth client ID
            secret (str): The OAuth secret
        Returns:
            Instance: A newly-created instance from the information provided
        """

        if capabilities_url is not None:
            if not HipChat.validate_capabilities(capabilities_url):
                raise cls.InvalidCapabilities

        instance = Instance(oauth_client_id=client_id, oauth_secret=secret, room_id=room_id)
        group_id = instance.refresh_token(False)
        try:
            group = Group.objects.get(group_id=group_id)
        except Group.DoesNotExist:
            group = Group.objects.create(group_id=group_id)
        instance.group = group
        instance.save()
        return instance

    def refresh_token(self, save=True):
        """Get a fresh OAuth token using the secret and client ID.

        Returns the group ID of the group the token is valid for because bizarrely, the only way to get the group ID
        from HipChat is through the token endpoint, when you generate a token.
        By default, causes this Instance to be saved.

        Args:
            save (bool): If True, will save after refreshing the token. Defaults to True.
        Returns:
            int: The group ID of the group the token is valid for
        """
        group_id, self.oauth_token = HipChat.authenticate(self.oauth_client_id, self.oauth_secret)
        if save:
            self.save()
        return group_id

    def send_room_notification(self, message):
        """Sends a notification to a room

        Args:
            room (int, str): The ID or name of the room
            message (str): The text of the message
        Exceptions:
            HipChatApiError: If the request to send the notification is unsuccessful.
        """
        try:
            hipchat = HipChat(self.oauth_token)
            hipchat.send_room_notification(self.room_id, message)
        except HipChat.Unauthorized:
            # If authentication fails, refresh token and try once more, because probably the token expired.
            # If it still fails just throw the exception because refreshing the token again is unlikely to help
            self.refresh_token()
            hipchat = HipChat(self.oauth_token)
            hipchat.send_room_notification(self.room_id, message)

    def __str__(self):
        return "Instance (Client ID: {client_id})".format(client_id=self.oauth_client_id)


class KarmicEntity(models.Model):
    """A thing that can have karma. It could be a user, or just some string.

    mention_name should never be used for looking up entities, only for displaying a nice friendly human name instead
    of a number.

    Attributes:
        USER (str): Type value for a KarmicEntity representing a user
        STRING (str): Type value for a KarmicEntity representing some arbitrary string
        KARMIC_ENTITY_TYPES ([(str, str)]): Possible values for type
        name (str): If this entity is a user, their ID, otherwise the string itself
        type (str): One of KARMIC_ENTITY_TYPES indicating whether this is a user or a random string
        mention_name (str): If type is USER, this will contain the most-recently-seen mention name for the user
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

    group = models.ForeignKey(Group, related_name='karmic_entities')
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=1, choices=KARMIC_ENTITY_TYPES)
    mention_name = models.CharField(blank=True, null=True, max_length=50)
    karma = models.IntegerField(default=0)
    max_karma = models.IntegerField(default=0)
    min_karma = models.IntegerField(default=0)

    class Meta:
        index_together = [
            ['group', 'name', 'type']
        ]

    @classmethod
    def update_mentions(cls, group, mentions):
        """Given a list of mentions, update the mention names of any extant KarmicEntities

        Args:
            group: The group within which to look for entities
            mentions ([{}]): A list of dicts representing mentions. Each dict must have 'id' and 'mention_name' keys.
        """
        for mention in mentions:
            try:
                entity = cls.objects.get(group=group, name=mention['id'], type=cls.USER)
                entity.mention_name = mention['mention_name']
                entity.save()
            except KarmicEntity.DoesNotExist:
                cls.objects.create(group=group, name=mention['id'], type=cls.USER,
                                   mention_name=mention['mention_name'])

    def give_karma(self, value):
        """Apply karma to this entity.

        Automatically saves this entity after applying the karma.

        Args:
            karma (str): The type of karma. One of Karma.KARMA_VALUES.
        """
        new_karma = self.karma
        if value == Karma.GOOD:
            new_karma += 1
        elif value == Karma.BAD:
            new_karma -= 1

        if new_karma > self.max_karma:
            self.max_karma = new_karma
        elif new_karma < self.min_karma:
            self.min_karma = new_karma
        self.karma = new_karma
        self.save()

    def get_karma_sample(self, n):
        """Get a sampling of karma for this entity.

        Takes a random sample of up to n of the Karmas given to this user (samples good and bad separately and returns n
        Karmas of each type.)

        Args:
            n (int): The number of comments to get for each type of karma.
        Returns:
            ([Karma], [Karma]): A list of up to n good Karmas given to this user, and up to n bad ones.
        """
        def reservoir_sample(n_, l):
            r = []
            for i, x in enumerate(l):
                if i < n_:
                    r.append(x)
                elif random.random() < n_/float(i+1):
                    j = random.randint(0, n_-1)
                    r[j] = x
            return r

        good = self.karma_received.filter(value=Karma.GOOD, comment__isnull=False)
        bad = self.karma_received.filter(value=Karma.BAD, comment__isnull=False)
        return reservoir_sample(n, good), reservoir_sample(n, bad)

    def get_name(self):
        """Return the mention name (if this is a user) or the string

        Returns:
            str: The mention name if this is a user, or just the string
        """
        return self.name if self.type == self.STRING else ('@' + self.mention_name if self.mention_name else 'Unknown')

    def __str__(self):
        return "{type} {name}".format(
            type=dict(self.KARMIC_ENTITY_TYPES)[self.type],
            name=self.get_name(),
        )


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
    value = models.CharField(max_length=1, choices=KARMA_VALUES)
    when = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, null=True)

    class SelfKarma(Exception):
        pass

    @classmethod
    def apply_new(cls, instance, sender, recipient, recipient_type, value, comment=None):
        """Apply new karma.

        Creates/saves (as necessary) model objects for the sender and recipient.
        The returned Karma object is also automatically saved.

        Args:
            instance (Instance): The instance for which we are applying karma
            sender (int): The user ID of the sender of the karma
            recipient (str, int): The user ID (if user) or string of the recipient of the karma
            recipient_type (str): One of KarmicEntity.KARMIC_ENTITY_TYPES, the type of the recipient
            value: One of Karma.KARMA_VALUES, the value of the karma
            comment: An optional comment for the karma
        Exceptions:
            SelfKarma: If the sender and the recipient are the same
        """
        group = instance.group

        # Disallow giving karma to oneself
        if recipient_type == KarmicEntity.USER and value != Karma.BAD and sender == recipient:
            raise cls.SelfKarma

        # Get or create the KarmicEntity for the recipient
        try:
            recipient_entity = KarmicEntity.objects.get(group=group, name=recipient, type=recipient_type)
        except KarmicEntity.DoesNotExist:
            recipient_entity = KarmicEntity.objects.create(group=group, name=recipient, type=recipient_type)

        # Get or create the KarmicEntity for the sender
        try:
            sender_entity = KarmicEntity.objects.get(group=group, name=sender, type=KarmicEntity.USER)
        except KarmicEntity.DoesNotExist:
            sender_entity = KarmicEntity.objects.create(group=group, name=sender, type=KarmicEntity.USER)

        # Save a new karma with the data
        karma = Karma.objects.create(recipient=recipient_entity,
                                     sender=sender_entity,
                                     value=value,
                                     comment=comment)

        # Update karma totals on recipient
        recipient_entity.give_karma(value)

        return karma

    def __str__(self):
        return "{sender}->{recipient} ({value})".format(sender=str(self.sender),
                                                        recipient=str(self.recipient),
                                                        value=dict(Karma.KARMA_VALUES)[self.value])
