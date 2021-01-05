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

from decimal import Decimal
from optofidelity_protocols.measurementdb import Setting

settings = {}

precision = Decimal("0.001") # Precision to use in calculations

setting_categories = {'One Finger Non-Stationary Reporting Rate': ['minreportingrate'],
                      'One Finger Swipe': ['maxoffset', 'maxjitter', 'jittermask', 'maxmissingswipes'],
                      'Linearity': ['max_avg_of_max_errors', 'max_rms_error', 'min_report_rate',
                                    'min_report_rate_noise_inj_single', 'min_report_rate_noise_inj_multi',
                                    'max_missing_swipes', 'max_broken_lines', 'max_ghost_fingers', 'jitter_mask'],
                      'One Finger Tap': ['edgelimit', 'maxposerror', 'maxmissing', 'edgepositioningerror', 'maxedgemissing'],
                      'Grid Accuracy': ['max_error_edge', 'max_error_edge_corner_notch', 'max_error_center',
                                        'grid_acc_missing_points'],
                      'One Finger Tap Repeatability': ['maxrepeaterror'],
                      'One Finger Tapping Repeatability Test': ['max_error_edge_down', 'max_error_edge_up',
                                                                'max_error_center_down', 'max_error_center_up',
                                                                'max_error_corner_down', 'max_error_corner_up',
                                                                'repeatability_missing_points'],
                      'One Finger Stationary Jitter': ['maxstationaryjitter'],
                      'Stationary Jitter Static Noise': ['max_stat_jitter_no_noise', 'max_stat_jitter_noise',
                                                         'max_noise_test_jitter', 'jitter_missing_points'],
                      'One Finger Stationary Reporting Rate': ['minreportingrate'],
                      'MultiFinger Tap': ['edgelimit', 'maxposerror', 'maxmissing', 'edgepositioningerror', 'maxedgemissing'],
                      'MultiFinger Swipe': ['maxoffset', 'maxjitter', 'jittermask', 'maxmissingswipes'],
                      'Two Finger Separation': ['maxseparation', 'maxdiagseparation'],
                      }

csvchars = ".,"

def loadSettings(dbsession):
    global settings
    dbSettings = dbsession.query(Setting).all()

    for s in dbSettings:
        settings[s.id] = Decimal.quantize(Decimal(s.value), precision)
