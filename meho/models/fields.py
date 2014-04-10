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

import json

from collections.abc import Mapping
from django.db import models
from django.db.models.fields import CharField, TextField
from django.utils.translation import ugettext_lazy as _
from meho.core import validators
from meho.forms.fields import URNFormField

class URNField(CharField):

    description = _('URN')

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 200)
        CharField.__init__(self, *args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': URNFormField}
        defaults.update(kwargs)
        return super(CharField, self).formfield(**defaults)

class CredentialsField(TextField, metaclass=models.SubfieldBase):

    description = _('Dictionary-like object to contain credentials.')

    def __init__(self, *args, **kwargs):
        TextField.__init__(self, *args, **kwargs)

    def to_python(self, value):
        if isinstance(value, Mapping):
            return value
        return json.loads(value.decode('utf-8'))
    
    def get_prep_value(self, value):
        return json.dumps(value).encode('utf-8')
