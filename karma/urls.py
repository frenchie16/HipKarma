from django.conf.urls import patterns, url
from . import views


urlpatterns = patterns('karma',
                       url(r'^$', views.index, name='index'),
                       url(r'^capabilities/$', views.capabilities, name='capabilities'),
                       url(r'^install/$', views.install, name='install'),
                       url(r'^install/(?P<client_id>\S*$)', views.uninstall, name='uninstall'),
                       url(r'^hooks/give/$', views.give_hook, name='hooks.give'),
                       url(r'^hooks/show/$', views.show_hook, name='hooks.show'),
                       url(r'^hooks/help/$', views.help_hook, name='hooks.help'))
