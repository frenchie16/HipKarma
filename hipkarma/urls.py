import karma.urls
import karma.views

from django.conf.urls import patterns, include, url
from django.contrib import admin


admin.autodiscover()

urlpatterns = patterns('',
                       url(r'^karma/', include(karma.urls)),
                       url(r'^$', karma.views.index, name='index'),
                       url(r'^admin/', include(admin.site.urls)))
