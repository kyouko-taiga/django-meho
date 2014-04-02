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
            return self.model._meta.verbose_name.lower()
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
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj

    def render_object(self, status=200):
        if not hasattr(self, 'object'):
            self.object = self.get_object()

        response = {
            'status': 'success',
            'data': {
                self.get_model_name(): model_to_dict(self.object)
            }
        }
        return HttpResponse(json.dumps(response), status=status, content_type='application/json')

class MultipleReadMixin(ReadMixin):
    """A mixin that provides a way to render multiple model instances."""

    def get_model_name_plural(self):
        if self.model:
            return self.model._meta.verbose_name_plural.lower()
        else:
            raise ImproperlyConfigured(
                "%(cls)s is missing a model. Define %(cls)s.model or override"
                "%(cls)s.get_model_name()." % {'cls': self.__class__.__name__}
            )

    def get_objects(self):
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

        response = {
            'status': 'success',
            'data': {
                self.get_model_name_plural(): [model_to_dict(o) for o in self.objects]
            }
        }
        return HttpResponse(json.dumps(response), status=status, content_type='application/json')

class EditMixin(SingleReadMixin):
    """A mixin that provides a way to handle the edition of an model object."""

    fields = None

    def get_object_kwargs(self):
        try:
            jrq_body = json.loads(request.body.decode('utf-8'))
        except ValueError:
            return self.invalid_request_body()

        model_name = self.get_model_name()
        if model_name in jrq_body and isinstance(jrq_body[model_name], Mapping):
            return {k:v for k,v in jrq_body[model_name].items() if k in fields}
        else:
            return self.invalid_request_body()

    def validate_object(self):
        if not hasattr(self, 'object'):
            self.object = self.get_object()
        try:
            self.object.full_clean()
        except ValidationError as e:
            return e.error_dict
        return None

    def invalid_request_body(self):
        response = {
            'status': 'error',
            'message': 'Invalid request body.'
        }
        return HttpResponse(json.dumps(response), status=400, content_type='application/json')

    def invalid_object(self, errors):
        response = {
            'status': 'error',
            'message': 'Invalid %s object.' % self.get_model_name(),
            'data': {
                'errors': errors
            }
        }
        return HttpResponse(json.dumps(response), status=400, content_type='application/json')

class CreateMixin(EditMixin):
    """A mixin that provides a way to handle the creation of a model object."""

    def create_object(self, override=False):
        # create and validate new object
        self.object = self.model(**self.get_object_kwargs())
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
        for field, value in self.get_object_kwargs():
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
        if self.pk_url_kwarg in self.kwargs:
            self.object = self.get_object()
            return self.render_object()
        else:
            self.objects = self.get_objects()
            return self.render_objects()

    def post(self, request, *args, **kwargs):
        return self.update_object()

    def delete(self, request, *args, **kwargs):
        return self.delete_object()
