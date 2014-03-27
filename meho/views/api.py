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

import json
import os
import re
import uuid

from django import forms
from django.core import serializers
from django.conf import settings
from django.core.files.uploadhandler import FileUploadHandler
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from meho.auth import basic_http_auth
from meho.models import Media

@ensure_csrf_cookie
def version(request):
    return HttpResponse(json.dumps({'version': '0.1'}), content_type='application/json')

@basic_http_auth(realm='api')
def upload(request, user, filename):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # create file path if necessery (delete symbolic references to ., .. and leading /)
    filename = re.sub(r'\.?\./', '', filename).lstrip('/')
    filename = os.path.join(settings.MEDIA_ROOT, filename)
    filename = os.path.realpath(filename)
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))

    with open(filename, 'wb+') as f:
        for chunk in request.FILES['file'].chunks():
            f.write(chunk)

    file_url = settings.MEDIA_URL + filename.replace(settings.MEDIA_ROOT, '').lstrip('/')
    return HttpResponse(json.dumps([{'file': {'url': file_url}}]), content_type='application/json')
    # return HttpResponseRedirect(file_url)

@basic_http_auth(realm='api')
def media_list(request, user):
    # get a queryset over all media, with optional filters
    objects = Media.objects.filter(**{k: v for k,v in request.GET.items()})

    json_serializer = serializers.get_serializer('json')()
    response = json_serializer.serialize(objects, ensure_ascii=False, use_natural_keys=True)
    return HttpResponse(response, content_type='application/json')

@basic_http_auth(realm='api')
def media_post(request, user, urn=None):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    urn     = urn or str(uuid.uuid1().urn)
    parent  = request.POST.get('parent', None)
    url     = request.POST.get('url', None)
    episode = request.POST.get('episode', None)
    
    media = Media(urn=urn, parent=parent, url=url, episode=episode)
    media.save()

    return HttpResponse(json.dumps(media))

@basic_http_auth(realm='api')
def media(request, user, urn):
    # create a new media object
    if request.method == 'POST':
        return media_post(request, uuid=media_uuid)

    # retrieve media object from its urn
    media = get_object_or_404(Media, urn=urn)
    json_serializer = serializers.get_serializer('json')()
    response = json_serializer.serialize([media,], ensure_ascii=False, use_natural_keys=True)

    # delete the media object is method is DELETE
    if request.method == 'DELETE':
        media.delete()

    # returns the retrieved object
    return HttpResponse(response, content_type='application/json')
