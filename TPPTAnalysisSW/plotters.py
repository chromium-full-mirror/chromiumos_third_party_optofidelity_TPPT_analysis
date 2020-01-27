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

# Contains functions which do the math and plot figures
# These functions do not cause side effects

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from numpy import diff
from matplotlib import cm

def plot_panel_borders(panelwidthmm, panelheightmm, zorder=1):
    # Plots panel borders to the plot
    plt.plot([panelwidthmm,0],[0,0], color="black", zorder=zorder)
    plt.plot([0,0],[0,panelheightmm], color="black", zorder=zorder)
    plt.plot([0,panelwidthmm],[panelheightmm,panelheightmm], color="black", zorder=zorder)
    plt.plot([panelwidthmm,panelwidthmm],[0,panelheightmm], color="black", zorder=zorder)

def plot_3d_panel_borders(ax, panelwidthmm, panelheightmm, zorder=1):
    # Plots panel borders to the plot
    x = np.array([0, panelwidthmm])
    y = np.array([0, panelheightmm])
    x, y = np.meshgrid(x, y)
    z = np.zeros(x.shape)
    surf = ax.plot_surface(x, y, z, rstride=1, cstride=1, cmap=cm.gray,
                           linewidth=1, antialiased=False, zorder=zorder,
                           alpha=0.6)

def split_bins(bins, factor):
    """ Splits the equally sized bins into smaller bins of equal size, each bin is splitted into factor new bins """
    retval = [bins[0]]
    diffs = diff(bins) # Bin sizes

    # This loop extends the array item by item by inserting (factor - 1) new values in each bin
    for b, d in zip(bins[1:], diffs):
        retval.extend([(b - i*d/factor) for i in range(factor - 1, -1, -1)])

    return retval

def get_range(points):
    """ Gets the range of list of (x, y) points. Returns tuple of (min_x, min_y, max_x, max_y) 
        The point tuples may contain other values that are discarded. Returns None if
        there are no points in the list """
    if points is None or len(points) == 0:
        return None

    x = [p[0] for p in points]
    y = [p[1] for p in points]
    return (min(x), min(y), max(x), max(y))
