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
import tempfile
import uuid

from django.core import serializers
from django.core.files.storage import default_storage
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
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

    urn         = urn or str(uuid.uuid1().urn)
    url         = request.POST.get('url', None)
    file        = 
    mime_type   = request.POST.get('mime-type', None)
    parent      = request.POST.get('parent', None)
    
    media = Media(urn=urn, url=url, file=file, mime_type=mime_type, parent=parent)
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

@basic_http_auth(realm='api')
def transcode(request, user):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # retrieve media inut and output
    media_in  = get_object_or_404(Media, urn=request.POST.get('in-urn', None))
    try:
        media_out = Media(
            urn=request.POST.get('out-urn', uuid.uuid1().urn),
            url='file://' + os.path.join(tempfile.mkdtemp(), str(uuid.uuid4())),
            published=False,
            mime_type=request.POST.get('out-mime', ''),
            parent=media_in)
