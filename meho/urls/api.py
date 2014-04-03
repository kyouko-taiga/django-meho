# This source file is part of django-meho
# Main Developer : Dimitri Racordon (kyouko.taiga@gmail.com)
#
# Copyright 2013 Dimitri Racordon
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.conf.urls import patterns, include, url
from meho.views.api import media

URN_REGEX = r"urn:[a-zA-Z0-9][a-zA-Z0-9-]{1,31}:([a-zA-Z0-9()+,.:=@;$_!*'-]|%[0-9A-Fa-f]{2})+"

urlpatterns = patterns('',
    url(r'^version$', 'meho.views.api.version', name='api_version'),

    url(r'^files/(?P<filename>[\w\-\./]+)$', 'meho.views.api.upload', name='api_file_upload'),

    url(r'^media$', media.MediaCrudView.as_view(), name='api_media_unnamed'),
    url(r'^media/$', media.MediaCrudView.as_view(), name='api_media_list'),
    url(r'^media/(?P<pk>%s)$' % URN_REGEX, media.MediaCrudView.as_view(), name='api_media_one'),

    #url(r'^media$', 'meho.views.api.media.create', name='api_media_create'),
    #url(r'^media/$', 'meho.views.api.media.search', name='api_media_search'),
    #url(r'^media/(?P<urn>{0})$'.format(URN_REGEX),
    #    'meho.views.api.media.single', name='api_media_single_old'),
    #url(r'^media/(?P<urn>{0})/transcode/$'.format(URN_REGEX),
    #    'meho.views.api.media.transcode', name='api_media_transcode'),

    url(r'^tasks/(?P<task_id>.+)$', 'meho.views.api.tasks.single', name='api_task_single'),
)
