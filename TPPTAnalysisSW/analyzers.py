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

import math
import numpy as np


def analyze_swipe_linearity(points):
    """
    Calculates linear fit for a single swipe line
    Determine max, avg, stdev and rms errors from linear fit
    """
    if len(points) == 0:
        results = {'linear_error': [],
                   'fitted_y': [],
                   'lin_error_avg': float('nan'),
                   'lin_error_stdev': float('nan'),
                   'lin_error_max': float('nan'),
                   'lin_error_rms': float('nan'),
                   'linear_fit': []}
        return results

    x = []
    y = []
    for point in points:
        x.append(point[0])
        y.append(point[1])

    # Linearfit to fit the data
    # Linearcoef has slope (1) and intercept (2)
    linearcoef = np.polyfit(x, y, 1)
    linearfit = np.polyval(linearcoef, x)

    # Starndard form of linear equation
    # ax + by + c = 0
    a = linearcoef[0]
    b = -1
    c = linearcoef[1]

    # Point y-coordinates in the "fitted line coordinate frame" where the fitted line is the x-axis.
    # These are signed values, not unsigned distances.
    fitted_y = (a * np.array(x) + b * np.array(y) + c) / math.sqrt(a**2 + b**2)

    # Max deviation calc: orthogonal distance
    # from fit line to data set
    lin_error = np.absolute(fitted_y)

    lin_error_max = max(lin_error)
    lin_error_avg = np.mean(lin_error)
    lin_error_rms = np.sqrt(np.mean(np.power(lin_error, 2)))

    # Standard deviation is calculated from the y-coordinates in the "fitted line coordinate frame".
    # Sample averaging is used so ddof parameter is 1.
    lin_error_stdev = np.std(fitted_y, ddof=1)

    results = {'linear_error': lin_error.tolist(),
               'fitted_y': fitted_y.tolist(),
               'lin_error_avg': lin_error_avg,
               'lin_error_stdev': lin_error_stdev,
               'lin_error_max': lin_error_max,
               'lin_error_rms': lin_error_rms,
               'linear_fit': linearfit}

    return results


def calculate_report_rates(points):

    previous_timestamp = 0.0
    report_rates = []

    for point in points:

        if previous_timestamp == 0.0:
            previous_timestamp = point.time
        else:
            delay = point.time - previous_timestamp

            if delay > 0:
                report_rate = 1.0 / (delay / 1000.0)
                report_rates.append(report_rate)
                previous_timestamp = point.time

    return report_rates
