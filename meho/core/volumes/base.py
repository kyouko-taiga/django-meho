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

try:
    from urllib import parse as urlparse
except:
    import urlparse

class VolumeDriver(object):

    @property
    def volume_scheme(self):
        raise NotImplementedError()

    def scheme(self, name):
        """
        Returns the URL scheme of the file specified by ``name``.
        """
        return urlparse.urlparse(name).scheme

    def netloc(self, name):
        """
        Returns the URL net location of the file specified by ``name``.
        """
        netloc = urlparse.urlparse(name).netloc
        return netloc.split('@')[0]

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

    def filename(self, name):
        """
        Returns the filename supplied whithin ``name``, as read by the volume.
        """
        return urlparse.urlparse(name).path

    def next_available_name(self):
        """
        Returns the next available free filename on the volume.
        """
        return str(uuid.uuid4())

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
        Returns a local filesystem path where the file specified by ``name`` can be retrieved using
        python's built-in ``open`` function. Volume drivers that can't expose files using ``open``
        should *not* implement this method.
        """
        raise NotImplementedError("This backend doesn't support absolute paths.")

    def url(self, name):
        """
        Returns a URL where the file specified by ``name`` can be retrieved using a HTTP GET
        request. Note that the resource may be protected by some authentication method even if
        no credentials are privided within the returned url. Volume drivers that can't expose files
        using HTTP GET should *not* implement this method.
        """
        raise NotImplementedError("This backend doesn't support HTTP access.")
