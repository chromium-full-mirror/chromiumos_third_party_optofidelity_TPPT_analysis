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
import TPPTAnalysisSW.measurementdb as measurementdb
from datetime import datetime
import TPPTAnalysisSW.test_refs as test_refs
from .info.version import Version
from genshi.template import MarkupTemplate
import TPPTAnalysisSW.testbase as testbase

class TestSessionReport(BasePage):

    exposed = True

    def GET(self, session_id=None, function=None, **kwargs):
        """ Generates one big summary report from all tests in a test session. """

        if session_id is None:
            raise HTTPError(status="500", message="Internal error - test session not found")
            return

        all_results = []
        summaries = []
        dbsession = measurementdb.get_database().session()
        session = dbsession.query(measurementdb.TestSession).filter(measurementdb.TestSession.id == session_id).first()

        if session is None:
            raise HTTPError(status="500", message="Internal error - test session not found")
            return

        for test in session.test_items:

            generator, cache = testbase.TestBase.create(test.id, **kwargs)
            summary = {"id": test.id}

            if cache:
                all_results.append(test_refs.testclass_refs[str(test.id)].get_results_for_session_template())

            else:
                html, result = generator.createreport(**kwargs)
                session = measurementdb.get_database().session()
                dbresult = measurementdb.TestResult()
                dbresult.test_id = test.id
                dbresult.result = result
                dbresult.calculated = datetime.now()
                session.query(measurementdb.TestResult).filter(measurementdb.TestResult.test_id == test.id).delete()
                session.add(dbresult)
                session.commit()
                all_results.append(test_refs.testclass_refs[str(test.id)].get_results_for_session_template())

            summary['type'] = test_refs.testclass_refs[str(test.id)].results['test_type_name']
            results = dbsession.query(measurementdb.TestResult).filter(measurementdb.TestResult.test_id == test.id).first()
            summary['verdict'] = results.result
            summaries.append(summary)

        templateParams = {}
        templateParams['test_type_name'] = "Test Session #%s Report" % session_id
        templateParams['all_results'] = all_results
        templateParams['test_script'] = 'test_page_subplots.js'
        templateParams['test_page'] = 'test_session_report.html'
        templateParams['version'] = Version
        templateParams['summaries'] = summaries

        template = MarkupTemplate(open("templates/test_session_report_common.html"))
        stream = template.generate(**(templateParams))

        return stream.render('xhtml')
