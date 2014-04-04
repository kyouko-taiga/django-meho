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

import json, logging, re
import fcntl, os, select, shlex, shutil, threading
import tempfile

from datetime import datetime
from django.core.cache import cache
from subprocess import Popen, PIPE
from meho.core.volumes import VolumeSelector, TemporaryVolumeDriver

logger = logging.getLogger('meho')

class FFmpeg(object):

    def transcode(self, media_in, media_out, encoder_string=''):
        """
        Transcodes ``media_in`` using ffmpeg with the profile specified by ``encoder_string``
        and saves the transcoded media to the private url of ``media_out``.

        This method is asynchronous and only returns the task identifier. Current progress status
        can be obtained with the tasks api.

        .. note:: Transcoding relies on both ``ffmpeg`` and ``ffprobe`` binaries; those should be
           available by the ``PATH`` variable.
        """
        # get file locators for input/output media
        selector   = VolumeSelector()
        volume_in  = selector.backend_for(selector.scheme(media_in.private_url))()
        volume_out = selector.backend_for(selector.scheme(media_out.private_url))()

        # retrieve an accessible absolute path to the input media
        try:
            input_file = volume_in.path(media_in.private_url)
        except NotImplementedError:
            with volume_in.open(media_in.private_url) as f:
                input_file = self._local_copy(f)

        # retrieve an accessible absolute path to the output media
        try:
            output_file = volume_out.path(media_out.private_url)
        except NotImplementedError:
            with volume_out.open(media_out.private_url) as f:
                output_file = self._local_copy(f)

        # start ffmpeg task
        return self._start_ffmpeg_task(input_file, output_file, encoder_string, media_out)

    def _start_ffmpeg_task(self, input_file, output_file, encoder_string, media_out):
        """Starts a new ffmpeg task; returns the pid of the spawned process.

        .. warning:: This method spawns a new thread when called, possibly ending up using all
           system resources in case of high load due to normal traffic or trivial DoS attack.

           Consider replacing the spawning of a new thread by a task queue manager.
        """
        # retrieves input media information
        input_info = parse_ffprobe(input_file)

        # generate ffmpeg command
        cmd = 'ffmpeg -y -i "%s" %s "%s"' % (input_file, encoder_string, output_file)

        # run ffmpeg in a new thread
        p = Popen(shlex.split(cmd), stderr=PIPE, close_fds=True, shell=False)
        t = threading.Thread(target=self._handle_ffmpeg_task, args=[p, input_info, media_out])
        t.setDaemon(True)
        t.start()

        logger.info('started ffmpeg job [%i]: %s' % (p.pid, cmd))
        return 'task_ffmpeg_{0}'.format(p.pid)

    def _handle_ffmpeg_task(self, ffmpeg_proc, input_info, media_out):
        """Handles the execution of a ffmpeg task.
        
        The logic of this function is mostly based on OSCIED (https://github.com/ebu/OSCIED) for
        parsing ffmpeg output and update encoding progress.
        """

        # frame= 2071 fps=  0 q=-1.0 size=   34623kB time=00:01:25.89 bitrate=3302.3kbits/s
        FFMPEG_REGEX = re.compile(
            r'frame=\s*(?P<frame>\d+)\s+fps=\s*(?P<fps>\d+)\s+q=\s*(?P<q>\S+)\s+\S*'
            r'size=\s*(?P<size>\S+)\s+time=\s*(?P<time>\S+)\s+bitrate=\s*(?P<bitrate>\S+)')

        # update transcoding status every 0.1 second(s)
        UPDATE_TIME_DELTA = 0.1

        cache.set('task_ffmpeg_{0}'.format(ffmpeg_proc.pid), {
            'eta': 0,
            'progress': 0
        })

        previous_time = start_time = datetime.now()
        input_duration = float(input_info['format']['duration'])

        # Add the O_NONBLOCK flag to stderr file descriptor.
        # http://stackoverflow.com/a/7730201/190597
        fcntl.fcntl(ffmpeg_proc.stderr, fcntl.F_SETFL,
            fcntl.fcntl(ffmpeg_proc.stderr, fcntl.F_GETFL) | os.O_NONBLOCK)

        while True:
            # wait for data to be available
            select.select([ffmpeg_proc.stderr], [], [])
            chunk = ffmpeg_proc.stderr.read()
            elapsed_time = datetime.now() - start_time

            # parse ffmpeg output to compute progress status
            match = FFMPEG_REGEX.match(chunk.decode('utf-8'))
            if match:
                output_info = match.groupdict()
                try:
                    ratio = total_seconds(output_info['time']) / float(input_duration)
                    ratio = 0.0 if ratio < 0.0 else 1.0 if ratio > 1.0 else ratio
                except ZeroDivisionError:
                    ratio = 1.0

                delta = (datetime.now() - previous_time).total_seconds()
                if delta >= UPDATE_TIME_DELTA:
                    previous_time = datetime.now()
                    try:
                        eta_time = int(elapsed_time.total_seconds() * (1.0 - ratio) / ratio)
                    except ZeroDivisionError:
                        eta_time = 0

                    # update process status
                    cache.set('task_ffmpeg_{0}'.format(ffmpeg_proc.pid), {
                        'eta': eta_time,
                        'progress' : ratio * 100
                    })

            # check for ffmpeg task termination
            if ffmpeg_proc.poll() is not None:
                break

        # call handler for ffmpeg task termination
        self._handle_ffmpeg_complete(ffmpeg_proc, media_out)

    def _handle_ffmpeg_complete(self, ffmpeg_proc, media_out):
        """
        Handles the termination of a ffmpeg task.
        """
        # update output media status
        status_code = ffmpeg_proc.poll()
        if status_code == 0:
            media_out.status = 'ready'
        else:
            media_out.status = 'failed'
        media_out.save()

        cache.set('task_ffmpeg_{0}'.format(ffmpeg_proc.pid), {
            'eta': 0,
            'progress' : 100
        })

        logger.info('ffmpeg job [%i] exited with status %i' % (ffmpeg_proc.pid, status_code))

    def _local_copy(self, content):
        """
        Saves ``content`` to a local temporary file and returns its name; ``content`` should be a
        proper python file-like object.
        """
        (fd, tmp_name) = tempfile.mkstemp()
        with open(fd, 'wb') as tmp_file:
            shutil.copyfileobj(content, tmp_file)
        return tmp_name    

def parse_ffprobe(filename):
    cmd = 'ffprobe -print_format json -show_format -show_streams "%s"' % filename
    p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, close_fds=True, shell=False)
    stdout, stderr = p.communicate()

    return json.loads(stdout.decode('utf-8'))

def total_seconds(time):
    hours, minutes, seconds = time.split(':')
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
