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

from cherrypy import *

from .base_page import BasePage
import TPPTAnalysisSW.testbase as testbase
from optofidelity_protocols.measurementdb import get_database, TestResult
from datetime import datetime
import TPPTAnalysisSW.test_refs as test_refs
import json
import TPPTAnalysisSW.sqluploader as cloud
import TPPTAnalysisSW.tests.test_config as testconfig



def upload_test(test_id, **kwargs):
    test_class_object, cache = testbase.TestBase.create(test_id, **kwargs)

    if test_class_object:
        response.headers['Content-type'] = 'application/json'
        # Upload test results, needs to be done first
        # to get the test start time easily
        result_test = cloud.upload_test(test_class_object)
        result_test = "Results upload: " + result_test
        # Upload test configs
        test_config = testconfig.TestConfig()
        # Connecting the test and configs
        test_config.set_linked_test(test_class_object)
        result_config = cloud.upload_test(test_config)
        result_config = " Config upload: " + result_config

        return json.dumps(result_test + " | " + result_config).encode()
    else:
        print("unknown test type (test id %s)" % test_id)
        raise HTTPError(status="500", message="Internal error - test type not found")

#Controller for test
class Test(BasePage):
    SAVEPATH = ""
    exposed = True


    def GET(self, test_id=None, function=None, **kwargs):
        #print "Test GET, testid", test_id
        if (test_id==None):
            raise HTTPError("404")

        generator, cache = testbase.TestBase.create(test_id, **kwargs)
        if 'refresh' in kwargs and kwargs['refresh'] == "yes":
            cache = False

        if generator:

            if cache:
                html, result = test_refs.testclass_refs[test_id].createreport(cache=True, **kwargs)
                return html

            else:
                html, result = generator.createreport(**kwargs)

                session = get_database().session()
                dbresult = TestResult()
                dbresult.test_id = test_id
                dbresult.result = result
                dbresult.calculated = datetime.now()
                session.query(TestResult).filter(TestResult.test_id == test_id).delete()
                session.add(dbresult)
                session.commit()

                return html
        else:
            print("unknown test type (test id %s)" % test_id)
            raise HTTPError(status="500", message="Internal error - test type not found")

    def PUT(self,**kwargs):
        pass

    def POST(self, test_id=None, function=None, **kwargs):
        if function == 'upload':
            if test_id is None:
                raise HTTPError("404")

            return upload_test(test_id, **kwargs)