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
import sqlite3
import time

_indices = {'dut_information_test_fkey': ['dut_information_test', 'testsession_id'],
            'dut_parameters_fkey': ['dut_parameters', 'dut_id'],
            'multi_finger_swipe_results_fkey': ['multi_finger_swipe_results', 'swipe_id'],
            'multi_finger_swipe_test_fkey': ['multi_finger_swipe_test', 'test_id'],
            'multi_finger_tap_results_fkey': ['multi_finger_tap_results', 'point_id'],
            'multi_finger_tap_test_fkey': ['multi_finger_tap_test', 'test_id'],
            'one_finger_non_stationary_reporting_rate_results_fkey': ['one_finger_non_stationary_reporting_rate_results', 'swipe_id'],
            'one_finger_non_stationary_reporting_rate_test_fkey': ['one_finger_non_stationary_reporting_rate_test', 'test_id'],
            'one_finger_stationary_jitter_results_fkey': ['one_finger_stationary_jitter_results', 'point_id'],
            'one_finger_stationary_jitter_test_fkey': ['one_finger_stationary_jitter_test','test_id'],
            'one_finger_stationary_reporting_rate_results_fkey': ['one_finger_stationary_reporting_rate_results', 'point_id'],
            'one_finger_stationary_reporting_rate_test_fkey': ['one_finger_stationary_reporting_rate_test', 'test_id'],
            'one_finger_swipe_results_fkey': ['one_finger_swipe_results', 'swipe_id'],
            'one_finger_swipe_test_fkey': ['one_finger_swipe_test', 'test_id'],
            'one_finger_tap_repeatability_test_fkey': ['one_finger_tap_repeatability_test', 'test_id'],
            'one_finger_tap_test_fkey': ['one_finger_tap_test', 'test_id'],
            'one_finger_tapping_repeatability_test_fkey': ['one_finger_tapping_repeatability_test', 'test_id'],
            'separation_results_fkey': ['separation_results', 'point_id'],
            'separation_test_fkey': ['separation_test', 'test_id'],
            'linearity_test_fkey': ['linearity_test', 'test_id'],
            'linearity_results_fkey': ['linearity_results', 'line_id'],
            'grid_accuracy_test_fkey': ['grid_accuracy_test', 'test_id'],
            'grid_accuracy_results_fkey': ['grid_accuracy_results', 'point_id'],
            'stationary_jitter_static_noise_test_fkey': ['stationary_jitter_static_noise_test', 'test_id'],
            'stationary_jitter_static_noise_results_fkey': ['stationary_jitter_static_noise_results', 'point_id'],
            'session_parameters_fkey': ['session_parameters', 'testsession_id'],
            'test_item_fkey': ['test_item', 'testsession_id'],
            'test_result_fkey': ['test_result', 'test_id'],
            }

def create_sqlite_indices(database_file):
    """ Creates indices to the SQLite database """
    max_wait_time = 15
    start = time.time()
    while(True):
        db = sqlite3.connect(database_file, timeout=1)
        try:
            curindices = get_current_indices(db)
            break
        except sqlite3.OperationalError as e:
            if time.time() - start > max_wait_time:
                raise e
            else:
                pass

    for index_name, index_values in _indices.items():
        if index_name not in curindices:
            print ("Creating database index %s" % index_name)
            create_index(db, index_name, index_values)

    db.close()

def get_current_indices(database):
    """ Returns an array of currently declared indices in the database """

    c = database.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
    indices = [r[0] for r in c.fetchall()]

    return indices

def create_index(database, index_name, index_values):
    """ Creates the specified index in the database """
    database.execute('CREATE INDEX IF NOT EXISTS %s ON %s ( %s )' % (index_name, index_values[0], index_values[1]))
