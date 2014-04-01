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

from django.core.cache import cache
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.http import require_safe

@require_safe
def single(request, task_id):
    # retrieve task status from the cache
    task_status = cache.get(task_id)
    if task_status:
        return HttpResponse(json.dumps(task_status), content_type='application/json')

    # specified task could not be found within the cache, maybe it expired
    return HttpResponseNotFound('Task not found.')
