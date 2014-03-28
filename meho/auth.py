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

import base64

from django.contrib.auth import authenticate
from django.http import HttpResponse

class basic_http_auth(object):

    def __init__(self, realm=''):
        self.realm = realm

    def __call__(self, f):
        def wrap(request, *args, **kwargs):
            if request.META.get('HTTP_AUTHORIZATION', False):
                auth_type, auth = request.META['HTTP_AUTHORIZATION'].split(' ')
                auth = base64.b64decode(auth)
                username, password = auth.decode('utf-8').split(':')

                # try to authenticate the user
                user = authenticate(username=username, password=password)
                if user is not None:
                    return f(request, user, *args, **kwargs)

            r = HttpResponse('Authentication required', status=401)
            r['WWW-Authenticate'] = 'Basic realm="{0}"'.format(self.realm)
            return r
        return wrap
