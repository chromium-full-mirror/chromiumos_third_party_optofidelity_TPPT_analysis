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
from sqlalchemy import Column, INTEGER, DATETIME, VARCHAR, func

from TPPTAnalysisSW.testbase import TestBase, timestr_to_datetime
from TPPTAnalysisSW.info.version import Version
from TPPTAnalysisSW.sqluploader import Base


class TestConfigSQL(Base):
    __tablename__ = 'touch_test_config'
    meta_id = Column(INTEGER, primary_key=True)
    time_test_start = Column(DATETIME)
    dut_id = Column(VARCHAR(40))
    test_description = Column(VARCHAR(100))
    operator = Column(VARCHAR(40))
    station_id = Column(VARCHAR(40))
    version_tppt_scripts = Column(VARCHAR(40))
    version_tnt_server = Column(VARCHAR(40))
    version_tppt_analyser = Column(VARCHAR(40))
    created = Column(DATETIME(), server_default=func.current_timestamp())


class TestConfig(TestBase):
    """
    Implements TestConfig class that is used to upload data to test_config database
    """

    def __init__(self, *args, **kwargs):
        self.sql_summary_class = TestConfigSQL
        self.linked_test = None

    def set_linked_test(self, test_class_object):
        """
        Test config is always bound to an actual test and the
        connection is set here.
        :param test_class_object: instance of the test class we want to write the configs to
        :return:
        """
        self.linked_test = test_class_object

    def upload_sql_data(self, session):
        """
        Uploads data to SQL database
        :param session: test object the data of which we want to upload
        :return:
        """
        # Most of the needed data is saved in test_session database table
        test_session_db_dict = self.linked_test.testsession
        time_test_start = timestr_to_datetime(self.linked_test.test_item['starttime'])
        # Does the database field already exist
        if self.exists_in_database_with_start_time(time_test_start):
            pass
        else:
            testconfig = TestConfigSQL()
            testconfig.time_test_start = time_test_start
            testconfig.dut_id = self.linked_test.dut['sample_id']
            testconfig.test_description = test_session_db_dict['notes']
            testconfig.operator = test_session_db_dict['operator']
            testconfig.station_id = test_session_db_dict['station_id']
            testconfig.version_tppt_scripts = test_session_db_dict['tppt_version']
            testconfig.version_tnt_server = test_session_db_dict['tnt_version']
            testconfig.version_tppt_analyser = Version.software
            session.add(testconfig)
            session.commit()

