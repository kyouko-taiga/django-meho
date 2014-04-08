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
from requests.cookies import extract_cookies_to_jar
from django.utils.module_loading import import_by_path
from meho.core.volumes.base import VolumeDriver
from meho.models import Credentials
try:
    from urllib import parse as urlparse
except:
    import urlparse

class WebdavVolumeDriver(VolumeDriver):

    class AutoAuth(requests.auth.AuthBase):

        def __init__(self, identities, volume_driver):
            self.identities = identities
            self.volume_driver = volume_driver
            self._handlers = {}

        def __call__(self, request, **kwargs):
            if request.url in self._handlers:
                # attach an already built auth handler
                return self._handlers[request.url](request, **kwargs)
            else:
                # add a hook to the request so it calls _retry_401 if it fails
                request.register_hook('response', self._retry_401)
                return request

        def reset(self):
            self._handlers = {}

        def _retry_401(self, response, **kwargs):
            if response.status_code != 401:
                return response

            auth_scheme = response.headers.get('www-authenticate', '').split(' ')[0].lower()
            origin = self.volume_driver.netloc(response.url)

            try:
                identity = self.identities.get(scheme=auth_scheme, origin=origin).data
            except Credentials.DoesNotExist:
                identity = None

            auth_class = meho_settings.MEHO_AUTH_BACKENDS.get(auth_scheme, None)
            if identity and auth_class:
                # set authentication handler for requested url
                auth = import_by_path(auth_class)(**identity)
                self._handlers[response.url] = auth

                # consume content and release the original connection
                # to allow our new request to reuse the same one
                response.content
                response.raw.release_conn()
                prep = auth(response.request.copy())
                extract_cookies_to_jar(prep._cookies, response.request, response.raw)
                prep.prepare_cookies(prep._cookies)

                _r = response.connection.send(prep, **kwargs)
                _r.history.append(response)
                _r.request = prep
                return _r
            else:
                raise ImproperlyConfigured(
                    'No authentication credentials for "%(origin)s" with scheme '
                    '"%(scheme)s". Either provide credentials within the file '
                    'name or set credentials for (%(origin)s, %(scheme)s).' % {
                        'origin': origin,
                        'scheme': auth_scheme
                    })

    def __init__(self, identities=None):
        self.identities = identities or Credentials.objects
        self.auth_handler = WebdavVolumeDriver.AutoAuth(self.identities, self)

    @property
    def volume_scheme(self):
        return 'http'

    def open(self, name, mode='r'):
        return WebdavFileWrapper(self, name, mode)

    def save(self, name, content):
        # issue #2: cannot write file content with HTTP Digest authentication
        self._write(name, content)

    def delete(self, name):
        response = requests.delete(name, auth=self.auth_handler)

    def exists(self, name):
        response = requests.head(name, auth=self.auth_handler)
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        else:
            response.raise_for_status()

    def url(self, name):
        return re.sub(r'\/\/.*:?.*@', '//', name)

    def _read(self, name):
        response = requests.get(name, auth=self.auth_handler)
        temporary_file = tempfile.TemporaryFile()
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                temporary_file.write(chunk)
                temporary_file.flush()
        temporary_file.seek(0)
        return temporary_file

    def _write(self, name, content):
        # create a directories if required
        self._mkdirs(name)

        # we send a HEAD request before sending the actual data so we can load
        # authentication credentials without reading the file about te be sent
        requests.head(name, auth=self.auth_handler)
        requests.put(name, auth=self.auth_handler, data=content)

    def _mkdirs(self, name):
        file_url = self.url(name)
        file_path = self.filename(name)
        url_split = urlparse.urlsplit(file_url)
        base_url = urlparse.urlunsplit((url_split.scheme, url_split.netloc, '', '', ''))

        for directory in file_path.split('/')[1:-1]:
            base_url = urlparse.urljoin(base_url, directory + '/')
            if not self.exists(base_url):
                requests.request('MKCOL', base_url, auth=self.auth_handler)

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
        if not self._file:
            return

        if 'r' not in self._mode:
            self._file.seek(0)
            self._volume_driver._write(self._name, self._file)
        return self._file.close()
