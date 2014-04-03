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

import uuid

from django.conf import settings
from django.db import models
from meho.models.fields import URNField

class Media(models.Model):

    urn         = URNField(primary_key=True, default=lambda: uuid.uuid1().urn)
    public_url  = models.URLField(blank=True)
    media_type  = models.CharField(max_length=100, blank=True)
    status      = models.CharField(max_length=100, blank=True, default='ready')
    parent      = models.ForeignKey('self', blank=True, null=True)

    # Expected syntax for private_url is actually the same as the URL syntax as
    # defined in RFC 3986. However, since django built-in URLField only accepts
    # 'http', 'https', 'ftp' and 'ftps' as valid schemes, ``private_url`` fields
    # can't use the same validator.
    private_url = models.CharField(max_length=200)

    def get_api_url(self):
        from django.core.urlresolvers import reverse
        return reverse('api_media_one', kwargs={'pk': self.urn})

    def clean(self):
        # try to guess the media type if not provided
        if not self.media_type and self.private_url:
            from meho.core.volumes import VolumeSelector
            from mimetypes import guess_type

            selector = VolumeSelector()
            volume = selector.backend_for(selector.scheme(self.private_url))()
            mime, encoding = guess_type(volume.filename(self.private_url))
            if mime:
                self.media_type = mime
            if encoding:
                self.media_type += '; ' if mime else ''
                self.media_type += encoding

    def __str__(self):
        return self.urn

    class Meta:
        app_label = 'meho'
        verbose_name_plural = 'media'

class Metadata(models.Model):

    media       = models.ForeignKey(Media)
    name        = models.CharField(max_length=200)
    content     = models.CharField(max_length=200)

    def __str__(self):
        return '{0}.{1}: {2}'.format(media, name, content)

    class Meta:
        app_label = 'meho'
