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

from collections.abc import Mapping
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponse
from django.views.generic import View

class ReadMixin(object):
    """A mixin provides a way to get a queryset on a model."""

    model = None
    queryset = None

    def get_queryset(self):
        """
        Returns the ``QuerySet`` that will be used to look up the object.

        Note that this method is called by the default implementation of
        ``get_object`` and may not be called if ``get_object`` is overriden.
        """
        if self.queryset is None:
            if self.model:
                return self.model._default_manager.all()
            else:
                raise ImproperlyConfigured(
                    "%(cls)s is missing a QuerySet. Define "
                    "%(cls)s.model, %(cls)s.queryset, or override "
                    "%(cls)s.get_queryset()." % {
                        'cls': self.__class__.__name__
                    }
                )
        return self.queryset.all()

class SingleReadMixin(ReadMixin):
    """A mixin that provides a way to render a single model instance."""

    pk_url_kwarg = 'pk'

    def get_model_name(self):
        if self.model:
            return self.model._meta.verbose_name
        else:
            raise ImproperlyConfigured(
                "%(cls)s is missing a model. Define %(cls)s.model or override"
                "%(cls)s.get_model_name()." % {'cls': self.__class__.__name__}
            )

    def get_object(self, queryset=None):
        """
        Returns the object the view is rendering.

        By default this requires ``self.queryset`` and a ``pk`` argument in
        the URLconf, but subclasses can override this to return any object.
        """
        # use a custom queryset if provided
        if queryset is None:
            queryset = self.get_queryset()

        # next, try looking up by primary key.
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # if pk is not defined, it's an error.
        else:
            raise AttributeError("Generic detail view %s must be called with "
                                 "a pk." % self.__class__.__name__)

        try:
            # get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404("No %(verbose_name)s found matching the query" %
                {'verbose_name': queryset.model._meta.verbose_name})
        return obj

    def render_object(self, status=200):
        if not hasattr(self, 'object'):
            self.object = self.get_object()

        response = { self.get_model_name(): model_to_dict(self.object) }
        return HttpResponse(json.dumps(response), status=status, content_type='application/json')

class MultipleReadMixin(ReadMixin):
    """A mixin that provides a way to render multiple model instances."""

    def get_model_name_plural(self):
        if self.model:
            return self.model._meta.verbose_name_plural
        else:
            raise ImproperlyConfigured(
                "%(cls)s is missing a model. Define %(cls)s.model or override"
                "%(cls)s.get_model_name()." % {'cls': self.__class__.__name__}
            )

    def get_objects(self, queryset=None):
        """
        Returns the objects the view is rendering.

        By default this requires ``self.queryset``, but subclasses can
        override this to return any list of objects.
        """
        if queryset is None:
            queryset = self.get_queryset()
        return queryset.all()

    def render_objects(self, status=200):
        if not hasattr(self, 'objects'):
            self.objects = self.get_objects()

        response = { self.get_model_name_plural(): [model_to_dict(o) for o in self.objects] }
        return HttpResponse(json.dumps(response), status=status, content_type='application/json')

class EditMixin(SingleReadMixin):
    """A mixin that provides a way to handle the edition of an model object."""

    fields = None

    def parse_request_body(self):
        return json.loads(self.request.body.decode('utf-8')) 

    def get_object_kwargs(self):
        rq_body = self.parse_request_body()
        model_name = self.get_model_name()
        if model_name in rq_body and isinstance(rq_body[model_name], Mapping):
            return {k:v for k,v in rq_body[model_name].items() if k in self.fields}
        else:
            raise ValueError("Request data must contain a %s object." % self.get_model_name())

    def validate_object(self):
        if not hasattr(self, 'object'):
            self.object = self.get_object()
        try:
            self.object.full_clean()
        except ValidationError as e:
            return e.error_dict
        return None

    def invalid_request_body(self, reason=None):
        response = {
            'status': 'error',
            'message': 'Invalid request body.',
            'data': {
                'reason': reason
            }
        }
        return HttpResponse(json.dumps(response), status=400, content_type='application/json')

    def invalid_object(self, errors):
        errors_data = {}
        for field in errors:
            field_data = []
            for e in errors[field]:
                e = ValidationError(e)
                field_data.append({'message': e.messages[0], 'code': e.code})
            errors_data[field] = field_data

        response = {
            'status': 'error',
            'message': 'Invalid %s object.' % self.get_model_name(),
            'data': {
                'errors': errors_data
            }
        }
        return HttpResponse(json.dumps(response), status=400, content_type='application/json')

class CreateMixin(EditMixin):
    """A mixin that provides a way to handle the creation of a model object."""

    def create_object(self, override=False):
        # create and validate new object
        try:
            object_kwargs = self.get_object_kwargs()
        except ValueError as e:
            return self.invalid_request_body(str(e))
        self.object = self.model(**object_kwargs)
        errors = self.validate_object()
        if errors:
            return self.invalid_object(errors)

        # if pk is provided, check if it already designates an existing model instance
        if self.pk_url_kwarg in self.kwargs:
            try:
                existing_object = self.get_object()
                if override:
                    # delete existing instance
                    existing_object.delete()
                    self.object.pk = self.kwargs[self.pk_url_kwarg]
                else:
                    return self.duplicate_object(existing_object)
            except Http404: pass

        # save the new object
        self.object.save()
        return self.render_object(status=201)

    def duplicate_object(self, obj):
        response = {
            'status': 'error',
            'message': 'Duplicate object for key %s' % obj.pk
        }
        return HttpResponse(json.dumps(response), status=400, content_type='application/json')

class UpdateMixin(EditMixin):
    """A mixin that provides a way to handle the update of a model object."""

    def update_object(self):
        self.object = self.get_object()
        try:
            object_kwargs = self.get_object_kwargs()
        except ValueError as e:
            return self.invalid_request_body(str(e))
        
        for field, value in object_kwargs.items():
            setattr(self.object, field, value)
        errors = self.validate_object()
        if errors:
            return self.invalid_object(errors)

        # update the object
        self.object.save()
        return self.render_object()

class DeleteMixin(SingleReadMixin):
    """A mixin that provides a way to handle the deletion of a model object."""

    def delete_object(self):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse(status=204)

class CrudView(CreateMixin, MultipleReadMixin, UpdateMixin, DeleteMixin, View):
    """A class-based view for handling CRUD operations on a model."""

    def put(self, request, *args, **kwargs):
        return self.create_object(override=kwargs.get('override', False))

    def get(self, request, *args, **kwargs):
        # if a pk has been provided, render a single object
        if self.pk_url_kwarg in self.kwargs:
            self.object = self.get_object()
            return self.render_object()

        # otherwise if the requested path has a trailing '/', render a list of objects
        elif request.path[-1] == '/':
            queryset = self.get_queryset()
            if request.GET:
                # apply queryset filters if provided
                from urllib.parse import unquote
                queryset = queryset.filter(**{k: unquote(v) for k,v in request.GET.items()})

            self.objects = self.get_objects(queryset)
            return self.render_objects()

        # if it's neither a request for a single nor multiple objects, raise a 404
        raise Http404()

    def post(self, request, *args, **kwargs):
        return self.update_object()

    def delete(self, request, *args, **kwargs):
        return self.delete_object()
