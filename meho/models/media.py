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

    urn = URNField(primary_key=True, default=lambda: uuid.uuid1().urn)
    private_url = models.URLField()
    public_url = models.URLField(null=True)
    media_type = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True)

    def __str__(self):
        return self.urn

    class Meta:
        app_label = 'meho'

class Metadata(models.Model):

    media = models.ForeignKey(Media)
    name = models.CharField(max_length=200)
    content = models.CharField(max_length=200)

    def __str__(self):
        return '{0}.{1}: {2}'.format(media, name, content)

    class Meta:
        app_label = 'meho'
