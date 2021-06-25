"""
Copyright (c) 2019, OptoFidelity OY

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    3. All advertising materials mentioning features or use of this software must display the following acknowledgement: This product includes software developed by the OptoFidelity OY.
    4. Neither the name of the OptoFidelity OY nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
# -*- coding: utf-8 -*-
import matplotlib
import matplotlib.pyplot as plt
from threading import Semaphore

import TPPTAnalysisSW.plotters as plotters
from TPPTAnalysisSW.utils import Timer

matplotlib.use('Agg')

# Used for mutual exclusion. Only one thread can use matplotlib as a time
plotSemaphore = Semaphore()

# Color constants
_PASS = '#00FF00'
_FAIL = '#FF0000'
_DEFAULT = 'r'

# Scatter plot marker size (in points)
_markersize = 40

# Z-orders for different elements
_zorder = {'pass': 3,
           'fail': 4,
           'edges': 1,  # Panel borders
           'lines': 2,
           }


# Decorator for easy locking
def synchronized(f):
    global plotSemaphore

    def locker(*args, **kwargs):
        with plotSemaphore:
            return f(*args, **kwargs)
    return locker


def waitForPlot():
    """Waits until there is no plot running.

    Does not hold the lock, so the next drawing may commence after waitForPlot() returns.
    """
    plotSemaphore.acquire()
    plotSemaphore.release()


@synchronized
def plot_swipes_on_target(imagepath, plotinfo, dutinfo, *args, **kwargs):
    """ Plots swipe diagram -  'target_points' of points (x,y) on target coordinates and
        'lines' that are tuple of (x,y) coordinates giving swipe start and end coordinates.
       alternatively, 'target_points' can be replaced by 'passed_points' and 'failed_points' """
    # Used by: hover, one finger swipe, non-stationary reporting rate
    t = Timer(3)

    if len(args) > 0 and args[0] == 'detailed':
        fig = plt.figure(num=2, dpi=100, figsize=(20,20))
    else:
        fig = plt.figure(num=1, dpi=100, figsize=(8,6))
    plt.clf()

    # Plot panel borders
    plt.axis('equal')
    plotters.plot_panel_borders(dutinfo.dimensions[0], dutinfo.dimensions[1],zorder=_zorder['edges'])
    plt.axis([-5.0, dutinfo.dimensions[0] + 5.0, dutinfo.dimensions[1] + 5.0, -5.0])

    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    # Plot arrows in the image
    for line in plotinfo['lines']:
        plt.arrow(line[0][0], line[0][1],
                    line[1][0] - line[0][0],
                    line[1][1] - line[0][1],
                    width=0.1, length_includes_head=True)

    t.Time("Arrows")

    # points
    if 'target_points' in plotinfo:
        x = [p[0] for p in plotinfo['target_points']]
        y = [p[1] for p in plotinfo['target_points']]
        plt.scatter(x, y, s=_markersize, c=_DEFAULT)
    else:
        x = [p[0] for p in plotinfo['passed_points']]
        y = [p[1] for p in plotinfo['passed_points']]
        plt.scatter(x, y, s=_markersize, c=_PASS, zorder=_zorder['pass'],edgecolors='k')
        x = [p[0] for p in plotinfo['failed_points']]
        y = [p[1] for p in plotinfo['failed_points']]
        plt.scatter(x, y, s=_markersize, c=_FAIL, zorder=_zorder['fail'],edgecolors='k')

    t.Time("Plots")

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')
    t.Time("Save")
