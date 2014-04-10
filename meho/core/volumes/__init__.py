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

import meho.settings as meho_settings

from django.utils.module_loading import import_by_path
try:
    from urllib import parse as urlparse
except:
    import urlparse

from meho.core.volumes.base import VolumeDriver
from meho.core.volumes.filesystem import FileSystemVolumeDriver, TemporaryVolumeDriver
from meho.core.volumes.webdav import WebdavVolumeDriver

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
