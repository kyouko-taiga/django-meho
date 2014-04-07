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

import re, requests
from meho.core.volumes.base import VolumeDriver

try:
    from urllib import parse as urlparse
except:
    import urlparse

class WebdavVolumeDriver(VolumeDriver):

    @property
    def volume_scheme(self):
        return 'http'

    def open(self, name, mode='rb'):
        return open(self.path(name), mode=mode)

    def save(self, name, content):
        assert name, 'The name argument is not allowed to be empty.'

        # write content to a temporary file
        (fd, tmp_name) = tempfile.mkstemp()
        with open(fd, 'wb') as tmp_file:
            shutil.copyfileobj(content, tmp_file)

        # try to create a directory for the location specified by name if required
        full_path = self.path(name)
        directory = os.path.dirname(full_path)
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
        if not os.path.isdir(directory):
            raise IOError('%s exists and is not a directory.' % directory)

        # move the temporary file to the location specified by name
        os.rename(tmp_name, full_path)

    def delete(self, name):
        assert name, 'The name argument is not allowed to be empty.'
        name = self.path(name)

        # If the file exists, delete it from the filesystem.
        # Note that there is a race between os.path.exists and os.remove:
        # if os.remove fails with ENOENT, the file was removed
        # concurrently, and we can continue normally.
        if os.path.exists(name):
            try:
                os.remove(name)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise

    def exists(self, name):
        return os.path.exists(self.path(name))

    def listdir(self, path):
        path = self.path(path)
        directories, files = [], []
        for entry in os.listdir(path):
            if os.path.isdir(os.path.join(path, entry)):
                directories.append(entry)
            else:
                files.append(entry)
        return directories, files

    def path(self, name):
        return self.filename(name)

    def _build_password_manager(self):
        password_manager = urlrequest.HTTPPasswordMgrWithDefaultRealm()
        credential_manager = CredentialManager()
        for c in credential_manager.filter(scheme='http'):
            password_manager.add_password(c.realm, c.uri, c.username, c.password)
        return password_manager

class WebdavFile(object):

    def __init__(self, name, mode, volume_driver):
        self._name = name
        self._mode = mode
        self._volume_driver = volume_driver
        self._temporary = None

    def read(self, size):
        if not self._temporary:
            # get a local copy of the remote file
            pass
