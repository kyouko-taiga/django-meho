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
from meho.models.fields import CredentialsField

class Credentials(models.Model):

    scheme = models.CharField(max_length=200)
    origin = models.CharField(max_length=200)
    data = CredentialsField()

    def __str__(self):
        return '({0},{1}): {2}'.format(self.scheme, self.origin, self.data)

    class Meta:
        app_label = 'meho'
