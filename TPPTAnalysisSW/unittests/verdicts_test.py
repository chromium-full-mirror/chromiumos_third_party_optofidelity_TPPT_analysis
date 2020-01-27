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

# Test class for testing test generation (phew...)

import unittest
import testbase
import time

# Result generation time threshold for acceptance
# Analysis should run in 500 ms
_report_time_threshold = 0.5

def setUpModule():
    import start_webserver

class VerdictTest(unittest.TestCase):
    
    # addTestId - runTest pattern enables us to read test id's from database
    # and run each test id as a separate test
    @staticmethod
    def addTestId(test_id):
        def subtest(self):
            self.runTest(test_id)
        
        test_method = "test_testid_%s" % test_id
        setattr(VerdictTest, test_method, subtest)
        return test_method

    def runTest(self, test_id):
        import testbase
        testclass = testbase.TestBase.create(test_id)
        self.assertIsNotNone(testclass, "None testclass for test id %s" % str(test_id))
        start = time.clock()
        verdict = testclass.runanalysis()       
        end = time.clock()
        self.assertIn(verdict, ["Pass", "Fail", "N/A"], "Invalid response for test id %s: %s" % (test_id, verdict))
        self.assertLessEqual(end-start, _report_time_threshold, "The execution of verdict took too long: %.1f seconds" % (end-start))

def suite():
    import measurementdb
    dbsession = measurementdb.get_database().session()
    test_ids = dbsession.query(measurementdb.TestItem).order_by(measurementdb.TestItem.id).\
                                                       values(measurementdb.TestItem.id)

    tests = []
    for test_id in test_ids:
        tests.append(VerdictTest.addTestId(str(test_id[0])))

    suite = unittest.TestSuite()
    for test in tests:
        suite.addTest(VerdictTest(test))
    return suite
