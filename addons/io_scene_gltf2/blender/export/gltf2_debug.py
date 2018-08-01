# Copyright (c) 2017 The Khronos Group Inc.
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

#
# Globals
#

g_profile_started = False
g_profile_start = 0.0
g_profile_end = 0.0
g_profile_delta = 0.0

g_output_levels = ['ERROR', 'WARNING', 'INFO', 'PROFILE', 'DEBUG', 'VERBOSE']
g_current_output_level = 'DEBUG'

#
# Functions
#

def set_output_level(level):
    """
    Allows to set an output debug level.
    """
    
    global g_current_output_level
    
    if g_output_levels.index(level) < 0:
        return
    
    g_current_output_level = level


def print_console(level,
                  output):
    """
    Prints to Blender console with a given header and output.
    """
    
    global g_output_levels
    global g_current_output_level
    
    if g_output_levels.index(level) > g_output_levels.index(g_current_output_level):
        return 
    
    print(level + ': ' + output)


def print_newline():
    """
    Prints a new line to Blender console.
    """
    print()


def print_timestamp(label = None):
    """
    Print a timestamp to Blender console.
    """
    output = 'Timestamp: ' + str(time.time())
    
    if label is not None:
        output = output + ' (' + label + ')'    
    
    print_console('PROFILE', output)
    

def profile_start():
    """
    Start profiling by storing the current time.
    """
    global g_profile_start
    global g_profile_started
    
    if g_profile_started:
        print_console('ERROR', 'Profiling already started')
        return
        
    g_profile_started = True
    
    g_profile_start = time.time()


def profile_end(label = None):
    """
    Stops profiling and printing out the delta time since profile start.
    """
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
