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
import os, tempfile
import meho.settings as meho_settings

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.generic import View
from django.views.generic.edit import ModelFormMixin
from django.utils.decorators import method_decorator

from meho.auth.decorators import basic_http_auth
from meho.models import Media
from meho.core.encoders import load_encoder
from meho.core.publishers import PublisherSelector
from meho.views.api.crud import ReadMixin, EditMixin, CrudView

class MediaCrudView(CrudView):

    model = Media
    fields = ['urn', 'private_url', 'media_type', 'parent']

    @method_decorator(basic_http_auth(realm='api'))
    def put(self, request, user, pk=None):
        rq_body = self.parse_request_body()
        overwrite = rq_body['overwrite'] if 'overwrite' in rq_body else False
        return super(MediaCrudView, self).put(request, overwrite=overwrite)

    @method_decorator(basic_http_auth(realm='api'))
    def get(self, request, user, pk=None):
        return super(MediaCrudView, self).get(request)

    @method_decorator(basic_http_auth(realm='api'))
    def post(self, request, user, pk=None):
        return super(MediaCrudView, self).post(request)

    @method_decorator(basic_http_auth(realm='api'))
    def delete(self, request, user, pk=None):
        return super(MediaCrudView, self).delete(request)

class TranscodeView(EditMixin, View):

    model = Media
    fields = ['urn', 'private_url', 'media_type']

    @method_decorator(basic_http_auth(realm='api'))
    def post(self, request, user, pk):
        # retrieve input media
        media_in = self.get_object()

        # retrieve request parameters
        rq_body = self.parse_request_body()
        media_out_kwargs = self.get_object_kwargs()
        media_out_kwargs['status'] = 'transcoding'
        media_out_kwargs['parent'] = media_in
        if 'private_url' not in media_out_kwargs:
            return self.invalid_request_body('Output private_url is required')

        # create output media
        media_out = Media(**media_out_kwargs)
        media_out.save()

        # start transcoding job
        encoder = rq_body.get('encoder', meho_settings.MEHO_DEFAULT_ENCODER)
        encoder_string = rq_body.get('encoder_string', '')
        if encoder not in meho_settings.MEHO_ENCODERS:
            return HttpResponseBadRequest(encoder + ' is not a valid encoder.')

        encoder = load_encoder(meho_settings.MEHO_ENCODERS[encoder])()
        encoder.transcode(media_in, media_out, encoder_string)

        # return the freshly created media
        self.object = media_out
        return self.render_object()

class PublishView(EditMixin, View):

    model = Media

    @method_decorator(basic_http_auth(realm='api'))
    def post(self, request, user, pk):
        rq_body = self.parse_request_body()
        if 'publisher' not in rq_body:
            return self.invalid_request_body('publisher is required')
        if 'publisher_options' not in rq_body:
            return self.invalid_request_body('publisher_options is required')

        publisher = PublisherSelector().backend_for(rq_body['publisher'])()
        publisher_options = rq_body['publisher_options']

        self.object = self.get_object()
        try:
            publisher.publish(self.object, **publisher_options)
        except ValueError as e:
            return self.invalid_request_body(str(e))

        return self.render_object()

class UnpublishView(EditMixin, View):

    model = Media

    @method_decorator(basic_http_auth(realm='api'))
    def post(self, request, user, pk):
        rq_body = self.parse_request_body()
        if 'publisher' not in rq_body:
            return self.invalid_request_body('publisher is required')

        publisher = PublisherSelector().backend_for(rq_body['publisher'])()
        publisher_options = rq_body.get('publisher_options', {})

        self.object = self.get_object()
        try:
            publisher.unpublish(self.object, **publisher_options)
        except ValueError:
            self.invalid_request_body(str(e))

        return self.render_object()
