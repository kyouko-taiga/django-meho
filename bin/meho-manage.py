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

import sys
import argparse, json, re, requests
import getpass

from urllib.parse import urljoin, urlunsplit

__version__ = '0.1'

class MehoClient(object):

    def main(self, *args):
        """
        meho-manage is a command-line tool that exposes the meho Rest API to
        manage media transcoding and publishing.
        usage: meho-manage [-h] <category> <action> [<args>]

        The following describes the available categories and arguments.

        meho api
        ~~~~~~~~

            meho-manage api version <api>

                Prints the version of meho Rest API running on the remote
                server. ``api`` denotes the root url to the API endpoint, e.g.
                http://site.com/meho/api/

        meho media
        ~~~~~~~~~~

            meho-manage media list   [-u user] [-p password] [-f filter...]
                                     <api>

                Prints the ID of all stored media.

            meho-manage media detail [-u user] [-p [password]] <media_urn> <api>

                Prints the all information stored for a specific media.

            meho-manage media create [-u user] [-p [password]] [-i urn] [-t type]
                                     [-a parent] [-o] <private_url> <api>

                Create a new media and register it in the database.

                ``private_url`` should denote a meho-compatible url to the
                media source, e.g. file:///path/to/media. See the meho
                documentation for an exhaustive list of supported url scheme.

                The api will return a HTTP 400 error if you specify an ``urn``
                which is already being used by another media. Set --overwrite
                if you want to ignore this error and overwrite any existing
                media.

            meho-manage media update [-u user] [-p [password]] [-r private_url]
                                     [-t type] [-a parent] <urn> <api>

                Updates an existing media with the provided data.

                ``private_url`` should denote a meho-compatible url to the
                media source, e.g. file:///path/to/media. See the meho
                documentation for an exhaustive list of supported url scheme.

            meho-manage media delete [-u user] [-p [password]] <urn> <api>

                Deletes an existing media.
                

        """
        if len(args) > 1 and args[1] in ('-h', '--help'):
            print(self.main.__doc__)
            exit(0)

        try:
            category, action = args[1:3]
        except:
            print('unrecognized command: %s' % ' '.join(map(str, args[1:])))
            print('usage: meho-manage [-h] <category> <action> [<args>]')
            exit(-1)

        func_name = '%s_%s' % (category, action)
        if hasattr(self, func_name):
            try:
                return getattr(self, func_name)(*args[3:])
            except Exception as e:
                print(e)
        else:
            print('unrecognized command: %s' % ' '.join(map(str, args[1:])))
            print('usage: meho-manage [-h] <category> <action> [<args>]')
            exit(-1)

    def api_version(self, *args):
        # parse command line options
        parser = argparse.ArgumentParser(prog='meho-manage api version')
        parser.add_argument('api', help='root url to the API endpoint')
        args = parser.parse_args(args)

        # request API version on the meho server
        endpoint = urljoin(self._format_url(args.api), 'version')
        r = requests.get(endpoint)

        # parse the server response
        data = r.json()
        print('API version: %s' % data['version'])

    def media_list(self, *args):
        # parse command line options
        parser = argparse.ArgumentParser(prog='meho-manage media list')
        parser.add_argument('-u', '--user', help='username of your meho account')
        parser.add_argument('-p', '--password', help='password of your meho account')
        parser.add_argument('-f', '--filters', action='append', default=[],
            help='list of query filters')
        parser.add_argument('api', help='root url to the API endpoint')
        args = parser.parse_args(args)

        # request API for media list
        filters = {k:v for k,v in map(lambda f: f.split('='), args.filters)}
        auth = self._get_credentials(args)
        endpoint = self._format_url(args.api) + 'media/'
        r = requests.get(endpoint, auth=auth, params=filters)

        # parse the server response
        if r.status_code == 200:
            data = r.json()
            if data['media']:
                for media in data['media']:
                    print(media['urn'])
            else:
                print('No stored media')
        elif r.status_code == 401:
            self._handle_401(r)

    def media_detail(self, *args):
        # parse command line options
        parser = argparse.ArgumentParser(prog='meho-manage media detail')
        parser.add_argument('-u', '--user', help='username of your meho account')
        parser.add_argument('-p', '--password', help='password of your meho account')
        parser.add_argument('urn', help='urn of the media to be detailed')
        parser.add_argument('api', help='root url to the API endpoint')
        args = parser.parse_args(args)

        # request API for media detail
        auth = self._get_credentials(args)
        api_url = self._format_url(args.api)
        endpoint = '%(api)smedia/%(urn)s' % {'api': api_url, 'urn': args.urn}
        r = requests.get(endpoint, auth=auth)

        # parse the server response
        if r.status_code == 200:
            print(json.dumps(r.json(), indent=4, sort_keys=True))
        elif r.status_code == 401:
            self._handle_401(r)
        elif r.status_code == 404:
            self._handle_404(r)

    def media_create(self, *args):
        # parse command line options
        parser = argparse.ArgumentParser(prog='meho-manage media create')
        parser.add_argument('-u', '--user', help='username of your meho account')
        parser.add_argument('-p', '--password', help='password of your meho account')
        parser.add_argument('-i', '--urn', help='urn of the media (auto-generated by default)')
        parser.add_argument('-t', '--media_type', help='type of the media (guessed by default)')
        parser.add_argument('-a', '--parent', help='parent of the media')
        parser.add_argument('-o', '--overwrite', action='store_true', default=False,
            help='overwrite existing media')
        parser.add_argument('private_url', help='private url of the media')
        parser.add_argument('api', help='root url to the API endpoint')
        args = parser.parse_args(args)

        # get csrftoken
        api_url = self._format_url(args.api)
        session = requests.Session()
        csrftoken = self._get_csrf_token(session, api_url)

        # forge payload
        fields = ['urn', 'media_type', 'parent', 'private_url']
        payload = {'media': {f:getattr(args, f) for f in fields if getattr(args, f) is not None}}
        payload['overwrite'] = args.overwrite

        # request API for media creation
        endpoint = api_url + 'media'
        if args.urn:
            endpoint += '/' + args.urn
        auth = self._get_credentials(args)
        r = session.put(endpoint, auth=auth, data=json.dumps(payload),
            headers={'X-CSRFToken':csrftoken, 'content-type': 'application/json'})

        # parse the server response
        if r.status_code == 201:
            print(json.dumps(r.json(), indent=4, sort_keys=True))
        elif r.status_code == 401:
            self._handle_401(r)

    def media_update(self, *args):
        # parse command line options
        parser = argparse.ArgumentParser(prog='meho-manage media update')
        parser.add_argument('-u', '--user', help='username of your meho account')
        parser.add_argument('-p', '--password', help='password of your meho account')
        parser.add_argument('-r', '--private_url', help='private url of the media')
        parser.add_argument('-t', '--media_type', help='type of the media')
        parser.add_argument('-a', '--parent', help='parent of the media')
        parser.add_argument('urn', help='urn of the media to be updated')
        parser.add_argument('api', help='root url to the API endpoint')
        args = parser.parse_args(args)

        # get csrftoken
        api_url = self._format_url(args.api)
        session = requests.Session()
        csrftoken = self._get_csrf_token(session, api_url)

        # forge payload
        fields = ['media_type', 'parent', 'private_url']
        payload = {'media': {f:getattr(args, f) for f in fields if getattr(args, f) is not None}}

        # request API for media creation
        endpoint = api_url + 'media'
        if args.urn:
            endpoint += '/' + args.urn
        auth = self._get_credentials(args)
        r = session.post(endpoint, auth=auth, data=json.dumps(payload),
            headers={'X-CSRFToken':csrftoken, 'content-type': 'application/json'})

        # parse the server response
        if r.status_code == 200:
            print(json.dumps(r.json(), indent=4, sort_keys=True))
        elif r.status_code == 401:
            self._handle_401(r)
        elif r.status_code == 404:
            self._handle_404(r)

    def media_delete(self, *args):
        # parse command line options
        parser = argparse.ArgumentParser(prog='meho-manage media delete')
        parser.add_argument('-u', '--user', help='username of your meho account')
        parser.add_argument('-p', '--password', help='password of your meho account')
        parser.add_argument('urn', help='urn of the media to be updated')
        parser.add_argument('api', help='root url to the API endpoint')
        args = parser.parse_args(args)

        # get csrftoken
        api_url = self._format_url(args.api)
        session = requests.Session()
        csrftoken = self._get_csrf_token(session, api_url)

        # request API for media creation
        endpoint = api_url + 'media'
        if args.urn:
            endpoint += '/' + args.urn
        auth = self._get_credentials(args)
        r = session.delete(endpoint, auth=auth,
            headers={'X-CSRFToken':csrftoken, 'content-type': 'application/json'})

        # parse the server response
        if r.status_code == 204:
            print('\033[92mObject successfully deleted\033[0m')
        elif r.status_code == 401:
            self._handle_401(r)
        elif r.status_code == 404:
            self._handle_404(r)

    def _handle_401(self, response):
        print('\033[91mAuthentication failed\033[0m\n'
            '\tThe request could not be executed. Please check your credentials.\n'
            '\tServer reponse: %s' % response.text, file=sys.stderr)

    def _handle_404(self, response):
        print('\033[91mResource not found\033[0m', file=sys.stderr)

    def _get_csrf_token(self, session, api_url):
        endpoint = urljoin(self._format_url(api_url), 'version')
        r = session.get(endpoint)
        return r.cookies.get('csrftoken', None)

    def _format_url(self, url):
        """Completes missing parts of a user-privided and returns it."""
        exp = re.compile(r'^((?P<scheme>[a-z](?:[a-z\d\+\.-])*):\/\/)?'
            r'(?P<host>(?:[a-z\d\.-])*(?::[0-9]+)?)(?P<path>(?:\/[\w\.-]+\/?)*)'
            r'(?P<query>\?(?:\w+(?:=\w+)&?)*)?(?P<fragment>#\w*)?$')
        match = exp.match(url)
        if not match:
            raise ValueError('Invalid url: %s' % url)
        
        parts = match.groupdict('')
        parts['scheme'] = parts['scheme'] or 'http'
        return '%(scheme)s://%(host)s%(path)s%(query)s%(fragment)s' % parts

    def _get_credentials(self, args):
        if args.user:
            # if --user is set within the command line but --password is not,
            # we will ask the user to provide one on stdin
            pwd = args.password or getpass.getpass('Password:')
            return (args.user, pwd)
        return None

if __name__ == '__main__':
    import sys
    meho_client = MehoClient()
    meho_client.main(*sys.argv)
