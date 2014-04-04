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

import errno, os, shutil

from django.conf import settings
from django.utils.six.moves.urllib.parse import urljoin
from django.utils._os import safe_join, abspathu
from meho.core.volumes import VolumeSelector

class SymlinkOrCopyPublisher(object):

    def __init__(self, root=None, base_url=None, file_permissions_mode=None,
            directory_permissions_mode=None):
        if root is None:
            root = settings.MEDIA_ROOT
        self.root = abspathu(root)
        if base_url is None:
            base_url = settings.MEDIA_URL
        self.base_url = base_url

        if file_permissions_mode is not None:
            self.file_permissions_mode = file_permissions_mode
        else:
            self.file_permissions_mode = settings.FILE_UPLOAD_PERMISSIONS
        if directory_permissions_mode is not None:
            self.directory_permissions_mode = directory_permissions_mode
        else:
            self.directory_permissions_mode = settings.FILE_UPLOAD_DIRECTORY_PERMISSIONS

    def publish(self, media, public_name):
        if media.public_url:
            raise ValueError("%(media)s is already published on %(url)s" % {
                'media': str(media),
                'url': media.public_url
            })

        selector = VolumeSelector()
        volume = selector.backend_for(selector.scheme(media.private_url))()

        try:
            private_path = volume.path(media.private_url)
            symlink = True
        except NotImplementedError:
            with volume.open(media.private_url) as f:
                private_path = self._local_copy(f)
            symlink = False

        # check that the publication path doesn't override an existing file
        publication_path = safe_join(self.root, public_name)
        if os.path.exists(publication_path):
            raise ValueError("The publication path is not available.")

        # create any intermediate directories to the publication path that do not exist
        directory = os.path.dirname(publication_path)
        if not os.path.exists(directory):
            try:
                if self.directory_permissions_mode is not None:
                    # os.makedirs applies the global umask, so we reset it,
                    # for consistency with file_permissions_mode behavior.
                    old_umask = os.umask(0)
                    try:
                        os.makedirs(directory, self.directory_permissions_mode)
                    finally:
                        os.umask(old_umask)
                else:
                    os.makedirs(directory)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
        if not os.path.isdir(directory):
            raise IOError("%s exists and is not a directory." % directory)

        # create a symlink or a copy to the file being published
        if symlink:
            os.symlink(private_path, publication_path)
        else:
            os.rename(private_path, publication_path)

        # compute and return publication url
        media.public_url = urljoin(self.base_url, public_name)
        media.save()
        return media.public_url

    def unpublish(self, media):
        public_name = media.public_url.replace(self.base_url, '', 1)
        publication_path = safe_join(self.root, public_name)
        if not os.path.exists(publication_path):
            raise ValueError("%(media)s not found among the publication paths" % {
                'media': str(media)
            })

        os.remove(publication_path)
        media.public_url = ''
        media.save()

    def _local_copy(self, content):
        """
        Saves ``content`` to a local temporary file and returns its name; ``content`` should be a
        proper python file-like object.
        """
        (fd, tmp_name) = tempfile.mkstemp()
        with open(fd, 'wb') as tmp_file:
            shutil.copyfileobj(content, tmp_file)
        return tmp_name    
