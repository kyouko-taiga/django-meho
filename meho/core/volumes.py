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

import errno
import os
import shutil
import uuid
import meho.settings as meho_settings

from django.utils._os import safe_join
from django.utils.module_loading import import_by_path
try:
    from urllib import parse as urlparse
except:
    import urlparse

class VolumeDriver(object):

    def scheme(self, name):
        """
        Returns the URL scheme of the file specified by ``name``.
        """
        return urlparse.urlparse(name).scheme

    def credentials(self, name):
        """
        Returns the credentials supplied whithin ``name``, returning a 2-tuple; the first item
        begin ``username``, the second item being ``password``. If no credentials are supplied,
        returns ``None``.
        """
        netloc = urlparse.urlparse(name).netloc
        if '@' not in netloc:
            return None

        try:
            # try to extract both username and password from credentials
            usr, pwd = netloc.split('@')[0].split(':')
        except ValueError:
            # extract only the username from credentials
            usr = netloc.split('@')[0]
            pwd = None
        return (usr, pwd)

    def open(self, name, mode='rb'):
        """
        Retrieves the specified file from the volume.
        """
        raise NotImplementedError()

    def save(self, name, content):
        """
        Saves new content to the file specified by ``name``. The content should be a proper python
        file-like object. If ``file`` already exists and is not a directory, it will be replaced
        silently.
        """
        raise NotImplementedError()

    def delete(self, name):
        """
        Deletes the file specified by ``name`` from the volume.
        """
        raise NotImplementedError()

    def exists(self, name):
        """
        Returns True if a file specified by ``name`` already exists on the volume.
        """
        raise NotImplementedError()

    def listdir(self, path):
        """
        Lists the contents of the specified ``path``, returning a 2-tuple of lists; the first item
        being directories, the second item being files.
        """
        raise NotImplementedError()

    def path(self, name):
        """
        Returns a local filesystem path where the file spcified by ``name`` can be retrieved using
        python's built-in ``open`` function. Volume drivers that can't be accessed using ``open``
        should *not* implement this method.
        """
        raise NotImplementedError("This backend doesn't support absolute paths.")

class FileSystemVolumeDriver(VolumeDriver):

    def open(self, name, mode='rb'):
        return open(self.path(name), mode=mode)

    def save(self, name, content):
        assert name, 'The name argument is not allowed to be empty.'

        # write content to a temporary file
        tmp_name = os.path.join(meho_settings.MEHO_TEMP_ROOT, str(uuid.uuid4()))
        with open(tmp_name, 'wb') as tmp_file:
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
        return urlparse.urlparse(name).path

class TemporaryVolumeDriver(FileSystemVolumeDriver):

    def __init__(self, root=None):
        self.root = root or meho_settings.MEHO_TEMP_ROOT

    def path(self, name):
        return safe_join(self.root, urlparse.urlparse(name).path.lstrip('/'))

class VolumeSelector(object):

    def __init__(self, backends=None):
        if not backends:
            backends = meho_settings.MEHO_VOLUME_BACKENDS
        self.backends = {}

        for scheme, backend in backends.items():
            self.backends[scheme] = import_by_path(backend)

    def scheme(self, name):
        """
        Returns the URL scheme of the file specified by ``name``.
        """
        return urlparse.urlparse(name).scheme

    def backend_for(self, scheme):
        """
        Returns the backend class that handles ``scheme``.
        """
        return self.backends[scheme]
