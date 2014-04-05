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

import argparse, json

from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener

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

            meho-manage api version <url>

                Prints the version of meho Rest API running on the remote
                server. ``url`` denotes the root url to the API endpoint, e.g.
                http://site.com/meho/api/

        meho media
        ~~~~~~~~~~

            meho-manage media list <url>
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
        parser.add_argument('url', help='root url to the API endpoint')
        args = parser.parse_args(args)

        # request API version on the meho server
        url = urljoin(self._format_url(args.url), 'version')
        request = Request(url, headers={'Content-Type': 'application/json'})
        opener = build_opener()
        response = opener.open(request)

        # parse the server response
        data = json.loads(response.read().decode('utf-8'))
        print('API version: %s' % data['version'])

    def _format_url(self, url):
        parts = urlsplit(url, 'http')
        if parts.netloc:
            netloc, path = parts.netloc, parts.path
        else:
            netloc = parts.path.split('/')[0]
            path = '/'.join(parts.path.split('/')[1:])
        return urlunsplit((parts.scheme, netloc, path, parts.query, parts.fragment))
            

if __name__ == '__main__':
    import sys
    meho_client = MehoClient()
    meho_client.main(*sys.argv)
