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

import cherrypy
from genshi.template import MarkupTemplate
from sqlalchemy.orm import joinedload
import optofidelity_protocols.measurementdb as measurementdb
from .plotinfo import *
import TPPTAnalysisSW.analyzers as analyzers
from .settings import settings
from datetime import datetime
import math
import json

import time
import traceback
import TPPTAnalysisSW.plotinfo as plotinfo
from .utils import Timer
from .testbase import TestBase
from .base_page import BasePage
from .info.version import version
import TPPTAnalysisSW.imagefactory as imagefactory
from TPPTAnalysisSW.test import upload_test
import TPPTAnalysisSW.sqluploader as sqluploader


# Controller for testsession
class TestSession(BasePage):
    exposed = True

    def GET(self, testSessionId=None, command=None):
        # Command is here in case we need to create e.g. session-wide settings
        if command is None:
            if (testSessionId == None):
                raise cherrypy.HTTPError("404", "No testsession given")

            dbsession = measurementdb.get_database().session()
            testsession = dbsession.query(measurementdb.TestSession).filter(
                measurementdb.TestSession.id == testSessionId).first()
            sessioninfo = plotinfo.TestSessionInfo(testsession=testsession)

            tests, tests_in_database, results, curved = self.sessionResultsFromDB(testsession, dbsession)
            button_attributes = [{'disabled': 'true'} if test_uploaded else {} for test_uploaded in tests_in_database]

            tests_results = zip(tests, results, button_attributes)

            # Categorize tests by DUTs
            duts = []  # list of tuples: (dut, [(test, result), ...])
            dut_indices = {}  # Dut id -> duts list index map
            for test_result in tests_results:
                dut = test_result[0].dut
                if dut.id in dut_indices:
                    # Append to an older dut
                    dut_index = dut_indices[dut.id]
                    duts[dut_index][1].append(test_result)
                else:
                    # Add new dut
                    dut_index = len(duts)
                    dut_indices[dut.id] = dut_index
                    duts.append((dut, [test_result]))

            # Disable session upload button if all the tests have been uploaded to database
            session_upload_button_attributes = {'disabled': 'true'} if tests_in_database.count(True) == len(tests) else {}

            with open("templates/testsession.html") as f:
                tmpl = MarkupTemplate(f)
                stream = tmpl.generate(duts=duts, session=sessioninfo,
                                       session_upload_button_attributes=session_upload_button_attributes,
                                       sql_uploader_initialized=sqluploader.is_sql_uploader_initialized(),
                                       version=version)
                return stream.render('xhtml')
        else:
            raise cherrypy.HTTPError("404", "Command not found")

    def POST(self, testSessionId=None, command=None, **kwargs):
        if command == 'upload_test':
            test_id = kwargs['test_id']

            return upload_test(test_id)
        elif command == 'upload_session':
            session_id = kwargs['session_id']

            dbsession = measurementdb.get_database().session()

            # Get IDs of tests that are part of the session.
            test_query = dbsession.query(measurementdb.TestItem).filter(
                measurementdb.TestItem.testsession_id == session_id)

            test_items = test_query.all()
            test_classes = [test_class for test_class, cache in map(TestBase.create, [test.id for test in test_items])]

            test_items_and_classes = zip(test_items, test_classes)

            uploaded_ids = []

            # Upload all tests in the session that are not already uploaded
            for test_item, test_class in test_items_and_classes:
                if not test_class.exists_in_database_with_start_time(test_item.starttime):
                    if upload_test(test_item.id) is None:
                        return None
                    # Keep track of uploaded test items to inform user which tests were actually uploaded
                    uploaded_ids.append(str(test_item.id))

            return json.dumps("Sequence upload successful. Uploaded tests: {}".format(', '.join(uploaded_ids))).encode()

        if 'data' not in kwargs:
            print("No data in kwargs")
            raise cherrypy.HTTPError("400", "Expected data not received")

        data = json.loads(kwargs['data'])
        if 'command' not in data:
            print("No command in data")
            raise cherrypy.HTTPError("400", "Expected command not received")

        return_data = 'No such command'

        if data['command'] == 'set_notes':
            dbsession = measurementdb.get_database().session()
            testsession = dbsession.query(measurementdb.TestSession).filter(
                measurementdb.TestSession.id == testSessionId).first()
            testsession.notes = data['value']
            dbsession.commit()
            return_data = testsession.notes

        return return_data

    @staticmethod
    def session_samples_progs_manus(testsession, dbsession):

        sample_names = set()
        sample_prog = set()
        sample_manu = set()
        sample_ver = set()

        for test in testsession.test_items:

            sample = test.dut.sample_id
            manu = test.dut.manufacturer
            prog = test.dut.program
            ver = test.dut.batch

            if sample is None or len(sample) == 0:
                sample = "[Empty]"
            sample_names.add(sample)

            if manu is None or len(manu) == 0:
                manu = "[Empty]"
            sample_manu.add(manu)

            if prog is None or len(prog) == 0:
                prog = "[Empty]"
            sample_prog.add(prog)

            if ver is None or len(ver) == 0:
                ver = "[Empty]"
            sample_ver.add(ver)

        return ", ".join(sorted(sample_names)), \
               ", ".join(sorted(sample_prog)), \
               ", ".join(sorted(sample_manu)), \
               ", ".join(sorted(sample_ver))

    @staticmethod
    def sessionResultsFromDB(testsession, dbsession):
        tests = []
        tests_in_database = []
        results = []
        test_types = []

        for test in testsession.test_items:
            if len(test.test_results) == 0:
                # Run analysis
                result = TestBase.evaluateresult(test.id)
            else:
                result = test.test_results[0].result

            test_object, cache = TestBase.create(test.id)
            already_in_database = test_object.exists_in_database_with_start_time(test.starttime)

            tests.append(test)
            tests_in_database.append(already_in_database)
            test_types.append(test.testtype_id)
            results.append(result)

        curved = False
        if len(set(test_types)) == 1:
            if test_types[0] == 15:
                curved = True

        return tests, tests_in_database, results, curved

    @classmethod
    def eval_tests_results(caller, dbsession, testSessionId, recalculate=True):
        try:
            return TestSession.do_evaluation(dbsession, testSessionId, recalculate=recalculate)
        except Exception as e:
            print("Error in analysis!", e)

    @classmethod
    def do_evaluation(caller, dbsession, testSessionId, recalculate=True):
        '''
        Analyzes all test results in test session.
        '''

        tests = dbsession.query(measurementdb.TestItem).options(joinedload('type')). \
            filter(measurementdb.TestItem.testsession_id == testSessionId).all()
        results = []

        s = Timer(2)

        for idx, t in enumerate(tests):
            imagefactory.ImageFactory.delete_images(str(t.id))
            result = TestBase.evaluateresult(t.id, recalculate=recalculate)
            results.append(result)
            s.Time("Analyzed test %d - result %s" % (t.id, result))

        return tests, results
