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

@basic_http_auth(realm='api')
def search(request, user):
    # get a queryset over all media, with optional filters
    objects = Media.objects.filter(**{k: v for k,v in request.GET.items()})

    json_serializer = serializers.get_serializer('json')()
    response = json_serializer.serialize(objects, ensure_ascii=False, use_natural_keys=True)
    return HttpResponse(response, content_type='application/json')

@basic_http_auth(realm='api')
def create(request, user, urn=None):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    urn     = urn or str(uuid.uuid1().urn)
    parent  = request.POST.get('parent', None)
    url     = request.POST.get('url', None)
    episode = request.POST.get('episode', None)
    
    media = Media(urn=urn, parent=parent, url=url, episode=episode)
    media.save()

    json_serializer = serializers.get_serializer('json')()
    response = json_serializer.serialize([media,], ensure_ascii=False, use_natural_keys=True)
    return HttpResponse(response, content_type='application/json')

@basic_http_auth(realm='api')
def single(request, user, urn):
    # create a new media object
    if request.method == 'POST':
        return create(request, uuid=media_uuid)

    # retrieve media object from its urn
    media = get_object_or_404(Media, urn=urn)
    json_serializer = serializers.get_serializer('json')()
    response = json_serializer.serialize([media,], ensure_ascii=False, use_natural_keys=True)

    # delete the media object is method is DELETE
    if request.method == 'DELETE':
        media.delete()

    # returns the retrieved object
    return HttpResponse(response, content_type='application/json')
