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

from meho.core.volumes import VolumeSelector, TemporaryVolumeDriver

class Copy(object):

    def transcode(self, media_in, media_out, encoder_string=''):
        # get file locators for input/output media
        selector   = VolumeSelector()
        volume_in  = selector.backend_for(selector.scheme(media_in.private_url))()
        volume_out = selector.backend_for(selector.scheme(media_out.private_url))()

        # copy input file into output
        with volume_in.open(media_in.private_url, 'rb') as i:
            volume_out.save(media_out.private_url, i)
