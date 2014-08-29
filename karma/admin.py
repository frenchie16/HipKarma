from django.contrib import admin
from .models import Instance, Group, KarmicEntity, Karma

admin.site.register(Instance)
admin.site.register(Group)
admin.site.register(KarmicEntity)
admin.site.register(Karma)
