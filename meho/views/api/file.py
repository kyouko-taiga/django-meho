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

import re
import os

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotAllowed
from meho.auth import basic_http_auth

@basic_http_auth(realm='api')
def upload(request, user, filename):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # create file path if necessery (delete symbolic references to ., .. and leading /)
    filename = re.sub(r'\.?\./', '', filename).lstrip('/')
    filename = os.path.join(settings.MEDIA_ROOT, filename)
    filename = os.path.realpath(filename)
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))

    with open(filename, 'wb+') as f:
        for chunk in request.FILES['file'].chunks():
            f.write(chunk)

    file_url = settings.MEDIA_URL + filename.replace(settings.MEDIA_ROOT, '').lstrip('/')
    return HttpResponse(json.dumps([{'file': {'url': file_url}}]), content_type='application/json')
    # return HttpResponseRedirect(file_url)
