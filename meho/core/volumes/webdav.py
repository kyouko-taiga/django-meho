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
from meho.models import Credentials
try:
    from io import StringIO
    from urllib import parse as urlparse
except:
    import StringIO
    import urlparse

class WebdavVolumeDriver(VolumeDriver):

    def __init__(self, credential_set=None):
        self._credential_set = credential_set or Credentials.objects

    @property
    def volume_scheme(self):
        return 'http'

    def open(self, name, mode='r'):
        assert name, 'The name argument is not allowed to be empty.'
        return WebdavFileWrapper(self, name, mode)

    def save(self, name, content):
        assert name, 'The name argument is not allowed to be empty.'
        # upload issue: cannot write file content with HTTP Digest authentication
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
        req = self._retry_if_auth('GET', name)

        temporary_file = tempfile.TemporaryFile()
        for chunk in req.iter_content(chunk_size=1024):
            if chunk:
                temporary_file.write(chunk)
                temporary_file.flush()
        temporary_file.seek(0)
        return temporary_file

    def _write(self, name, content):
        req = self._retry_if_auth('PUT', name, data=content)

    def _delete(self, name):
        req = self._retry_if_auth('DELETE', name)

    def _head(self, name):
        req = self._retry_if_auth('HEAD', name)

    def _retry_if_auth(self, method, name, **kwargs):
        url = self.url(name)
        req = requests.request(method, url, **kwargs)

        # if server returned 401, retry with authentication credentials
        if req.status_code == 401:
            kwargs['auth'] = self._get_auth_handler(name, req)
            req = requests.request(method, url, **kwargs)
        if req.status_code != 200:
            req.raise_for_status()
        return req

    def _get_auth_handler(self, name, request):
        auth_scheme = request.headers['WWW-Authenticate'].split(' ')[0].lower()
        credentials = self.credentials(name)
        origin = self.netloc(name)

        # format credentials into kwargs style if provided within the file name
        if credentials is not None:
            credentials = {'username': credentials[0], 'password': credentials[1]}

        # if credentials are not provided within the file name, we try to get
        # them from the credential manager
        else:
            try:
                print 
                credentials = self._credential_set.get(scheme=auth_scheme, origin=origin).data
            except Credentials.DoesNotExist:
                credentials = None

        auth_class = meho_settings.MEHO_AUTH_BACKENDS.get(auth_scheme, None)
        if credentials and auth_class:
            return import_by_path(auth_class)(**credentials)
        else:
            raise ImproperlyConfigured(
                'No authentication credentials for "%(origin)s" with scheme '
                '"%(scheme)s". Either provide credentials within the file '
                'name or set credentials for (%(origin)s, %(scheme)s).' % {
                    'origin': origin,
                    'scheme': auth_scheme
                })

class WebdavFileWrapper(object):

    def __init__(self, volume_driver, name, mode):
        self._volume_driver = volume_driver
        self._name = name
        self._mode = mode
        self._file = None

    def __getattr__(self, name):
        if self._file is None:
            # if write mode, override any existing content of the remote file
            if 'w' in self._mode:
                self._file = tempfile.TemporaryFile()
            # otherwise fetch the content (read or append mode)
            else:
                self._file = self._volume_driver._read(self._name)
                # if append mode, seek end of the file
                if 'a' in self._mode:
                    self._file.seek(0,2)
        return getattr(self._file, name)

    def close(self):
        self._file.seek(0)
        self._volume_driver._write(self._name, self._file)
        return self._file.close()
