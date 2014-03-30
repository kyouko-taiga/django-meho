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

import importlib
import os
import meho.settings as meho_settings

try:
    from urllib import parse as urlparse
except:
    import urlparse

class LocatorFactory(object):

    def get_locator(self, url, *args, **kwargs):
        # extract sheme from url scheme
        el = urlparse.urlparse(url)
        scheme = el.scheme

        # return an instance of the corresponding locator
        module_name, class_name = meho_settings.MEHO_FILE_LOCATORS[scheme].rsplit('.', 1)
        locator = getattr(importlib.import_module(module_name), class_name)
        return locator(*args, **kwargs)

class FileSystemLocator(object):

    def open(self, url, *args, **kwargs):
        el = urlparse.urlparse(url)
        file = os.path.expanduser(el.path)
        return open(file, *args, **kwargs)

class TemporaryFileLocator(object):

    def __init__(self, *args, **kwargs):
        self.temp_root = kwargs.get('temp_root', meho_settings.MEHO_TEMP_ROOT)

    def open(self, url, *args, **kwargs):
        el = urlparse.urlparse(url)
        file = os.path.join(self.temp_root, os.path.expanduser(el.path.lstrip('/')))
        return open(file, *args, **kwargs)
