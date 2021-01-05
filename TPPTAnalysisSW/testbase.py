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

from sqlalchemy.orm import joinedload
from datetime import datetime
import numpy as np
import math

import time
import traceback
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.analyzers as analyzers

from optofidelity_protocols.measurementdb import get_database, TestItem, TestResult
from .settings import settings
from TPPTAnalysisSW.sqluploader import Session, is_sql_uploader_initialized
import TPPTAnalysisSW.test_refs as test_refs

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# generator functions for the different images - will be filled by the decorator
# This is a directory id -> generating function
_test_generators = {}

def timestr_to_datetime(timestr):
    """
    Convert time string that has been generated in TPPT scripts via time.strftime to datetime object.
    :param timestr: Time string.
    """
    return datetime.strptime(timestr, TIME_FORMAT)

# Decorator class
class testclasscreator(object):
    """ Creates test reports and images for the test. Gets the test type id as parameter """

    _generators = {}

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        pass

    def __call__(self, f):
        global _test_generators
        for arg in self.args:
            _test_generators[arg] = f
        return f


class TestBase(object):
    """Base class for all test objects. """

    def __init__(self, test_item_row, *args, **kwargs):
        """ Initialize the common report parameters """

        # Create dictionary for testsession parameters
        self.test_item = {column.name: getattr(test_item_row, column.name) for column in test_item_row.__table__.columns}
        self.test_item['test_type_name'] = test_item_row.type.name
        self.test_id = self.test_item['id']
        self.reporting_rates = {}
        self.verdict = "Pass"

        # Set in child class __init__ to allow exists_in_database_with_start_time to be called easily from child classes
        self.sql_summary_class = None

        # Create dictionary for test session parameters
        session = test_item_row.testsession
        self.testsession = {column.name: getattr(session, column.name) for column in session.__table__.columns}
        dut = test_item_row.dut
        self.dut = {column.name: getattr(dut, column.name) for column in dut.__table__.columns}

    @staticmethod
    def create(test_id, dbsession=None, **kwargs):
        """ Create a correct subclass for given test id """
        global _test_generators

        if dbsession is None:
            dbsession = get_database().session()

        test = dbsession.query(TestItem).options(joinedload(TestItem.testsession)).\
                                                 options(joinedload(TestItem.type)).\
                                                 filter(TestItem.id==test_id).first()

        cache = True
        test_id = str(test_id)

        if test.testtype_id in _test_generators:
            if test_id not in test_refs.testclass_refs:
                generator = _test_generators[test.testtype_id](test, **kwargs)
                test_refs.testclass_refs[test_id] = generator
                cache = False

        if test.testtype_id != 15:
            cache = False

        return test_refs.testclass_refs[test_id], cache

    def get_test_item(self, dbsession=None):
        if dbsession is None:
            dbsession = get_database().session()

        test = dbsession.query(TestItem).options(joinedload(TestItem.testsession)). \
            options(joinedload(TestItem.type)). \
            filter(TestItem.id == self.test_id).first()

        return test

    def get_test_session(self, dbsession=None):
        if dbsession is None:
            dbsession = get_database().session()

        test = dbsession.query(TestItem).options(joinedload(TestItem.testsession)). \
            options(joinedload(TestItem.testsession)). \
            filter(TestItem.id == self.test_id).first()

        return test.testsession

    def get_session_and_dutinfo(self):
        """ Gets db session and dutinfo objects. """

        dbsession = get_database().session()
        dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
        return dbsession, dutinfo

    def disable_upload_button_if_already_uploaded(self, template_params):
        """
        Called from the test.createreport() for each test class
        :param template_params: template parameters for the test case
        """
        test_item = self.get_test_item()
        time_test_start = timestr_to_datetime(test_item.starttime)
        already_exists = self.exists_in_database_with_start_time(time_test_start)

        # Using pyattrs in the test_configured_body.html this disables the upload button if necessary
        template_params['upload_button_attributes'] = {'disabled': 'true'} if already_exists else {}

    def exists_in_database_with_start_time(self, time_test_start):
        """
        Assumes that time_test_start is a unique identifier for test items regardless of sqlite database id mixups
        :param time_test_start: Timestamp for the TestItem.starttime in measurementdb
        :return: True if rows found for the test class in database, False otherwise
        """

        # If DB is not initialized, return True (return value should not be used in this case)
        if not is_sql_uploader_initialized():
            return True

        session = Session()

        try:
            query = session.query(self.sql_summary_class)\
                            .filter(self.sql_summary_class.time_test_start == time_test_start)

            exists = session.query(query.exists()).scalar()
        finally:
            session.close()

        return exists

    # These functions must be implemented in the child classes

    def runanalysis(self, *args, **kwargs):
        raise NotImplementedError("Method not implemented")

    def clearanalysis(self, *args, **kwargs):
        raise NotImplementedError("Method not implemented")

    def createreport(self, *args, **kwargs):
        raise NotImplementedError("Method not implemented")

    def createimage(self, *args, **kwargs):
        raise NotImplementedError("Method not implemented")

    def create_common_templateparams(self, *args, **kwargs):
        templateParams = {}
        templateParams["test_item"] = self.test_item
        templateParams["testsession"] = self.testsession
        templateParams["dut"] = self.dut
        templateParams["test_id"] = self.test_item['id']
        templateParams["test_type_name"] = self.test_item['test_type_name']
        templateParams["curtime"] = time.time()

        templateParams["settings"] = settings

        templateParams["sql_uploader_initialized"] = is_sql_uploader_initialized()

        templateParams["kwargs"] = kwargs

        return templateParams

    @staticmethod
    def evaluateresult(test_id, dbsession=None, recalculate=True):

        if dbsession is None:
            session = get_database().session()
        else:
            session = dbsession

        result = None

        if recalculate:
            testclass = TestBase.create(test_id, dbsession=session)[0]

        try:

            if recalculate:
                if testclass is not None:
                    result = testclass.runanalysis()
                else:
                    # Test class not found!
                    print("Test class not found for test " + str(test_id))
                    result = "Error"

            dbresult = TestResult()
            dbresult.test_id = test_id

            if recalculate:
                dbresult.result = result
            else:
                result = "Requires recalculate"
                dbresult.result = result

            dbresult.calculated = datetime.now()
            session.query(TestResult).filter(TestResult.test_id == test_id).delete()
            session.add(dbresult)
            session.commit()

        except Exception as e:
            print(traceback.format_exc())
            result = "Error"

        if dbsession is None:
            session.close()

        return result
