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

from requests.auth import AuthBase

class AutoAuth(AuthBase):

    def __init__(self, identities):
        self.identities = identities
        self._handlers = {}

    def __call__(self, request, **kwargs):
        if request.url in self._handlers:
            # attach an already built auth handler
            return self._handlers[request.url](request, **kwargs)
        else:
            # add a hook to the request so it calls _retry_401 if it fails
            request.register_hook('response', self._retry_401)
            return request

    def reset(self):
        self._handlers = {}

    def netloc(self, name):
        netloc = urlparse.urlparse(name).netloc
        if '@' in netloc:
            return netloc.split('@')[1]
        else:
            return netloc

    def _retry_401(self, response, **kwargs):
        if response.status_code != 401:
            return response

        auth_scheme = response.headers.get('www-authenticate', '').split(' ')[0].lower()
        origin = self.netloc(response.url)

        try:
            identity = self.identities.get(scheme=auth_scheme, origin=origin).data
        except Credentials.DoesNotExist:
            identity = None

        auth_class = meho_settings.MEHO_AUTH_BACKENDS.get(auth_scheme, None)
        if identity and auth_class:
            # set authentication handler for requested url
            auth = import_by_path(auth_class)(**identity)
            self._handlers[response.url] = auth

            # consume content and release the original connection
            # to allow our new request to reuse the same one
            response.content
            response.raw.release_conn()
            prep = auth(response.request.copy())
            extract_cookies_to_jar(prep._cookies, response.request, response.raw)
            prep.prepare_cookies(prep._cookies)

            _r = response.connection.send(prep, **kwargs)
            _r.history.append(response)
            _r.request = prep
            return _r
        else:
            raise ImproperlyConfigured(
                'No authentication credentials for "%(origin)s" with scheme '
                '"%(scheme)s". Either provide credentials within the file '
                'name or set credentials for (%(origin)s, %(scheme)s).' % {
                    'origin': origin,
                    'scheme': auth_scheme
                })