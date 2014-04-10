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

import errno, os, shutil, tempfile, uuid
import meho.settings as meho_settings

from django.utils._os import safe_join
from meho.core.volumes.base import VolumeDriver

class FileSystemVolumeDriver(VolumeDriver):

    @property
    def volume_scheme(self):
        return 'file'

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

class TemporaryVolumeDriver(FileSystemVolumeDriver):

    def __init__(self, root=None):
        self.root = root or meho_settings.MEHO_TEMP_ROOT

    @property
    def volume_scheme(self):
        return 'tmp'

    def path(self, name):
        return safe_join(self.root, self.filename(name).lstrip('/'))
