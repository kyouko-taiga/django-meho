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

from django.db import models

class Movie(models.Model):

    title = models.CharField(max_length=100)
    title_orig = models.CharField(max_length=100, blank=True)
    slug = models.SlugField()
    media_set = models.ManyToManyField('meho.Media', null=True)

    def __str__(self):
        return self.title    

    class Meta:
        app_label = 'meho'

class Serie(models.Model):

    title = models.CharField(max_length=100)
    title_orig = models.CharField(max_length=100, blank=True)
    slug = models.SlugField()

    def __str__(self):
        return self.title

    class Meta:
        app_label = 'meho'

class Episode(models.Model):

    title = models.CharField(max_length=100, blank=True)
    number = models.IntegerField()
    serie = models.ForeignKey(Serie)
    media_set = models.ManyToManyField('meho.Media', null=True)

    def __str__(self):
        return '{0} episode {1}'.format(serie.title, number)

    class Meta:
        app_label = 'meho'
        ordering = ('number',)
