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
from .measurementdb import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Ellipse, Rectangle
import TPPTAnalysisSW.measurementdb as measurementdb
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D

import TPPTAnalysisSW.plotters as plotters
from hashlib import md5
import random
import TPPTAnalysisSW.analyzers as analyzers
from .settings import settings
from threading import Semaphore
from datetime import datetime
from TPPTAnalysisSW.utils import Timer

# Used for mutual exclusion. Only one thread can use matplotlib as a time
plotSemaphore = Semaphore()

# Usage of matplotlib figure numbers
# 1 - Preview image (800 x 600)
# 2 - Detailed image (2000 x 2000)
# 3 - Large details image (800 x 800)
# 4 - Wide details image (1000 x 600)
# 5 - Narrow details image (600 x 600)
# 6 - Large details image (1000 x 800)

# Color constants
_PASS = '#00FF00'
_FAIL = '#FF0000'
_DEFAULT = 'r'
_STATIONARY_EDGE_PINCH = '#DFDF51'

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
    """ Waits until there is no plot running. Does not hold the lock, so the next drawing may commence after waitForPlot() returns"""
    plotSemaphore.acquire()
    plotSemaphore.release()

# Template for new image plotting functions:
#
#@synchronized
#def plot_xxx(imagepath, *args, **kwargs):
#    fig = plt.figure(1)
#    plt.clf()

#    drawing_code_here...

#    # Create the image
#    fig.savefig(imagepath)

@synchronized
def plot_dummy_image(imagepath, plotinfo, *args, **kwargs):
    """ Plots a dummy image for dummy test """

    t = Timer(3)

    fig = plt.figure(1)
    plt.clf()

    #plt.axis([-5.0, 5.0, 5.0, -5.0])
    x = [p[0] for p in plotinfo['points']]
    y = [p[1] for p in plotinfo['points']]
    plt.scatter(x, y, s=_markersize, c=_DEFAULT)
    t.Time("Plots")

    # Here we can use parameters
    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])
    plt.xlabel('X [mm]')
    plt.ylabel('Y [mm]')
    t.Time("Labels")

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')
    t.Time("Ready")

@synchronized
def plot_passfail_on_target(imagepath, plotinfo, dutinfo, *args, **kwargs):
    """ Plots passed and failed points on target.
        plotinfo argument must be a dictionary containing lists 'passed_points' and
        'failed_points' of points (x,y) on target coordinates """
    # Used by:

    s = Timer(3)
    fig = plt.figure(1)
    plt.clf()

    # Plot panel borders
    plt.axis('equal')
    plotters.plot_panel_borders(dutinfo.dimensions[0], dutinfo.dimensions[1],zorder=_zorder['edges'])
    plt.axis([-5.0, dutinfo.dimensions[0] + 5.0, dutinfo.dimensions[1] + 5.0, -5.0])
    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    # Passed points
    x = [p[0] for p in plotinfo['passed_points']]
    y = [p[1] for p in plotinfo['passed_points']]
    plt.scatter(x, y,  s=_markersize, c=_PASS, zorder=_zorder['pass'], edgecolors='k')
    # Failed points
    x = [p[0] for p in plotinfo['failed_points']]
    y = [p[1] for p in plotinfo['failed_points']]
    plt.scatter(x, y, s=_markersize, c=_FAIL, zorder=_zorder['fail'], edgecolors='k')

    s.Time("Plots")

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')
    s.Time("Save")

@synchronized
def plot_passfail_labels_on_target(imagepath, plotinfo, dutinfo, *args, **kwargs):
    """ Plots a graph with labelled points. Plotinfo contains 'passed_points' and
        'failed_points' arrays of tuples (x, y, s) where s is the label for a point """
    # Used by: first contact latency, stationary_reporting_rate, repeatability, stationary jitter
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

    # Passed points
    x = [p[0] for p in plotinfo['passed_points']]
    y = [p[1] for p in plotinfo['passed_points']]
    s = [str(p[2]) for p in plotinfo['passed_points']]
    plt.scatter(x, y, s=50, c=_PASS, zorder=_zorder['pass'])
    for (x, y, s) in zip(x, y, s):
        plt.annotate(s, (x,y), xytext=(5, 5), textcoords='offset points')
    # Failed points
    x = [p[0] for p in plotinfo['failed_points']]
    y = [p[1] for p in plotinfo['failed_points']]
    s = [str(p[2]) for p in plotinfo['failed_points']]
    plt.scatter(x, y, s=50, c=_FAIL, zorder=_zorder['fail'])
    for (x, y, s) in zip(x, y, s):
        plt.annotate(s, (x,y), xytext=(5, 5), textcoords='offset points')

    t.Time("Plots")

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')
    t.Time("Save")


@synchronized
def plot_tapping_passfail_labels_on_target(imagepath, plotinfo, dutinfo, *args, **kwargs):
    """ Plots a graph with labelled points. Plotinfo contains 'passed_points' and
        'failed_points' arrays of tuples (x, y, s) where s is the label for a point """
    # Used by: tapping repeatability
    t = Timer(3)
    if len(args) > 0 and args[0] == 'detailed':
        fig = plt.figure(num=2, dpi=100, figsize=(20, 20))
    else:
        fig = plt.figure(num=1, dpi=100, figsize=(8, 6))
    plt.clf()

    # Plot panel borders
    plt.axis('equal')
    plotters.plot_panel_borders(dutinfo.dimensions[0], dutinfo.dimensions[1], zorder=_zorder['edges'])
    plt.axis([-5.0, dutinfo.dimensions[0] + 5.0, dutinfo.dimensions[1] + 5.0, -5.0])
    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    # Plot edge area separator line
    border_width = float(plotinfo['border_width'])
    plt.plot([dutinfo.dimensions[0], 0], [border_width, border_width], color='blue',
             linestyle='dashed')
    plt.plot([border_width, border_width], [0, dutinfo.dimensions[1]], color='blue',
             linestyle='dashed')
    plt.plot([0, dutinfo.dimensions[0]],
             [dutinfo.dimensions[1] - border_width, dutinfo.dimensions[1] - border_width], color='blue',
             linestyle='dashed')
    plt.plot([dutinfo.dimensions[0] - border_width, dutinfo.dimensions[0] - border_width],
             [0, dutinfo.dimensions[1]], color='blue', linestyle='dashed')

    # Passed points
    x = [p[0] for p in plotinfo['passed_points']]
    y = [p[1] for p in plotinfo['passed_points']]
    s = [str(p[2]) for p in plotinfo['passed_points']]
    plt.scatter(x, y, s=50, c=_PASS, zorder=_zorder['pass'])
    for (x, y, s) in zip(x, y, s):
        plt.annotate(s, (x, y), xytext=(5, 5), textcoords='offset points')
    # Failed points
    x = [p[0] for p in plotinfo['failed_points']]
    y = [p[1] for p in plotinfo['failed_points']]
    s = [str(p[2]) for p in plotinfo['failed_points']]
    plt.scatter(x, y, s=50, c=_FAIL, zorder=_zorder['fail'])
    for (x, y, s) in zip(x, y, s):
        plt.annotate(s, (x, y), xytext=(5, 5), textcoords='offset points')

    t.Time("Plots")

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')
    t.Time("Save")


@synchronized
def plot_passfail_labels(imagepath, plotinfo, *args, **kwargs):
    """ Plots a graph with labelled points. Plotinfo contains 'passed_points' and
        'failed_points' arrays of tuples (x, y, s) where s is the label for a point.
       An optional 'center' point in plotinfo gives the center of the graph """
    # Used by: stationary_jitter
    t = Timer(3)
    fig = plt.figure(1)
    plt.clf()

    # Plot panel borders
    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    # Passed points
    x = [p[0] for p in plotinfo['passed_points']]
    y = [p[1] for p in plotinfo['passed_points']]
    s = [str(p[2]) for p in plotinfo['passed_points']]
    plt.scatter(x, y, s=50, c=_PASS, zorder=_zorder['pass'])
    for (x, y, s) in zip(x, y, s):
        plt.annotate(s, (x,y), xytext=(5, 5), textcoords='offset points')
    # Failed points
    x = [p[0] for p in plotinfo['failed_points']]
    y = [p[1] for p in plotinfo['failed_points']]
    s = [str(p[2]) for p in plotinfo['failed_points']]
    plt.scatter(x, y, s=50, c=_FAIL, zorder=_zorder['fail'])
    for (x, y, s) in zip(x, y, s):
        plt.annotate(s, (x,y), xytext=(5, 5), textcoords='offset points')

    robot_x = plotinfo['robot_point'][0].robot_x
    robot_y = plotinfo['robot_point'][0].robot_y
    robot_point = [(robot_x, robot_y),]

    plt.scatter(robot_x, robot_y, s=50, c="k")
    plt.annotate("Reference", (robot_x, robot_y), xytext=(30, 10), textcoords='offset points', color='k',
                    arrowprops=dict(arrowstyle="simple", fc="k", ec="none",
                                    connectionstyle="arc3,rad=0.3"))
    # Set axis
    passed_range = plotters.get_range(plotinfo['passed_points'] + plotinfo['failed_points'] + robot_point)
    if 'center' in plotinfo:
        center = plotinfo['center']
        x_width = max(center[0] - passed_range[0], passed_range[2] - center[0])
        y_width = max(center[1] - passed_range[1], passed_range[3] - center[1])
        plt.axis([center[0] - x_width - 0.5, center[0] + x_width + 0.5, center[1] + y_width + 0.5, center[1] - y_width - 0.5])
    elif passed_range is None:
        # Empty lists
        plt.axis([-5.0, 5.0, 5.0, -5.0])
    else:
        # This might result in non-equal axis...
        plt.axis([passed_range[0] - 0.5, passed_range[2] + 0.5, passed_range[3] + 0.5, passed_range[1] - 0.5])

    t.Time("Plots")

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')
    t.Time("Save")

@synchronized
def plot_repeatability_details(imagepath, plotinfo, *args, **kwargs):
    """ Plots repeatability diagram: a diagram of points and a circle with center at the
        average value of point coordinates. Points are in arrays 'passed_points', 'failed_points',
        'average_point' and 'robot_point' (the coordinates to which the robot has pressed) """
    # Used by: repeatability

    t = Timer(3)
    t.Time("START")

    fig = plt.figure(5, figsize=(6,6), dpi=100)
    plt.clf()

    plt.axis('equal')
    plt.xlabel('X [mm]')
    plt.ylabel('Y [mm]')

    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    # Plot individual measurements
    x = [p[0] for p in plotinfo['passed_points']]
    y = [p[1] for p in plotinfo['passed_points']]
    s = [20 if n == 1 else 50 for n in plotinfo['passed_points_count']]
    plt.scatter(x, y, s=s, c=_PASS, zorder=_zorder['pass'],edgecolors='k')
    for (x, y, s) in zip(x, y, plotinfo['passed_points_count']):
        if s > 1:
            plt.annotate(str(s), (x,y), xytext=(5, 5), textcoords='offset points')

    x = [p[0] for p in plotinfo['failed_points']]
    y = [p[1] for p in plotinfo['failed_points']]
    s = [20 if n == 1 else 50 for n in plotinfo['failed_points_count']]
    plt.scatter(x, y, s=s, c=_FAIL, zorder=_zorder['fail'])
    for (x, y, s) in zip(x, y, plotinfo['failed_points_count']):
        if s > 1:
            plt.annotate(str(s), (x,y), xytext=(5, 5), textcoords='offset points')

    # Plot robot point
    robot_x = plotinfo['robot_point'][0]
    robot_y = plotinfo['robot_point'][1]
    plt.scatter(robot_x, robot_y, s=50, c="k")
    plt.annotate("Reference", (robot_x,robot_y), xytext=(30, 10), textcoords='offset points', color='k',
                    arrowprops=dict(arrowstyle="simple", fc="k", ec="none",
                                    connectionstyle="arc3,rad=0.3"))

    # Plot error square
    if 'reference_point' in plotinfo:
        rx, ry = plotinfo['reference_point']
        d = float(plotinfo['distance'])
        # Draw a square
        x = [rx, rx + d, rx + d, rx, rx]
        y = [ry, ry, ry + d, ry + d, ry]
        plt.plot(x, y, "k")

    # Reverse y scale
    ax = plt.gca()
    ax.set_ylim(ax.get_ylim()[::-1])

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')
    t.Time("END")


@synchronized
def plot_tapping_repeatability_details(imagepath, plotinfo, *args, **kwargs):
    """ Plots tapping repeatability diagram: a diagram of points and a circle with center at the
        average value of point coordinates. Points are in arrays 'passed_points', 'failed_points',
        'average_point' and 'robot_point' (the coordinates to which the robot has pressed) """
    # Used by: tapping repeatability

    t = Timer(3)
    t.Time("START")

    fig = plt.figure(5, figsize=(6, 6), dpi=100)
    plt.clf()

    plt.axis('equal')
    plt.xlabel('X [mm]')
    plt.ylabel('Y [mm]')

    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    # Plot individual measurements
    x = [p[0] for p in plotinfo['passed_points']]
    y = [p[1] for p in plotinfo['passed_points']]
    s = [20 if n == 1 else 50 for n in plotinfo['passed_points_count']]
    plt.scatter(x, y, s=s, c=_PASS, zorder=_zorder['pass'], edgecolors='k')
    for (x, y, s) in zip(x, y, plotinfo['passed_points_count']):
        if s > 1:
            plt.annotate(str(s), (x, y), xytext=(5, 5), textcoords='offset points')

    x = [p[0] for p in plotinfo['failed_points']]
    y = [p[1] for p in plotinfo['failed_points']]
    s = [20 if n == 1 else 50 for n in plotinfo['failed_points_count']]
    plt.scatter(x, y, s=s, c=_FAIL, zorder=_zorder['fail'])
    for (x, y, s) in zip(x, y, plotinfo['failed_points_count']):
        if s > 1:
            plt.annotate(str(s), (x, y), xytext=(5, 5), textcoords='offset points')

    # Plot reference point
    reference_x = plotinfo['reference_point'][0]
    reference_y = plotinfo['reference_point'][1]
    plt.scatter(reference_x, reference_y, s=50, c="k")
    plt.annotate("Reference point", (reference_x, reference_y), xytext=(30, 10), textcoords='offset points', color='k',
                 arrowprops=dict(arrowstyle="simple", fc="k", ec="none",
                                 connectionstyle="arc3,rad=0.3"))

    # Plot max error circle
    d = float(plotinfo['error_radius'])
    circle = plt.Circle((reference_x, reference_y), d, fill=False, linestyle='--', color='r')

    ax = plt.gca()
    # Reverse y scale
    ax.set_ylim(ax.get_ylim()[::-1])
    ax.add_artist(circle)

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')
    t.Time("END")


@synchronized
def plot_swipes_on_target_with_labels(imagepath, plotinfo, dutinfo, *args, **kwargs):
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
    for line_id, line in zip(plotinfo['swipe_ids'], plotinfo['lines']):
        plt.arrow(line[0][0], line[0][1],
                    line[1][0] - line[0][0],
                    line[1][1] - line[0][1],
                    width=0.1, length_includes_head=True)
        plt.annotate("Line ID " + str(line_id), (line[0][0], line[0][1]), xytext=(25, 5), textcoords='offset points', color='k',
                            arrowprops=dict(arrowstyle="simple", fc="k", ec="none",
                                            connectionstyle="arc3,rad=0.3"))

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

@synchronized
def plot_jitter_diagram(imagepath, plotinfo, dutinfo, **kwargs):
    """ Plots jitter diagram - two subplots with target and swipe information
        plotinfo argument must be a dictionary containing lists 'target_points'
        and 'swipe_points' of points (x,y) on target coordinates """
    # Used by: hover, one finger swipe

    s = Timer(3)
    fig = plt.figure(num=4, dpi=100, figsize=(10,6))
    plt.clf()

    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    # Plot panel borders
    plt.subplot(121)
    plot_one_finger_swipe_on_target(plotinfo, dutinfo)

    # Swipe
    plt.subplot(122)
    plot_one_finger_swipe_offset_jitter(plotinfo)

    s.Time("Plots")

    # Create the image
    fig.savefig(imagepath, bbox_inches="tight")
    plt.close('all')
    s.Time("Save")

@synchronized
def plot_linearity_details(imagepath, plotinfo, dutinfo, *args, **kwargs):
    """
        Plots linearity subplots for single line.

        Requires:
            swipe_points (tuples of (traveled_distance, offset))
            linear_error (linear errors from least squares fit to reported coordinates)
            offset_error (offset errors from least squares fit to robot line)

    """

    s = Timer(3)
    fig = plt.figure(num=4, dpi=100, figsize=(12, 8))
    plt.clf()

    x = [p[0] for p in plotinfo['swipe_points']]

    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    gs = gridspec.GridSpec(3, 1, height_ratios=[1, 1, 2])

    # Plot panel borders
    ax = plt.subplot(gs[0])
    plt.xlabel('Distance traveled [mm]')
    plt.ylabel('Linearity error [mm]')

    plt.plot(x, plotinfo['linearity']['linear_error'], color='b')
    plt.vlines(x, 0.0, plotinfo['linearity']['linear_error'], alpha=0.5)

    # Swipe
    plt.subplot(gs[1])
    plt.xlabel('Distance traveled [mm]')
    plt.ylabel('Offset error [mm]')

    plt.plot(x, plotinfo['linearity']['offset_error'], color='b')
    plt.vlines(x, 0.0, plotinfo['linearity']['offset_error'], alpha=0.5)

    plt.subplot(gs[2])
    plt.axis('equal')
    plt.xlabel('X [mm]')
    plt.ylabel('Y [mm]')

    plotters.plot_panel_borders(dutinfo.dimensions[0],
                                dutinfo.dimensions[1],
                                zorder=_zorder['edges'])

    plt.axis([-5.0, dutinfo.dimensions[0] + 5.0,
             dutinfo.dimensions[1] + 5.0, -5.0])

    x = [p[0] for p in plotinfo['passed_points']]
    y = [p[1] for p in plotinfo['passed_points']]
    plt.scatter(x, y, s=_markersize, c=_PASS, zorder=_zorder['pass'], edgecolors='black')

    x = [p[0] for p in plotinfo['failed_points']]
    y = [p[1] for p in plotinfo['failed_points']]
    plt.scatter(x, y, s=_markersize, c=_FAIL, zorder=_zorder['fail'], edgecolors='black')

    s.Time("Plots")

    plt.tight_layout(h_pad=0.3)
    plt.subplots_adjust(top=0.95)

    # Create the image
    fig.savefig(imagepath, bbox_inches="tight")
    plt.close('all')
    s.Time("Save")

@synchronized
def plot_linearity_detailed_histograms(imagepath, plotinfo, dutinfo, *args, **kwargs):

    if len(args) > 0 and args[0] == 'detailed':
        fig = plt.figure(num=2, dpi=100, figsize=(15, 13))
    else:
        fig = plt.figure(num=1, dpi=100, figsize=(14, 8))

    if 'title' in kwargs:
        fig.suptitle(kwargs['title'])

    prefix = ''
    if 'exclude_edges' in kwargs:
        if kwargs['exclude_edges']:
            prefix = 'center_'


    columns = (
        ('horizontal', 'Horizontal'),
        ('vertical', 'Vertical'),
        ('diagonal', 'Diagonal'),
        ('all', 'Overall'))

    for column, (column_id, column_name) in enumerate(columns):

        ax = fig.add_subplot(3, 4, column + 1)

        hist, bins = np.histogram(plotinfo[column_id][prefix + 'linearity_errors'], bins='auto')
        width = 0.7 * (bins[1] - bins[0])
        center = (bins[:-1] + bins[1:]) / 2

        ax.bar(center, hist, align='center', width=width)
        ax.set_ylabel('Count')
        ax.set_xlabel('{} Linearity [mm]'.format(column_name))
        skip = int(math.ceil(len(center) / 8.0))
        ax.set_xticks(center[::skip])
        plt.setp(ax.get_xticklabels(), rotation=30, horizontalalignment='right')

        ax = fig.add_subplot(3, 4, column + 5)

        hist, bins = np.histogram(plotinfo[column_id][prefix + 'jitters'], bins='auto')
        width = 0.7 * (bins[1] - bins[0])
        center = (bins[:-1] + bins[1:]) / 2

        ax.bar(center, hist, align='center', width=width)
        ax.set_ylabel('Count')
        ax.set_xlabel('{} Jitter [mm]'.format(column_name))
        skip = int(math.ceil(len(center) / 8.0))
        ax.set_xticks(center[::skip])
        plt.setp(ax.get_xticklabels(), rotation=30, horizontalalignment='right')

        ax = fig.add_subplot(3, 4, column + 9)

        hist, bins = np.histogram(plotinfo[column_id][prefix + 'offset_errors'], bins='auto')
        width = 0.7 * (bins[1] - bins[0])
        center = (bins[:-1] + bins[1:]) / 2

        ax.bar(center, hist, align='center', width=width)
        ax.set_ylabel('Count')
        ax.set_xlabel('{} Offset [mm]'.format(column_name))
        skip = int(math.ceil(len(center) / 8.0))
        ax.set_xticks(center[::skip])
        plt.xticks()
        plt.setp(ax.get_xticklabels(), rotation=30, horizontalalignment='right')

    fig.tight_layout()
    fig.subplots_adjust(top=0.9)
    fig.savefig(imagepath)
    plt.close(fig)

def plot_one_finger_swipe_on_target(plotinfo, dutinfo):
    """ Plots one swipe on panel. See plot_jitter_diagram() for parameters.
        This is used in normal one finger swipe and in angle swipe.
    """

    plt.axis('equal')
    plt.xlabel('X [mm]')
    plt.ylabel('Y [mm]')

    plotters.plot_panel_borders(dutinfo.dimensions[0],
                                dutinfo.dimensions[1],
                                zorder=_zorder['edges'])

    plt.axis([-5.0, dutinfo.dimensions[0] + 5.0,
             dutinfo.dimensions[1] + 5.0, -5.0])

    # Target
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

    if 'line_start' in plotinfo:
        plt.arrow(plotinfo['line_start'][0], plotinfo['line_start'][1],
                  plotinfo['line_end'][0] - plotinfo['line_start'][0],
                  plotinfo['line_end'][1] - plotinfo['line_start'][1],
                  width=0.1, length_includes_head=True)


def plot_one_finger_swipe_offset_jitter(plotinfo):
    """ Plots single swipe offset/jitter graph.
        See plot_jitter_diagram() for parameters.
        This is used in normal one finger swipe and in angle swipe.
    """

    plt.xlabel('distance traveled [mm]')

    x = [p[0] for p in plotinfo['swipe_points']]
    y = [p[1] for p in plotinfo['swipe_points']]

    #plt.plot(x, y, "o-", color='k', mec='k', mfc='r')
    plt.plot(x, y, color='b')
    plt.vlines(x, 0.0, y, alpha=0.5)
    plt.plot(x, plotinfo['jitters'], color=_DEFAULT)
    plt.legend(("offset", "jitter"),
               bbox_to_anchor=(1.05, 1),
               loc=2,
               borderaxespad=0)

@synchronized
def plot_one_finger_swipe_with_linear_fit(imagepath, plotinfo, dutinfo, **kwargs):
    """ Plots linear fit diagram - two subplots with target and swipe information
        plotinfo argument must be a dictionary containing lists 'target_points'
        and 'swipe_points' of points (x,y) on target coordinates """
    # Used by: one finger swipe

    s = Timer(3)
    fig = plt.figure(num=1, dpi=100, figsize=(10,11))
    plt.clf()

    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    # Plot points on regression line
    plt.subplot2grid((4,2), (0,0), colspan=2, rowspan=1).set_title('Points on regression line')
    plot_one_finger_swipe_with_linear_fit_on_target(plotinfo)

    # Deviation from linear fit
    plt.subplot2grid((4,2), (1,0), colspan=2, rowspan=1).set_title('Linear fit error calculated from regression line')
    plot_one_finger_deviation_from_linear_fit(plotinfo)

    # Plot panel borders
    plt.subplot2grid((4,2), (2,0), colspan=1, rowspan=2).set_title('Points on robot drawn line')
    plot_one_finger_swipe_on_target(plotinfo, dutinfo)

    # Swipe
    plt.subplot2grid((4,2), (2,1), colspan=1, rowspan=2).set_title('Jitter with a sliding window')
    plot_one_finger_swipe_offset_jitter(plotinfo)

    fig.subplots_adjust(hspace=0.7)

    s.Time("Plots")

    # Create the image
    fig.savefig(imagepath, bbox_inches="tight")
    plt.close('all')
    s.Time("Save")

def plot_one_finger_swipe_with_linear_fit_on_target(plotinfo):
    """ Plots one swipe on panel. See plot_jitter_diagram() for parameters.
        This is used in normal one finger swipe and in angle swipe.
    """

    plt.xlabel('X [mm]')
    plt.ylabel('Y [mm]')

    x = [p[0] for p in plotinfo['swipe_points']]
    y = [p[1] for p in plotinfo['swipe_points']]

    plt.scatter(x, y, s=_markersize, c=_PASS, zorder=_zorder['pass'],edgecolors='k')

    if len(plotinfo['swipe_points']) > 0:
        plt.axis([-0.2 + min(x), max(x) + 0.2,
                 max(y) + 0.2, min(y) - 0.2])
        fit = np.polyfit(x, y, 1)
        fit_fn = np.poly1d(fit)
        plt.plot(x, fit_fn(x), 'r', zorder=10)
    else:
        plt.plot([], [], 'r', zorder=10)

def plot_one_finger_deviation_from_linear_fit(plotinfo):
    """ Plots single swipe deviation from linear fit graph.
        This is used in one finger swipe and in angle swipe.
    """

    plt.xlabel('distance traveled [mm]')

    x = [p[0] for p in plotinfo['swipe_points']]
    y = plotinfo['linear_error']

    if len(plotinfo['swipe_points']) > 0:
        plt.axis([-5.0 + min(x), max(x) + 5.0,
                 0.0, max(y) + max(y) / 4])

    linear_error, = plt.plot(x, y, color=_DEFAULT)

    # Create a blank rectangle for adding additional info to legend
    blank = Rectangle((0, 0), 1, 1, fc="w", fill=False, edgecolor='none', linewidth=0)
    max_err = round(plotinfo['lin_error_max'], 2)
    avg_err = round(plotinfo['lin_error_avg'], 2)
    rms_err = round(plotinfo['lin_error_rms'], 2)

    plt.legend([linear_error, blank, blank, blank],
               ("Linear fit error", "Max: %s" % max_err, "Avg: %s" % avg_err, "Rms: %s" % rms_err),
               bbox_to_anchor=(1.02, 1),
               loc=2,
               borderaxespad=0,
               fontsize=11)

@synchronized
def plot_reporting_rate(imagepath, plotinfo, **kwargs):
    """ Plots reporting rate diagram. plotinfo argument must be a dictionary containing
        'delays': list of delays, and 'passed' & 'failed' of tuples (0-based index, delay).
       If there is max_delay in plotinfo, it is used to scale the axis """
    # Used by: non-stationary reporting rate, stationary reporting rate

    s = Timer(3)
    fig = plt.figure(num=4, dpi=100, figsize=(10,6))
    plt.clf()

    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    # Delays
    x = range(1, len(plotinfo['delays']) + 1)
    plt.plot(x,plotinfo['delays'], "-", color='k')

    x = [(p[0]+1) for p in plotinfo['passed']]
    y = [p[1] for p in plotinfo['passed']]
    plt.scatter(x, y, s=_markersize, c=_PASS, zorder=_zorder['pass'],edgecolors='k')
    x = [(p[0]+1) for p in plotinfo['failed']]
    y = [p[1] for p in plotinfo['failed']]
    plt.scatter(x, y, s=_markersize, c=_FAIL, zorder=_zorder['fail'],edgecolors='k')

    plt.xlim(0, len(plotinfo['delays']) + 2)
    if 'max_delay' in plotinfo and plotinfo['max_delay'] is not None:
        plt.ylim(0, plotinfo['max_delay'] * 1.1)

    if 'max_allowed_delay' in plotinfo:
        plt.plot([0, len(plotinfo['delays']) + 2], [plotinfo['max_allowed_delay']] * 2, c=_FAIL)

    plt.ylabel("Delay [ms]")
    plt.xlabel("Point index")

    s.Time("Plots")

    # Create the image
    fig.savefig(imagepath, bbox_inches="tight")
    plt.close('all')
    s.Time("Save")

@synchronized
def plot_taptest_on_target(imagepath, plotinfo, dutinfo, *args, **kwargs):
    """ Plots one finger tap targets and points. Requires 'target-points',
        'passed_points', and 'failed_points', last two are tuples of (x,y) tuples:
        (target, actual_hit). If args[0] is 'detailed', a
        more accurate version is plotted"""

    s = Timer(3)

    if len(args) > 0 and args[0] == 'detailed':
        fig = plt.figure(num=2, dpi=100, figsize=(20,20))
    else:
        fig = plt.figure(num=1, dpi=100, figsize=(8,6))
    plt.clf()

    plt.axis('equal')
    plt.axis([-5.0, dutinfo.dimensions[0] + 5.0, dutinfo.dimensions[1] + 5.0, -5.0])
    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])
    else:
        plt.suptitle('Overview plot')
    plt.xlabel('X [mm]')
    plt.ylabel('Y [mm]')
    plotters.plot_panel_borders(dutinfo.dimensions[0], dutinfo.dimensions[1],zorder=_zorder['edges'])
    s.Time("Borders")

    # plot targets
    cx = np.cos(np.linspace(0,np.pi*2, num=32))
    cy = np.sin(np.linspace(0,np.pi*2, num=32))
    x = []
    y = []
    for p in plotinfo['hits']:
        x.extend([p[0][0] + float(p[1])*c for c in cx])
        y.extend([p[0][1] + float(p[1])*c for c in cy])
        x.append(None)
        y.append(None)
    plt.plot(x, y, color="#000000")
    x = []
    y = []
    for p in plotinfo['missing']:
        x.extend([p[0][0] + float(p[1])*c for c in cx])
        y.extend([p[0][1] + float(p[1])*c for c in cy])
        x.append(None)
        y.append(None)
    plt.plot(x, y, color=_FAIL, zorder=_zorder['lines'])
    s.Time("Targets")

    # Passed points
    lines_x = []
    lines_y = []
    for p in plotinfo['passed_points']:
        lines_x.extend((p[0][0], p[1][0], None))
        lines_y.extend((p[0][1], p[1][1], None))
    px = [p[1][0] for p in plotinfo['passed_points']]
    py = [p[1][1] for p in plotinfo['passed_points']]
    plt.plot(lines_x, lines_y, color=_PASS, zorder=_zorder['lines'])
    plt.scatter(px, py, s=_markersize, c=_PASS, zorder=_zorder['pass'],edgecolors='k')
    s.Time("Plots")

    # Failed points
    lines_x = []
    lines_y = []
    for p in plotinfo['failed_points']:
        lines_x.extend((p[0][0], p[1][0], None))
        lines_y.extend((p[0][1], p[1][1], None))
    px = [p[1][0] for p in plotinfo['failed_points']]
    py = [p[1][1] for p in plotinfo['failed_points']]
    plt.plot(lines_x, lines_y, color=_FAIL, zorder=_zorder['lines'])
    plt.scatter(px, py, s=_markersize, c=_FAIL, zorder=_zorder['fail'],edgecolors='k')

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')
    s.Time("Save")


@synchronized
def plot_dxdy_graph(imagepath, plotinfo, limited, *args, **kwargs):
    """ Plots dx-dy graph with two histograms. If args[0] is 'detailed', a
        more accurate version is plotted. The plotinfo parameter is a dectionary,
        which contains passed_points (tuple (target_point, hit)), failed points
        and 'maxposerror'. If edge are plot is to be printed, the 'maxposerror' is
        replaced by 'edgepositioningerror' """
    #used by: one finger tap
    s = Timer(3)

    if len(args) > 0 and args[0] == 'detailed':
        fig = plt.figure(num=2, dpi=100, figsize=(20,20))
    else:
        fig = plt.figure(num=1, dpi=100, figsize=(8,6))

    plt.clf()

    # setup subpolots
    plt.axis('equal')
    gs = gridspec.GridSpec(2, 2, width_ratios = [3, 1], height_ratios = [3, 1])
    ax = plt.subplot(gs[0])

    # Axis labels
    plt.xlabel('linearity error X [mm]')
    plt.ylabel('linearity error Y [mm]')
    ax.grid(True)
    ax.axhline(color="#000000")
    ax.axvline(color="#000000")

    # Draw acceptance circle
    if 'edge_only' not in kwargs:
        radius = float(plotinfo['maxposerror'])
        x = radius*np.cos(np.linspace(0,np.pi*2))
        y = radius*np.sin(np.linspace(0,np.pi*2))
        plt.plot(x, y, "k")

    if 'edgepositioningerror' in plotinfo and 'center_only' not in kwargs:
        # Draw second acceptance limit to the edge areas
        radius = float(plotinfo['edgepositioningerror'])
        x = radius*np.cos(np.linspace(0,np.pi*2))
        y = radius*np.sin(np.linspace(0,np.pi*2))
        plt.plot(x, y, "k")

    if limited:
        ax.set_xlim(-radius, radius)
        ax.set_ylim(-radius, radius)
        ax.set_aspect('equal')
        if 'center_only' in kwargs:
            plt.title('Center input error scatter plot (limited area)')
        elif 'edge_only' in kwargs:
            plt.title('Edge input error scatter plot (limited area)')
        else:
            plt.title('Input error scatter plot (limited area)')
    else:
        ax.set_aspect('equal')
        plt.title('Input error scatter plot')

    passed_points_x = [(p[1][0] - p[0][0]) for p in plotinfo['passed_points']]
    passed_points_y = [(p[1][1] - p[0][1]) for p in plotinfo['passed_points']]
    failed_points_x = [(p[1][0] - p[0][0]) for p in plotinfo['failed_points']]
    failed_points_y = [(p[1][1] - p[0][1]) for p in plotinfo['failed_points']]
    ax.scatter(passed_points_x, passed_points_y, s=_markersize, c=_PASS, zorder=_zorder['pass'],edgecolors='k')
    ax.scatter(failed_points_x, failed_points_y, s=_markersize, c=_FAIL, zorder=_zorder['fail'],edgecolors='k')

    # Set yaxis location and tick location
    ax.yaxis.tick_right()
    ax.set_ylim(ax.get_ylim()[::-1])



    # plot histograms
    ax1 = plt.subplot(gs[1], sharey=ax)
    # Set histogram bins according to the ticks in the axis
    bins = ax1.get_yticks()
    bins = plotters.split_bins(bins, 3)
    plt.setp(ax1.get_yticklabels(), visible=False)
    #ax1.set_xticklabels([])
    plt.hist([passed_points_y, failed_points_y], bins=bins, orientation='horizontal', color=[_PASS, _FAIL], stacked=True, edgecolor='k')
    labels = [int(l) for l in ax1.get_xticks()]
    for i in range(1, len(labels) - 1):
        labels[i] = ''
    ax1.set_xticklabels(labels)

    ax2 = plt.subplot(gs[2], sharex=ax)
    #ax2.set_yticklabels([])
    #ax2.yaxis.tick_right()
    plt.setp(ax2.get_xticklabels(), visible=False)
    bins = ax2.get_xticks()
    bins = plotters.split_bins(bins, 3)
    plt.hist([passed_points_x, failed_points_x], bins=bins, orientation='vertical', color=[_PASS, _FAIL], stacked=True, edgecolor='k')
    ax2.set_ylim(ax2.get_ylim()[::-1])
    labels = [int(l) for l in ax2.get_yticks()]
    for i in range(1, len(labels) - 1):
        labels[i] = ''
    ax2.set_yticklabels(labels)

    if limited:
        ax.set_xlim(-radius, radius)
        ax.set_ylim(radius, -radius)
        ax.set_aspect('equal')

    # Create the image
    plt.tight_layout()
    fig.savefig(imagepath)
    plt.close('all')
    s.Time("Save")

@synchronized
def plot_p2p_err_histogram(imagepath, plotinfo, limited, *args, **kwargs):
    if len(args) > 0 and args[0] == 'detailed':
        fig = plt.figure(num=2, dpi=100, figsize=(20,20))
    else:
        fig = plt.figure(num=1, dpi=100, figsize=(8,6))

    acc_errors = plotinfo['distances']

    num_bins = 30
    plt.hist(acc_errors, bins=num_bins, color='gray', stacked=True, edgecolor='k')
    plt.xlabel('Accuracy [mm]')
    plt.ylabel('Frequency')
    plt.title('Input Error Histogram')


    sorted_acc_errors = np.sort(acc_errors)
    index_85_0 = round(0.85*len(acc_errors)) - 1
    limit_85_0 = sorted_acc_errors[index_85_0]
    index_99_7 = round(0.997*len(acc_errors)) - 1
    limit_99_7 = sorted_acc_errors[index_99_7]

    line_85 = plt.axvline(x=limit_85_0, linewidth=2, color='g')
    line_997 = plt.axvline(x=limit_99_7, linewidth=2, color='r')

    # Create a blank rectangle for adding additional info to legend
    blank = Rectangle((0, 0), 1, 1, fc="w", fill=False, edgecolor='none', linewidth=0)

    legend = plt.legend([line_85, line_997, blank, blank], (u"85 % = " + str(limit_85_0) + u" mm",
                         u"99.7 % = " + str(limit_99_7) + u" mm",
                         "Mean: %s mm" % round(np.mean(acc_errors), 2),
                         "Std: %s mm" % round(np.std(acc_errors), 2)), fontsize=11)
    # Create the image
    plt.tight_layout()
    fig.savefig(imagepath)
    plt.close('all')

@synchronized
def plot_multifinger_p2p(imagepath, plotinfo, dutinfo, *args, **kwargs):
    """ Plots multifinger tap test detailed overview plot.
        plotinfo argument is the result array from multifinger analysis """
    # Used by:

    s = Timer(3)
    fig = plt.figure(1)
    plt.clf()

    # Plot panel borders
    plt.axis('equal')
    plotters.plot_panel_borders(dutinfo.dimensions[0], dutinfo.dimensions[1],zorder=_zorder['edges'])
    plt.axis([-5.0, dutinfo.dimensions[0] + 5.0, dutinfo.dimensions[1] + 5.0, -5.0])
    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    lines = []
    passed_fingers = []
    failed_fingers = []
    for tap in plotinfo['taps']:
        for point, verdict in zip(tap['targetpoints'], [f['verdict'] for f in tap['fingers']]):
            lines.append(point)
            if verdict:
                passed_fingers.append(point)
            else:
                failed_fingers.append(point)
        lines.append((None, None))

    # Lines connecting points
    x = [p[0] for p in lines]
    y = [p[1] for p in lines]
    plt.plot(x, y, color='k', zorder=_zorder['lines'])
    # Passed points
    x = [p[0] for p in passed_fingers]
    y = [p[1] for p in passed_fingers]
    plt.scatter(x, y,  s=_markersize, c=_PASS, zorder=_zorder['pass'], edgecolors='k')
    # Failed points
    x = [p[0] for p in failed_fingers]
    y = [p[1] for p in failed_fingers]
    plt.scatter(x, y, s=_markersize, c=_FAIL, zorder=_zorder['fail'], edgecolors='k')

    s.Time("Plots")

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')


@synchronized
def plot_multifinger_tapdetails(imagepath, plotinfo, dutinfo, *args, **kwargs):
    """ Plots multifinger tap detailed plot for single tap.
        plotinfo argument is the result array from multifinger tap analysis """
    # Used by:

    s = Timer(3)
    fig = plt.figure(num=3, dpi=100, figsize=(8,8))
    plt.clf()

    cx = np.cos(np.linspace(0,np.pi*2, num=32))
    cy = np.sin(np.linspace(0,np.pi*2, num=32))

    num_fingers = plotinfo['num_fingers']

    gs = gridspec.GridSpec(2, num_fingers, height_ratios = [3, 1])
    ax0 = plt.subplot(gs[0, :])
    axf = [plt.subplot(gs[1, i]) for i in range(num_fingers)]

    ax0.axis('equal')
    if 'title' in kwargs:
        ax0.set_title(kwargs['title'])

    error_c = []
    passed_points = []
    failed_points = []
    failed_lines = []
    for i, f in enumerate(plotinfo['fingers']):
        passed_f = []
        failed_f = []
        failed_linesf = []
        for id in f['points'].keys():
            passed_f.extend([p for d, p in zip(f['distances'][id], f['points'][id]) if d <= f['maxposerror']])
            failed_f.extend([p for d, p in zip(f['distances'][id], f['points'][id]) if d > f['maxposerror']])
            for p in failed_f:
                failed_linesf.extend(zip((f['target'][0], p[0], None), (f['target'][1], p[1], None)))
        passed_points.extend(passed_f)
        failed_points.extend(failed_f)
        failed_lines.extend(failed_linesf)

        error_cf = zip([f['target'][0] + x * float(f['maxposerror']) for x in cx],
                       [f['target'][1] + y * float(f['maxposerror']) for y in cy])
        error_c.extend(error_cf)
        error_c.append((None,None))

        axf[i].axis('equal')
        axf[i].set_xticklabels([])
        axf[i].set_yticklabels([])
        axf[i].set_title('Finger %d' % (i + 1))

        # Subplot: Passed points
        x = [p[0] for p in passed_f]
        y = [p[1] for p in passed_f]
        axf[i].scatter(x, y,  s=_markersize, c=_PASS, zorder=_zorder['pass'], edgecolors='k')
        # Subplot: lines
        x = [p[0] for p in error_cf]
        y = [p[1] for p in error_cf]
        axf[i].plot(x, y, color='k', zorder=_zorder['lines'])
        # Subplot: Lines to failed points
        x = [p[0] for p in failed_linesf]
        y = [p[1] for p in failed_linesf]
        axf[i].plot(x, y, color=_FAIL, zorder=_zorder['lines'])
        # Subplot: Failed points
        x = [p[0] for p in failed_f]
        y = [p[1] for p in failed_f]
        axf[i].scatter(x, y, s=_markersize, c=_FAIL, zorder=_zorder['fail'], edgecolors='k')
        diagstr = "n=%d, id: %s" % (len(passed_f) + len(failed_f), ','.join(str(k) for k in f['points'].keys()))
        col = 'k' if len(f['points'].keys()) == 1 else _FAIL
        axf[i].text(0.5, -0.15,diagstr, color=col, horizontalalignment='center', verticalalignment='center', transform=axf[i].transAxes)
        axf[i].set_ylim(axf[i].get_ylim()[::-1])


    # Annotations
    x = [f['target'][0] for f in plotinfo['fingers']]
    y = [f['target'][1] for f in plotinfo['fingers']]
    d = [float(f['maxposerror']) for f in plotinfo['fingers']]
    strings = [i + 1 for i in range(len(plotinfo['fingers']))]
    for (x, y, d, string) in zip(x, y, d, strings):
        ax0.annotate(string, (x+d,y+d), xytext=(1, 1), textcoords='offset points')

    # Passed points
    x = [p[0] for p in passed_points]
    y = [p[1] for p in passed_points]
    ax0.scatter(x, y,  s=_markersize, c=_PASS, zorder=_zorder['pass'], edgecolors='k')
    # Circles
    x = [p[0] for p in error_c]
    y = [p[1] for p in error_c]
    ax0.plot(x, y, color='k', zorder=_zorder['lines'])

    # Lines to failed points
    x = [p[0] for p in failed_lines]
    y = [p[1] for p in failed_lines]
    ax0.plot(x, y, color=_FAIL, zorder=_zorder['lines'])
    # Failed points
    x = [p[0] for p in failed_points]
    y = [p[1] for p in failed_points]
    ax0.scatter(x, y, s=_markersize, c=_FAIL, zorder=_zorder['fail'], edgecolors='k')
    ax0.set_ylim(ax0.get_ylim()[::-1])

    s.Time("Plots")

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')
    s.Time("Save")

@synchronized
def plot_separation_results(imagepath, plotinfo, dutinfo, *args, **kwargs):
    """ Plots separation general view
        plotinfo argument is the result array from separation analysis """
    # Used by:

    s = Timer(3)
    fig = plt.figure(1)
    plt.clf()

    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    passed = []
    failed = []
    for angle, avalues in plotinfo['angles'].items():
        for distance, dvalues in avalues['distances'].items():
            if dvalues['verdict']:
                passed.extend([dvalues['point'], dvalues['point2']])
            else:
                failed.extend([dvalues['point'], dvalues['point2']])

    # Passed points
    x = [p[0] for p in passed]
    y = [p[1] for p in passed]
    plt.scatter(x, y,  s=_markersize, c=_PASS, zorder=_zorder['pass'],edgecolors='k')
    # Failed points
    x = [p[0] for p in failed]
    y = [p[1] for p in failed]
    plt.scatter(x, y, s=_markersize, c=_FAIL, zorder=_zorder['fail'],edgecolors='k')

    s.Time("Plots")

    ax = plt.gca()
    ax.autoscale(tight=True)
    ax.set_aspect('equal', 'datalim')
    ax.set_ylim(ax.get_ylim()[::-1])

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')
    s.Time("Save")

@synchronized
def plot_separation_details(imagepath, plotinfo, dutinfo, *args, **kwargs):
    """ Plots separation general view
        plotinfo argument is the result array from separation analysis """
    # Used by:

    s = Timer(3)
    fig = plt.figure(1)
    plt.clf()
    plt.axis('equal')

    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    passed = []
    failed = []
    for angle, avalues in plotinfo['angles'].items():
        for distance, dvalues in avalues['distances'].items():
            for tapid, taps in dvalues['taps'].items():
                if dvalues['verdict']:
                    passed.extend(taps)
                else:
                    failed.extend(taps)

    # Passed points
    x = [p[0] for p in passed]
    y = [p[1] for p in passed]
    plt.scatter(x, y,  s=_markersize, c=_PASS, zorder=_zorder['pass'],edgecolors='k')
    # Failed points
    x = [p[0] for p in failed]
    y = [p[1] for p in failed]
    plt.scatter(x, y, s=_markersize, c=_FAIL, zorder=_zorder['fail'],edgecolors='k')

    ax = plt.gca()
    ax.autoscale(tight=True)
    ax.set_aspect('equal', 'datalim')
    ax.set_ylim(ax.get_ylim()[::-1])

    s.Time("Plots")

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')
    s.Time("Save")

@synchronized
def plot_separation_tapdetails(imagepath, plotinfo, dutinfo, *args, **kwargs):
    """ Plots separation tap details
        plotinfo argument is the result array from separation analysis """
    # Used by:

    s = Timer(3)
    fig = plt.figure(5, figsize=(6,6), dpi=100)
    plt.clf()
    plt.axis('equal')

    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    radius = plotinfo['point_diameter'] / 2.0
    x = plotinfo['point'][0] + radius*np.cos(np.linspace(0,np.pi*2))
    y = plotinfo['point'][1] + radius*np.sin(np.linspace(0,np.pi*2))
    plt.plot(x, y, "k", zorder=_zorder['lines'])
    radius = plotinfo['point2_diameter'] / 2.0
    x = plotinfo['point2'][0] + radius*np.cos(np.linspace(0,np.pi*2))
    y = plotinfo['point2'][1] + radius*np.sin(np.linspace(0,np.pi*2))
    plt.plot(x, y, "k", zorder=_zorder['lines'])

    passed = []
    failed = []
    lines = []
    for tapid, taps in plotinfo['taps'].items():
        if plotinfo['verdict']:
            passed.extend(taps)
        else:
            failed.extend(taps)
        lines.extend(taps)
        lines.append((None,None))

    # Passed points
    x = [p[0] for p in passed]
    y = [p[1] for p in passed]
    plt.scatter(x, y,  s=_markersize, c=_PASS, zorder=_zorder['pass'],edgecolors='k')
    # Failed points
    x = [p[0] for p in failed]
    y = [p[1] for p in failed]
    plt.scatter(x, y, s=_markersize, c=_FAIL, zorder=_zorder['fail'],edgecolors='k')
    x = [p[0] for p in lines]
    y = [p[1] for p in lines]
    plt.plot(x, y, "k", zorder=_zorder['lines'])

    ax = plt.gca()
    ax.set_ylim(ax.get_ylim()[::-1])

    s.Time("Plots")

    # Create the image
    fig.savefig(imagepath)
    plt.close('all')
    s.Time("Save")


@synchronized
def plot_multifinger_swipedetails(imagepath, plotinfo, dutinfo, **kwargs):
    """ Plots multifinger swipe details diagram - two subplots with target and swipe information
        plotinfo argument comes from multifinger swipe analysis """
    # Used by: multifinger swipe

    s = Timer(3)
    fig = plt.figure(num=6, dpi=100, figsize=(10,8))
    plt.clf()

    if 'title' in kwargs:
        plt.suptitle(kwargs['title'])

    # Plot panel borders
    gs = gridspec.GridSpec(len(plotinfo['fingers']), 2, hspace=0.35)
    ax = plt.subplot(gs[:, 0])

    plt.axis('equal')
    plt.xlabel('X [mm]')
    plt.ylabel('Y [mm]')
    plotters.plot_panel_borders(dutinfo.dimensions[0], dutinfo.dimensions[1],zorder=_zorder['edges'])
    plt.axis([-5.0, dutinfo.dimensions[0] + 5.0, dutinfo.dimensions[1] + 5.0, -5.0])

    passed = []
    failed = []

    for finger in plotinfo['fingers']:
        for idpoints in finger['passed_points'].values():
            passed.extend(idpoints)
        for idpoints in finger['failed_points'].values():
            failed.extend(idpoints)
        plt.arrow(finger['swipe_start'][0], finger['swipe_start'][1],
                  finger['swipe_end'][0] - finger['swipe_start'][0],
                  finger['swipe_end'][1] - finger['swipe_start'][1],
                  width=0.1, length_includes_head=True)

    # Target
    x = [p[0] for p in passed]
    y = [p[1] for p in passed]
    plt.scatter(x, y, s=_markersize, c=_PASS, zorder=_zorder['pass'], edgecolors='k')
    x = [p[0] for p in failed]
    y = [p[1] for p in failed]
    plt.scatter(x, y, s=_markersize, c=_FAIL, zorder=_zorder['fail'], edgecolors='k')

    # Plot swipes
    for i, finger in enumerate(plotinfo['fingers']):
        axf = plt.subplot(gs[i, 1])
        if i == len(plotinfo['fingers']) - 1:
            plt.xlabel('distance traveled [mm]')

        x = []
        y = []
        jitters = []
        for fid in finger['swipe_points'].keys():
            x.extend([p[0] for p in finger['swipe_points'][fid]])
            y.extend([p[1] for p in finger['swipe_points'][fid]])
            jitters.extend(finger['jitters'][fid])
        #plt.plot(x, y, "o-", color='k', mec='k', mfc='r')
        plt.plot(x, y, color='b')
        plt.vlines(x, 0.0, y, alpha=0.5)
        plt.plot(x, jitters, color=_DEFAULT)
        if len(x) > 0:
            axf.set_title('Finger %d id: %s, n=%d' % (i + 1, ', '.join([str(id) for id in finger['swipe_points'].keys()]), len(x)), fontsize=8)
        else:
            axf.set_title('Finger %d no measurements' % (i + 1), fontsize=8)
        legend = plt.legend(("offset", "jitter"), bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0, fontsize=8)
        for tick in axf.xaxis.get_major_ticks():
            tick.label.set_fontsize(8)
        for tick in axf.yaxis.get_major_ticks():
            tick.label.set_fontsize(8)

    s.Time("Plots")

    # Create the image
    fig.savefig(imagepath, bbox_inches="tight")
    plt.close('all')
    s.Time("Save")

