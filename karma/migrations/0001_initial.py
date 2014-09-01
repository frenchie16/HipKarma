# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                ('group_id', models.IntegerField(primary_key=True, serialize=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Instance',
            fields=[
                ('oauth_client_id', models.CharField(primary_key=True, serialize=False, max_length=50)),
                ('oauth_secret', models.CharField(max_length=50)),
                ('oauth_token', models.CharField(max_length=50)),
                ('room_id', models.IntegerField()),
                ('group', models.ForeignKey(to='karma.Group', related_name='instances')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Karma',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('value', models.CharField(max_length=1, choices=[('G', 'Good'), ('B', 'Bad')])),
                ('when', models.DateTimeField(auto_now_add=True)),
                ('comment', models.TextField(null=True, blank=True)),
                ('instance', models.ForeignKey(to='karma.Instance')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='KarmicEntity',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('name', models.CharField(max_length=50)),
                ('type', models.CharField(max_length=1, choices=[('U', 'User'), ('S', 'String')])),
                ('karma', models.IntegerField(default=0)),
                ('max_karma', models.IntegerField(default=0)),
                ('min_karma', models.IntegerField(default=0)),
                ('group', models.ForeignKey(to='karma.Group', related_name='karmic_entities')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterIndexTogether(
            name='karmicentity',
            index_together=set([('group', 'name', 'type')]),
        ),
        migrations.AddField(
            model_name='karma',
            name='recipient',
            field=models.ForeignKey(to='karma.KarmicEntity', related_name='karma_received'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='karma',
            name='sender',
            field=models.ForeignKey(to='karma.KarmicEntity', related_name='karma_sent'),
            preserve_default=True,
        ),
    ]
