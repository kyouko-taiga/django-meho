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
from meho.auth.backends import AutoAuth
from meho.models import Credentials
try:
    from urllib import parse as urlparse
except:
    import urlparse

class WebdavVolumeDriver(VolumeDriver):

    def __init__(self, identities=None):
        self.identities = identities or Credentials.objects
        self.auth_handler = AutoAuth(self.identities)

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
