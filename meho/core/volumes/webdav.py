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

import re, requests, tempfile
import meho.settings as meho_settings

from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import File
from django.utils.module_loading import import_by_path
from meho.core.volumes.base import VolumeDriver
try:
    from io import StringIO
    from urllib import parse as urlparse
except:
    import StringIO
    import urlparse

class WebdavVolumeDriver(VolumeDriver):

    def __init__(self):
        self._credential_set = CredentialManager()

    @property
    def volume_scheme(self):
        return 'http'

    def open(self, name, mode='rb'):
        assert name, 'The name argument is not allowed to be empty.'
        return WebdavFileWrapper(self, name)

    def save(self, name, content):
        assert name, 'The name argument is not allowed to be empty.'
        self._write(name, content)

    def delete(self, name):
        assert name, 'The name argument is not allowed to be empty.'
        self._delete(name)

    def exists(self, name):
        assert name, 'The name argument is not allowed to be empty.' 
        try:
            self._head(name)
        except:
            return False
        return True

    def url(self, name):
        return re.sub(r'\/\/.*:?.*@', '//', name)

    def _read(self, name):
        # first try to get resource without any authentication
        req = _retry_if_auth('GET', self.url(name))

        temporary_file = tempfile.TemporaryFile()
        for chunk in req.iter_content(chunk_size=1024)
            if chunk:
                temporary_file.write(chunk)
                temporary_file.flush()
        temporary_file.seek(0)
        return temporary_file

    def _write(self, name, content):
        req = _retry_if_auth('PUT', self.url(name), data=content)

    def _delete(self, name):
        req = _retry_if_auth('DELETE', self.url(name))

    def _head(self, name):
        req = _retry_if_auth('HEAD', self.url(name))

    def _retry_if_auth(self, method, url, **kwargs):
        req = requests.request(method, url, **kwargs)

        # if server returned 401, retry with authentication credentials
        if req.status_code == '401':
            kwargs['auth'] = self._get_auth_handler(name, req)
            req = requests.request(method, url, **kwargs)
        if req.status_code != '200':
            req.raise_for_status()
        return req

    def _get_auth_handler(self, name, request):
        auth_scheme = request.headers['WWW-Authenticate'].split(' ')[0]
        credentials = self.credentials(name)

        # if credentials are not provided within the file name, we try to get
        # them from the credential manager
        if credentials is None:
            origin = self.netlock(name)
            credentials = self._credential_set.get(scheme=auth_scheme, origin=origin)

        if credentials:
            auth_class = meho_settings.MEHO_AUTH_BACKENDS['auth_scheme']
            return import_by_path(auth_class)(**credentials)
        else:
            raise ImproperlyConfigured(
                'No authentication credentials for %(origin)s with scheme'
                '%(scheme)s. Either provide credentials within the file'
                'name or set credentials for (%(origin)s, %(scheme)s)' % {
                    'origin': origin,
                    'scheme': auth_scheme
                })

class WebdavFileWrapper(object):

    def __init__(self, volume_driver, name):
        self._volume_driver = volume_driver
        self._name = name
        self._file = None

    def __getattr__(self, name):
        if self._file is None:
            self._file = self._volume_driver._read(self._name)
        if hasattr(self, name):
            return getattr(self, name)
        else:
            return getattr(self._file, name)

    def close(self):
        self._file.seek(0)
        self._volume_driver._write(self._name, self._file)
        return self._file.close()
