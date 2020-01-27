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

from .measurementdb import *
import sqlalchemy
import inspect
import TPPTAnalysisSW.measurementdb as measurementdb


def copy_test(source_path, destination_path, test_id):
    source_db = ResultDatabase(source_path)
    destination_db = ResultDatabase(destination_path)

    session = source_db.session()

    # Tables to be fetched:
    #   "test_item"
    #     [test_object]
    #     [test_results] (list)
    #     "test_result"
    #   "test_dut"
    #   "test_type"
    #   "test_session"
    #
    # ???
    #   "dut_parameters"
    #   "session_parameters"
    #   "dut_information_test"

    # Get the test_item, test object, test_result
    test_item = session.query(TestItem).filter_by(id=test_id).first()
    if test_item is None:
        print("Error: test_item with ID", test_id, "not found.")
        return

    test_object = None
    test_result = None

    # Get the test object related to this test
    for name, obj in inspect.getmembers(measurementdb):
        if inspect.isclass(obj) and hasattr(obj, '__tablename__') and hasattr(obj, 'test_id'):
            test = session.query(obj).filter_by(test_id=test_item.id).first()
            if test is not None:
                if test.__tablename__ == 'test_result':
                    test_result = test
                else:
                    test_object = test

    results = None
    if test_object is None:
        print("test_item has no tests")
    else:
        # Get the results related to this test
        for name, obj in inspect.getmembers(measurementdb):
            if inspect.isclass(obj) and hasattr(obj, '__tablename__'):
                if hasattr(obj, 'point_id'):
                    results = session.query(obj).filter_by(point_id=test_object.id).all()
                    break
                elif hasattr(obj, 'swipe_id'):
                    results = session.query(obj).filter_by(swipe_id=test_object.id).all()
                    break

    test_dut = test_item.dut
    test_type = test_item.type
    test_session = test_item.testsession

    dut_parameters = session.query(DutParameters).filter_by(
        dut_id=test_dut.id).first()
    session_parameters = session.query(SessionParameters).filter_by(
        testsession_id=test_session.id).first()
    dut_information_test = session.query(DUTInformationTest).filter_by(
        testsession_id=test_session.id).first()

    destination_session = destination_db.session()

    # Remove all object instances from the source session
    """
    session.expunge(test_item.testsession)
    session.expunge(test_item.dut)
    session.expunge(test_item.type)
    session.expunge(test_item)
    session.expunge(test_object)
    session.expunge(test_result)
    session.expunge(session_parameters)
    session.expunge(dut_information_test)
    session.expunge(dut_parameters)
    """
    session.expunge_all()

    if test_item.dut is not None:
        sqlalchemy.orm.session.make_transient(test_item.dut)
    if test_item.type is not None:
        sqlalchemy.orm.session.make_transient(test_item.type)
    if test_item.testsession is not None:
        sqlalchemy.orm.session.make_transient(test_item.testsession)

    if dut_parameters is not None:
        sqlalchemy.orm.session.make_transient(dut_parameters)

    sqlalchemy.orm.session.make_transient(test_item)

    if session_parameters is not None:
        sqlalchemy.orm.session.make_transient(session_parameters)
    if dut_information_test is not None:
        sqlalchemy.orm.session.make_transient(dut_information_test)
    if test_object is not None:
        sqlalchemy.orm.session.make_transient(test_object)
    if test_result is not None:
        sqlalchemy.orm.session.make_transient(test_result)

    # Change the keys for all tables in order to avoid conflicts, update foreign keys

    # test_dut
    dest_duts = destination_session.query(TestDUT).all()
    test_dut.id = get_largest_id(dest_duts) + 1

    # test_type
    dest_types = destination_session.query(TestType).all()
    test_type.id = get_largest_id(dest_types) + 1

    # test_session
    dest_testsessions = destination_session.query(TestSession).all()
    test_session.id = get_largest_id(dest_testsessions) + 1

    # dut_parameters
    dest_dutparams = destination_session.query(DutParameters).all()
    dut_parameters.id = get_largest_id(dest_dutparams) + 1
    dut_parameters.dut_id = test_dut.id

    # test_item
    dest_testitems = destination_session.query(TestItem).all()
    test_item.id = get_largest_id(dest_testitems) + 1
    try:
        test_item.dut_id = test_dut.id
        test_item.testsession_id = test_session.id
        test_item.testtype_id = test_type.id
    except:
        pass

    # session_parameters
    if session_parameters is not None:
        dest_session_params = destination_session.query(SessionParameters).all()
        session_parameters.id = get_largest_id(dest_session_params) + 1
        session_parameters.testsession_id = test_session.id

    # dut_information_test
    if dut_information_test is not None:
        dest_information_tests = destination_session.query(DUTInformationTest).all()
        dut_information_test.id = get_largest_id(dest_information_tests) + 1
        dut_information_test.testsession_id = test_session.id

    # [test_object]
    if test_object is not None:
        dest_testobjects = destination_session.query(type(test_object)).all()
        test_object.id = get_largest_id(dest_testobjects) + 1
        test_object.test_id = test_item.id

    # test_result
    if test_result is not None:
        dest_testresult = destination_session.query(TestResult).all()
        test_result.id = get_largest_id(dest_testresult) + 1
        test_result.test_id = test_item.id

    # [results]
    if results is not None:
        all_results = destination_session.query(type(results[0])).all()
        largest_id = get_largest_id(all_results)
        i = 1
        for r in results:
            #session.expunge(r)
            sqlalchemy.orm.session.make_transient(r)
            r.id = largest_id + i
            if hasattr(r, 'swipe_id'):
                r.swipe_id = test_object.id
            else:
                r.point_id = test_object.id
            i += 1

    # Add the tables to the database starting from results
    if results is not None:
        destination_session.add_all(results)

    if test_object is not None:
        destination_session.add(test_object)
    if test_result is not None:
        destination_session.add(test_result)

    destination_session.add(dut_parameters)
    destination_session.add(test_item)

    if session_parameters is not None:
        destination_session.add(session_parameters)
    if dut_information_test is not None:
        destination_session.add(dut_information_test)

    destination_session.add(test_dut)
    destination_session.add(test_type)
    destination_session.add(test_session)

    # Done, commit
    destination_session.commit()
    print("Test item copied and committed successfully")


def get_largest_id(results):
    largest_id = 0
    for r in results:
        if r.id > largest_id:
            largest_id = r.id

    return largest_id


if __name__ == "__main__":
    path_src = r"C:\Users\hkleme\Downloads\TPPT\J\database_separation.sqlite"
    path_dst = r"C:\Users\hkleme\Downloads\TPPT\J\database.sqlite"
    test_id = 2

    copy_test(path_src, path_dst, test_id)
