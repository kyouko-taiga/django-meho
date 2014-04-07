#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import os
from setuptools import setup, find_packages
from codecs import open

# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname), 'r', encoding='utf-8').read()

setup(
    name = "meho",
    version = "0.1.0",
    author = "Dimitri Racordon",
    author_email = "kyouko.taiga@gmail.com",
    description = ("A Django reusable app for multimedia encoding and hosting."),
    license = "Apache 2.0",
    keywords = "django multimedia encoding hosting",
    url = "https://github.com/kyouko-taiga/paya",
    packages = find_packages(),
    long_description = read('README.md'),
    classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "Topic :: Multimedia",
        "License :: OSI Approved :: Apache Software License",
    ],
    extras_require = {},
    install_requires = ['django', 'requests'],
    entry_points={},
)