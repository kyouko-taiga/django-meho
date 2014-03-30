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

from django.db.models.fields import CharField
from django.utils.translation import ugettext_lazy as _
from meho.core import validators
from meho.forms.fields import URNFormField

class URNField(CharField):

    default_validators = [validators.validate_urn]
    description = _('URN')

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 200)
        CharField.__init__(self, *args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': URNFormField}
        defaults.update(kwargs)
        return super(CharField, self).formfield(**defaults)
