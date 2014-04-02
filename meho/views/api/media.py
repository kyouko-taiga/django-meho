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
import tempfile
import uuid
import meho.settings as meho_settings

from django.core import serializers
from django.core.files.storage import default_storage
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from meho.auth import basic_http_auth
from meho.core.encoders import load_encoder

import json

from django.http import HttpResponseBadRequest
from django.views.generic import View
from django.views.generic.edit import ModelFormMixin
from django.utils.decorators import method_decorator
from meho.models import Media
from meho.views.api.crud import CrudView

class MediaCrudView(CrudView):

    model = Media
    fields = ['urn', 'private_url', 'media_type', 'parent']

    @method_decorator(basic_http_auth(realm='api'))
    def put(self, request, user, pk=None):
        return super(MediaCrudView, self).put(request, *args, **kwargs)

    @method_decorator(basic_http_auth(realm='api'))
    def get(self, request, user, pk=None):
        return super(MediaCrudView, self).get(request, *args, **kwargs)

    @method_decorator(basic_http_auth(realm='api'))
    def post(self, request, user, pk=None):
        return super(MediaCrudView, self).post(request, *args, **kwargs)

    @method_decorator(basic_http_auth(realm='api'))
    def delete(self, request, user, pk=None):
        return super(MediaCrudView, self).delete(request, *args, **kwargs)


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

    # retrieve request parameters
    rbody = json.loads(request.body.decode('utf-8'))

    try:
        urn         = urn or rbody['media'].get('urn', uuid.uuid1().urn)
        private_url = rbody['media'].get('private_url', 'tmp:///' + slugify(urn))
        media_type  = rbody['media'].get('media_type', '')
        parent      = rbody['media'].get('parent', None)
    except KeyError as e:
        return HttpResponseBadRequest(str(e) + ' is required.')

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

    # retrieve request parameters
    rbody = json.loads(request.body.decode('utf-8'))

    try:
        out_urn         = rbody['media'].get('urn', uuid.uuid1().urn)
        out_private_url = rbody['media'].get('private_url', 'tmp:///' + slugify(out_urn))
        out_media_type  = rbody['media'].get('media_type', '')
    except KeyError as e:
        return HttpResponseBadRequest(str(e) + ' is required.')

    # create output media
    media_out = Media(urn=out_urn, private_url=out_private_url, media_type=out_media_type,
        status='transcoding', parent=media_in)
    media_out.save()

    # start transcoding job
    encoder = rbody.get('encoder', meho_settings.MEHO_DEFAULT_ENCODER)
    encoder_string = rbody.get('encoder-string', '')
    if encoder not in meho_settings.MEHO_ENCODERS:
        return HttpResponseBadRequest(encoder + ' is not a valid encoder.')

    encoder = load_encoder(meho_settings.MEHO_ENCODERS[encoder])()
    encoder.transcode(media_in, media_out, encoder_string)

    # return the freshly created media
    json_serializer = serializers.get_serializer('json')()
    response = json_serializer.serialize([media_out,], ensure_ascii=False, use_natural_keys=True)
    return HttpResponse(response, content_type='application/json')
