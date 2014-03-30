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
import meho.settings as meho_settings

from django.core import serializers
from django.core.files.storage import default_storage
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from meho.auth import basic_http_auth
from meho.core.encoders import load_encoder
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

    # retrieve media parameters
    urn = urn or str(uuid.uuid1().urn)
    parent = request.POST.get('parent', None)
    try:
        private_url = request.POST['private-url']
        media_type = request.POST['media-type']
    except KeyError as e:
        return HttpResponseBadRequest(str(e) + ' is required')

    # create the new media
    media = Media(urn=urn, private_url=private_url, media_type=media_type, parent=parent)
    media.save()

    # return the freshly created media
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
def transcode(request, user, urn):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # retrieve input media
    media_in = get_object_or_404(Media, urn=urn)

    # retrieve output media parameters
    media_out_urn = request.POST.get('out-urn', uuid.uuid1().urn)
    media_out_private_url = 'tmp:///' + slugify(media_out_urn)
    media_out_parent = media_in
    try:
        media_out_type = request.POST['out-media-type']
    except KeyError as e:
        return HttpResponseBadRequest(str(e) + ' is required')

    # create output media
    media_out = Media(urn=media_out_urn, private_url=media_out_private_url,
        media_type=media_out_type, parent=media_out_parent)
    media_out.save()

    # start transcoding job profile
    encoder = request.POST.get('encoder', meho_settings.MEHO_DEFAULT_ENCODER)
    encoder_string = request.POST.get('encoder-string', '')
    if encoder not in meho_settings.MEHO_ENCODERS:
        return HttpResponseBadRequest(encoder + ' is not a valid encoder.')

    encoder = load_encoder(meho_settings.MEHO_ENCODERS[encoder])
    encoder.transcode(media_in, media_out, encoder_string)

    # return the freshly created media
    json_serializer = serializers.get_serializer('json')()
    response = json_serializer.serialize([media,], ensure_ascii=False, use_natural_keys=True)
    return HttpResponse(response, content_type='application/json')
