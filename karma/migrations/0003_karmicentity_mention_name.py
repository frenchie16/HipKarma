# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('karma', '0002_remove_karma_instance'),
    ]

    operations = [
        migrations.AddField(
            model_name='karmicentity',
            name='mention_name',
            field=models.CharField(blank=True, null=True, max_length=50),
            preserve_default=True,
        ),
    ]
