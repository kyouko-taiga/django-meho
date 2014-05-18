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

from django.conf import settings as django_settings
from tempfile import gettempdir

MEHO_DEFAULT_ENCODER = getattr(django_settings, 'MEHO_DEFAULT_ENCODER', 'meho.encoders.FFmpeg')

MEHO_ENCODERS = getattr(django_settings, 'MEHO_ENCODERS', {
    'ffmpeg': 'meho.core.encoders.FFmpeg',
    'copy': 'meho.core.encoders.Copy'
})

MEHO_VOLUME_BACKENDS = getattr(django_settings, 'MEHO_VOLUME_BACKENDS', {
    'file': 'meho.core.volumes.FileSystemVolumeDriver',
    'tmp': 'meho.core.volumes.TemporaryVolumeDriver',
    'http': 'meho.core.volumes.WebdavVolumeDriver'
})

MEHO_PUBLISHER_BACKENDS = getattr(django_settings, 'MEHO_PUBLISHER_BACKENDS', {
    'symlink_or_copy': 'meho.core.publishers.SymlinkOrCopyPublisher',
})

MEHO_AUTH_BACKENDS = getattr(django_settings, 'MEHO_AUTH_BACKENDS', {
    'basic': 'requests.auth.HTTPBasicAuth',
    'digest': 'requests.auth.HTTPDigestAuth'
})

MEHO_TEMP_ROOT = getattr(django_settings, 'MEHO_TEMP_ROOT', gettempdir())
