# Copyright 2018-2021 The glTF-Blender-IO authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# Imports
#

import time
import logging

#
# Globals
#

OUTPUT_LEVELS = ['ERROR', 'WARNING', 'INFO', 'PROFILE', 'DEBUG', 'VERBOSE']

g_current_output_level = 'DEBUG'
g_profile_started = False
g_profile_start = 0.0
g_profile_end = 0.0
g_profile_delta = 0.0

#
# Functions
#


def set_output_level(level):
    """Set an output debug level."""
    global g_current_output_level

    if OUTPUT_LEVELS.index(level) < 0:
        return

    g_current_output_level = level


def print_console(level, output):
    """Print to Blender console with a given header and output."""
    global OUTPUT_LEVELS
    global g_current_output_level

    if OUTPUT_LEVELS.index(level) > OUTPUT_LEVELS.index(g_current_output_level):
        return

    print(get_timestamp() + " | " + level + ': ' + output)


def print_newline():
    """Print a new line to Blender console."""
    print()


def get_timestamp():
    current_time = time.gmtime()
    return time.strftime("%H:%M:%S", current_time)


def print_timestamp(label=None):
    """Print a timestamp to Blender console."""
    output = 'Timestamp: ' + get_timestamp()

    if label is not None:
        output = output + ' (' + label + ')'

    print_console('PROFILE', output)


def profile_start():
    """Start profiling by storing the current time."""
    global g_profile_start
    global g_profile_started

    if g_profile_started:
        print_console('ERROR', 'Profiling already started')
        return

    g_profile_started = True

    g_profile_start = time.time()


def profile_end(label=None):
    """Stop profiling and printing out the delta time since profile start."""
    global g_profile_end
    global g_profile_delta
    global g_profile_started

    if not g_profile_started:
        print_console('ERROR', 'Profiling not started')
        return

    g_profile_started = False

    g_profile_end = time.time()
    g_profile_delta = g_profile_end - g_profile_start

    output = 'Delta time: ' + str(g_profile_delta)

    if label is not None:
        output = output + ' (' + label + ')'

    print_console('PROFILE', output)


# TODO: need to have a unique system for logging importer/exporter
# TODO: this logger is used for importer, but in io and in blender part, but is written here in a _io_ file
class Log:
    def __init__(self, loglevel):
        self.logger = logging.getLogger('glTFImporter')
        self.hdlr = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        self.hdlr.setFormatter(formatter)
        self.logger.addHandler(self.hdlr)
        self.logger.setLevel(int(loglevel))
