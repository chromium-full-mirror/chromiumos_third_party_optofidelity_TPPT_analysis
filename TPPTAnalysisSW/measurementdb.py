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
import traceback
import argparse
import json
import time
import sqlite3

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, BLOB
from sqlalchemy.orm import relation, backref, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import event
from .measurementdb_sqlite import create_sqlite_indices

Base = declarative_base()

parser = argparse.ArgumentParser()
parser.add_argument('--check', action="store_true", default=False, help='Startup check for CI usage')
parser.add_argument('--database', type=str, default='C:/OptoFidelity/TPPT/database.sqlite', help='Path to used database file')
parser.add_argument('--config', type=str, default='C:/OptoFidelity/TPPT/config.json', help='Path to used configuration file')
parser.add_argument('--dbconfig', type=str, default='C:/OptoFidelity/TPPT Analysis/dbconfig.yaml',
                        help='Path to database configuration file')
args = parser.parse_args()

database = args.database
config = args.config

def on_connect(conn, record):
    conn.execute('pragma foreign_keys=ON')


def saveLastPath(path):
    f = open(config, 'w')
    f.write(json.dumps({"lastDB": path}))
    f.close()


def getLastPath():
    try:
        f = open(config, 'r')
        data = json.load(f)

        if "lastDB" in data:
            return data['lastDB']
        else:
            return database

    except Exception as e:
        print(str(e))
        return database


class ResultDatabase:

    def __init__(self, filename):
        self.db = None
        self.session = None
        self.dbpath = None

        self.initialize(filename)
        saveLastPath(filename)

    def initialize(self, filename):

        self.dbpath = filename
        self.db = create_engine('sqlite:///' + filename)
        event.listen(self.db, 'connect', on_connect)
        self.session = sessionmaker(bind=self.db, autoflush=False)
        Base.metadata.create_all(self.db)
        create_sqlite_indices(filename)

        # Check if ResultDatabase already contains test types below.
        try:
            session = self.session()
            session.add( TestType( 0, 'One Finger Tap Test' ) )
            session.add( TestType( 1, 'One Finger Swipe Test' ) )
            session.add( TestType( 5, 'MultiFinger Swipe Test' ) )
            session.add( TestType( 6, 'DUT Information test') )
            session.add( TestType( 8, 'MultiFinger Tap Test'))
            session.add( TestType( 9, 'One Finger Stationary Jitter'))
            session.add( TestType( 10, 'One Finger Tap Repeatability'))
            session.add( TestType( 11, 'One Finger Stationary Reporting Rate Test'))
            session.add( TestType( 12, 'One Finger Non Stationary Reporting Rate Test'))
            session.add( TestType( 13, 'Linearity Test'))
            session.add( TestType( 14, 'Two Finger Separation Test'))
            session.add( TestType( 15, 'Grid Accuracy Test'))
            session.add( TestType( 16, 'Stationary Jitter Static Noise Test'))
            session.add(TestType(17, 'One Finger Tapping Repeatability Test'))
            session.commit()
            session.close()
        except:
            # Already created
            pass
        try:
            # Grid accuracy settings
            self.checksetting(
                Setting('max_error_edge', 1.5, 'mm', 'Max error in edge area (not including 4 corners and notch)'))
            self.checksetting(
                Setting('max_error_edge_corner_notch', 2.0, 'mm',
                        'Max error in edge area (including 4 corners and notch'))
            self.checksetting(
                Setting('max_error_center', 1.0, 'mm', 'Max error in center area'))
            self.checksetting(
                Setting('grid_acc_missing_points', 10, '%', 'Max amount of missing points in percents'))

            # Linearity settings
            self.checksetting(
                Setting('max_avg_of_max_errors', 0.75, 'mm',
                        'Maximum allowed max of averages of max linearity errors '))
            self.checksetting(
                Setting('max_rms_error',0.5, 'mm', 'Maximum allowed rms linearity error'))
            self.checksetting(
                Setting('min_report_rate', 120, 'Hz', 'Minimum reporting rate in active mode'))
            self.checksetting(
                Setting('min_report_rate_noise_inj_single', 120, 'Hz',
                        'Minimum reporting rate with noise injected in active mode at single touch'))
            self.checksetting(
                Setting('min_report_rate_noise_inj_multi', 100, 'Hz',
                        'Minimum reporting rate with noise injected in active mode at multi touch'))
            self.checksetting(
                Setting('max_missing_swipes', 10, '%', 'Maximum amount of missing swipes in percents'))
            self.checksetting(
                Setting('max_broken_lines', 0, 'pcs', 'Maximum amount of broken lines'))
            self.checksetting(
                Setting('max_ghost_fingers', 0, 'pcs', 'Maximum amount of ghost fingers'))
            self.checksetting(Setting('jitter_mask', 10.0, "mm", "Non stationary jitter search mask"))

            # Stationary jitter static noise settings
            self.checksetting(
                Setting('max_stat_jitter_no_noise', 0.5, 'mm', 'Max stationary jitter with no noise injected'))
            self.checksetting(
                Setting('max_stat_jitter_noise', 1.0, 'mm', 'Max stationary jitter with noise injected'))
            self.checksetting(
                Setting('max_noise_test_jitter', 1.0, 'mm', 'Max stationary jitter in static noise test'))
            self.checksetting(
                Setting('jitter_missing_points', 10, '%', 'Max percentage of allowed missing points'))

            # Tapping repeatability settings
            self.checksetting(
                Setting('max_error_edge_down', 1.5, 'mm', 'Maximum repeatability error at the edge on pen down'))
            self.checksetting(
                Setting('max_error_edge_up', 1.5, 'mm', 'Maximum repeatability error at the edge on pen lift-off'))
            self.checksetting(
                Setting('max_error_corner_down', 1.5, 'mm', 'Maximum repeatability error in the corner on pen down'))
            self.checksetting(
                Setting('max_error_corner_up', 1.5, 'mm', 'Maximum repeatability error in the corner on pen lift-off'))
            self.checksetting(
                Setting('max_error_center_down', 1.0, 'mm', 'Maximum repeatability error at the center on pen down'))
            self.checksetting(
                Setting('max_error_center_up', 1.0, 'mm', 'Maximum repeatability error at the center on pen lift-off'))
            self.checksetting(
                Setting('repeatability_missing_points', 10, '%',
                        'Maximum amount of allowed missing points in repeatability'))

            # Legacy settings
            self.checksetting(Setting('maxjitter', 1.0, "mm", "Maximum allowed non stationary jitter"))
            self.checksetting(Setting('maxstationaryjitter', 1.0, "mm", "Maximum allowed stationary jitter"))
            self.checksetting(Setting('maxstationaryjitter_with_noise', 1.0, "mm", "Maximum allowed stationary jitter with noise source"))
            self.checksetting(Setting('jittermask', 10.0, "mm", "Non stationary jitter search mask"))
            self.checksetting(Setting('maxactiveresponselatency', 25.0, "ms", "Maximum allowed response latency from an active state for the initial input"))
            self.checksetting(Setting('maxidleresponselatency', 50.0, "ms", "Maximum allowed response latency from an idle state"))
            self.checksetting(Setting('minreportingrate', 100.0, "Hz", "Minimum allowed reporting rate"))
            self.checksetting(Setting('maxposerror',1.0,"mm","Maximum allowed accuracy error"))
            self.checksetting(Setting('maxmissing',0.0,"pcs","Maximum allowed missing inputs"))
            self.checksetting(Setting('maxoffset',1.0, "mm","Maximum allowed offset"))
            self.checksetting(Setting('maxseparation',12.0,"mm","Maximum allowed finger separation distance (vertical and horizontal)"))
            self.checksetting(Setting('maxdiagseparation',15.0,"mm","Maximum allowed finger separation distance (diagonal)"))
            self.checksetting(Setting('minppi',200.0,"ppi","Minimum display resolution"))
            self.checksetting(Setting('maxhoveroffset',1.0,"mm","Maximum allowed hover offset"))
            self.checksetting(Setting('maxrepeaterror',1.0,"mm","Maximum tap repeatability error"))
            self.checksetting(Setting('edgelimit',-1.0,"mm","Edge area distance from edge in Tap test"))
            self.checksetting(Setting('edgepositioningerror',1.0,"mm","Maximum allowed accuracy error in edge area"))
            self.checksetting(Setting('maxedgemissing',0.0,"pcs","Maximum allowed missing edge inputs"))
            self.checksetting(Setting('maxmissingswipes',0.0,"pcs","Maximum allowed missing swipes in swipe test"))
            self.checksetting(Setting('maxbrokenswipes', 0.0, "pcs", "Maximum allowed broken swipes in linearity test"))
            self.checksetting(Setting('maxghostfingerswipes', 0.0, "pcs", "Maximum allowed swipes with ghost finger in linearity test"))
            self.checksetting(Setting('maxmissinghover',0.0,"pcs","Maximum allowed missing swipes in hover test"))
            self.checksetting(Setting('maxhoverjitter',1.0,"mm","Maximum allowed jitter in hover test"))

            # When adding settings, remember to add them to settings.py categories
        except: #IntegrityError:
            print(traceback.format_exc())
            # Already created
            pass

    def changeDatabase(self, path):
        self.initialize(path)
        saveLastPath(path)

    def add( self, data, commit = True ):
        session = self.session()
        session.add( data )
        if commit == True:
            self.session_commit(session)

    def addAll( self, data, commit = True ):
        session = self.session()
        session.add_all( data )
        if commit == True:
            self.session_commit(session)

    def getEngine(self):
        return self.db

    def update(self, data):
        session = self.session()
        session.merge(data)
        self.session_commit(session)

    def commit(self):
        session = self.session()
        self.session_commit(session)

    def session_commit(self, session):
        # If database is locked, try again until timeout occurs
        max_wait_time = 15
        start = time.time()
        while(True):
            try:
                session.commit()
                break
            except sqlite3.OperationalError as e:
                if time.time() - start > max_wait_time:
                    raise e
                else:
                    pass

    def get_test_sessions( self, dbsession=None ):
        if dbsession is None:
            dbsession = self.session()
        return dbsession.query( TestSession ).all()

    def get_test_session( self, session_id ):
        session = self.session()
        print("#########GET TEST SESSION")
        return session.query( TestSession ).filter_by( id=session_id ).first()

    def get_test_results( self, test_id ):
        session = self.session()
        retval =  session.query(OneFingerTapTest).filter_by( test_id=test_id ).all()
        session.close()
        return retval

    def get_TestType( self, type_id ):
        session = self.session()
        return session.query(TestType).filter_by( id=type_id ).all()

    def get_TestTypes( self ):
        session = self.session()
        return session.query(TestType).all()

    def get_programs( self ):
        session = self.session()
        return session.query( TestSession.program).order_by(TestSession.program)

    def get_manufacturers( self, Program ):
        session = self.session()
        return session.query( TestSession.manufacturer).order_by(TestSession.manufacturer).all()

    def checksetting( self, setting ):
        session = self.session()
        dbsetting = session.query(Setting).filter_by(id=setting.id).first()
        if dbsetting is None:
            # Setting does not exist
            session.add(setting)
            self.session_commit(session)
        session.close()

# Define database tables

class TestSession( Base ):

# TestSession is constant to all test cases

    __tablename__ = 'test_session'

    id = Column( Integer, primary_key=True )
    operator = Column( String )
    starttime = Column( String )
    endtime = Column( String )
    invalid = Column( Boolean )
    notes = Column( String )
    tnt_version = Column( String )
    tppt_version = Column( String )
    station_id = Column( String )


class TestDUT( Base ):

    # A DUT that is tested in one or multiple test sessions and referenced to in Test Items
    __tablename__ = 'test_dut'
    id = Column( Integer, primary_key=True )

    # Dut parameters
    program = Column( String )
    manufacturer = Column( String )
    batch = Column( String )
    serial = Column( String )
    sample_id = Column( String )
    svg_data = Column( BLOB )


class TestType( Base ):

    #Device digitizer touch test types stored here

    __tablename__ = 'test_type'

    id = Column( Integer, primary_key = True )
    name = Column( String )

    def __init__( self, id, name ):
        self.id = id
        self.name = name

class TestItem( Base ):

    #A single test related to device digitizer touch is defined here
    __tablename__ = 'test_item'

    id = Column( Integer, primary_key= True )
    testsession_id = Column( Integer, ForeignKey('test_session.id', ondelete='CASCADE'), nullable=False )
    testsession = relation( TestSession, backref = backref('test_items', order_by =  id) )
    dut_id = Column( Integer, ForeignKey('test_dut.id'), nullable=False )
    dut = relation( TestDUT, backref = backref('test_items', order_by =  id) )
    starttime = Column( String )
    endtime = Column( String )
    slot_id = Column( Integer )
    finger_type = Column( String )
    invalid = Column( Boolean )
    testtype_id = Column( Integer, ForeignKey('test_type.id', ondelete='CASCADE'), nullable=False )
    type = relation( TestType, backref = backref('test_items', order_by = id) )
    kmsg_log = Column( Text )

class SessionParameters( Base ):

    #Session parameters are defined here
    __tablename__ = 'session_parameters'

    id = Column( Integer, primary_key = True )
    testsession_id = Column( Integer, ForeignKey('test_session.id', ondelete='CASCADE'), nullable=False )
    testsession = relation(TestSession, backref = backref('session_parameters', order_by = id ) )
    name = Column( String )
    valueFloat = Column( Float )
    valueString = Column( String )
    isFloat = Column( Boolean )

class DutParameters( Base ):

    #DUT parameters are defined here
    __tablename__ = 'dut_parameters'

    id = Column( Integer, primary_key = True )
    dut_id = Column( Integer, ForeignKey('test_dut.id', ondelete='CASCADE'), nullable=False )
    dut = relation(TestDUT, backref = backref('dut_parameters', order_by = id ) )
    name = Column( String )
    valueFloat = Column( Float )
    valueString = Column( String )
    isFloat = Column( Boolean )

class DUTInformationTest( Base ):

    __tablename__ = 'dut_information_test'

    id = Column(Integer, primary_key=True)
    testsession_id = Column( Integer, ForeignKey('test_session.id', ondelete='CASCADE'), nullable=False )
    testsession = relation( TestSession, backref = backref('dut_information_test', order_by =  id) )

    name = Column( String )
    valueFloat = Column( Float )
    valueString = Column( String )
    isFloat = Column( Boolean )

class OneFingerTapTest( Base ):

    #One-finger tap results are defined here
    __tablename__ = 'one_finger_tap_test'

    id = Column(Integer, primary_key=True)
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref=backref('one_finger_tap_test', order_by=id) )

    #Are results single tap or jitter
    jitter = Column( Boolean )

    #Common parameters
    robot_x = Column( Float )
    robot_y = Column( Float )
    robot_z = Column( Float )
    point_number = Column( Integer )

    #Results
    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    finger_id = Column( Integer )
    delay = Column( Float )
    time = Column( Float )

class OneFingerTapRepeatabilityTest( Base ):

    #One-finger tap results are defined here
    __tablename__ = 'one_finger_tap_repeatability_test'

    id = Column(Integer, primary_key=True)
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref=backref('one_finger_tap_repeatability_test', order_by=id) )

    #Common parameters
    robot_x = Column( Float )
    robot_y = Column( Float )
    robot_z = Column( Float )
    point_number = Column( Integer )

    #Results
    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    finger_id = Column( Integer )
    delay = Column( Float )
    time = Column( Float )
    event = Column( Integer )


class OneFingerTappingRepeatabilityTest(Base):
    # One-finger tap results are defined here
    __tablename__ = 'one_finger_tapping_repeatability_test'

    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False)
    test = relation(TestItem, backref=backref('one_finger_tapping_repeatability_test', order_by=id))

    # Common parameters
    robot_x = Column(Float)
    robot_y = Column(Float)
    robot_z = Column(Float)
    point_number = Column(Integer)

    border_width = Column(Float)
    finger_name = Column(Text)
    finger_type = Column(Text)
    finger_size = Column(Text)
    display_background = Column(Text)
    number_of_random_locations_center = Column(Integer)
    number_of_random_locations_edge = Column(Integer)
    number_of_random_locations_corner = Column(Integer)
    number_of_taps_at_each_location = Column(Integer)
    lift_off_distance = Column(Float)
    ground_status = Column(Text)
    noise_status = Column(Text)
    touch_area = Column(Text)


class OneFingerTappingRepeatabilityResults(Base):
    # One-finger tap results are defined here
    __tablename__ = 'one_finger_tapping_repeatability_results'

    id = Column(Integer, primary_key=True)
    point_id = Column(Integer, ForeignKey('one_finger_tapping_repeatability_test' + '.id', ondelete='CASCADE'), nullable=False)
    point = relation(OneFingerTappingRepeatabilityTest, backref=backref('one_finger_tapping_repeatability_results', order_by=id))

    tap_id = Column(Integer)
    point_number = Column(Integer)
    panel_x = Column(Float)
    panel_y = Column(Float)
    sensitivity = Column(Float)
    delay = Column(Float)
    finger_id = Column(Integer)
    time = Column(Float)
    event = Column(Integer)


class OneFingerSwipeTest( Base ):

    #One-finger swipe test is defined here
    __tablename__ = 'one_finger_swipe_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('one_finger_swipe_test', order_by = id) )

    #For straight lines, start and stop positions are defined
    start_x = Column( Float )
    start_y = Column( Float )
    end_x = Column( Float )
    end_y = Column( Float )

    #For circular lines, also through position and radius in x and y directions are defined
    through_x = Column( Float )
    through_y = Column( Float )
    radius_x = Column( Float )
    radius_y = Column( Float )

class OneFingerSwipeResults( Base ):

    #One-finger swipe results are defined here
    __tablename__ = 'one_finger_swipe_results'

    id = Column( Integer, primary_key = True )
    swipe_id = Column( Integer, ForeignKey('one_finger_swipe_test.id', ondelete='CASCADE'), nullable=False )
    swipe = relation( OneFingerSwipeTest, backref = backref('one_finger_swipe_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class LinearityTest( Base ):

    #Linearity results are defined here
    __tablename__ = 'linearity_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('linearity_test', order_by = id) )

    # For straight lines, start and stop positions are defined
    start_x = Column(Float)
    start_y = Column(Float)
    end_x = Column(Float)
    end_y = Column(Float)
    #speed = Column(Float)
    test_type = Column(Text)

    # Additional metadata for the analysis to use and to pass further
    finger_name = Column(Text)
    finger_type = Column(Text)  # Metal or soft
    finger_size = Column(Float)
    num_fingers = Column(Float)
    border_width = Column(Float)
    touch_area = Column(Text)  # center/edge
    display_background = Column(Text)
    step_size = Column(Float)
    swipe_speed = Column(Integer)
    swipe_direction = Column(Integer)  # horizontal, vertical or diagonal
    lift_off_distance = Column(Float)
    ground_status = Column(Text)
    noise_status = Column(Text)

class LinearityTestResults( Base ):

    #Linearity results are defined here
    __tablename__ = 'linearity_results'

    id = Column( Integer, primary_key = True )
    line_id = Column( Integer, ForeignKey('linearity_test.id', ondelete='CASCADE'), nullable=False )
    line = relation( LinearityTest, backref = backref('linearity_results', order_by = id) )

    panel_x = Column(Float)
    panel_y = Column(Float)
    finger_id = Column(Integer)
    delay = Column(Float)
    time = Column(Float)
    event = Column(Integer)
    sensitivity = Column(Float)

class OneFingerStationaryReportingRateTest( Base ):

    #One Finger Stationary Reporting Rate Test is defined here
    __tablename__ = 'one_finger_stationary_reporting_rate_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('one_finger_stationary_reporting_rate_test', order_by = id) )

    #For straight lines, start and stop positions are defined
    robot_x = Column( Float )
    robot_y = Column( Float )

class OneFingerStationaryReportingRateResults( Base ):

    #One Finger Stationary Reporting Rate results are defined here
    __tablename__ = 'one_finger_stationary_reporting_rate_results'

    id = Column( Integer, primary_key = True )
    point_id = Column( Integer, ForeignKey('one_finger_stationary_reporting_rate_test.id', ondelete='CASCADE'), nullable=False )
    point = relation( OneFingerStationaryReportingRateTest, backref = backref('one_finger_stationary_reporting_rate_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class OneFingerNonStationaryReportingRateTest( Base ):

    #One Finger Non Stationary Reporting Rate Test is defined here
    __tablename__ = 'one_finger_non_stationary_reporting_rate_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('one_finger_non_stationary_reporting_rate_test', order_by = id) )

    #For straight lines, start and stop positions are defined
    start_x = Column( Float )
    start_y = Column( Float )
    end_x = Column( Float )
    end_y = Column( Float )

class OneFingerNonStationaryReportingRateResults( Base ):

    #One Finger Non Stationary Reporting Rate results are defined here
    __tablename__ = 'one_finger_non_stationary_reporting_rate_results'

    id = Column( Integer, primary_key = True )
    swipe_id = Column( Integer, ForeignKey('one_finger_non_stationary_reporting_rate_test.id', ondelete='CASCADE'), nullable=False )
    swipe = relation( OneFingerNonStationaryReportingRateTest, backref = backref('one_finger_non_stationary_reporting_rate_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class OneFingerStationaryJitterTest( Base ):

    #One Finger Non Stationary Reporting Rate Test is defined here
    __tablename__ = 'one_finger_stationary_jitter_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('one_finger_stationary_jitter_test', order_by = id) )

    #For straight lines, start and stop positions are defined
    robot_x = Column( Float )
    robot_y = Column( Float )


class OneFingerStationaryJitterResults( Base ):

    #One Finger Non Stationary Reporting Rate results are defined here
    __tablename__ = 'one_finger_stationary_jitter_results'

    id = Column( Integer, primary_key = True )
    point_id = Column( Integer, ForeignKey('one_finger_stationary_jitter_test.id', ondelete='CASCADE'), nullable=False )
    point = relation( OneFingerStationaryJitterTest, backref = backref('one_finger_stationary_jitter_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class SeparationTest( Base ):

    #Separation results are defined here
    __tablename__ = 'separation_test'

    id = Column(Integer, primary_key=True)
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref=backref('separation_test', order_by=id) )

    #Is measurement 2-, 3-, 4-, or 5-finger
    number_of_fingers = Column( Integer )

    robot_x = Column( Float )
    robot_y = Column( Float )
    robot_z = Column( Float )
    separation_distance = Column( Float )
    separation_angle = Column( Float )
    first_finger_offset = Column( Float )
    tool_separation = Column( Float )
    finger1_diameter = Column( Float )
    finger2_diameter = Column( Float )

class SeparationResults( Base ):

    #Separation results are defined here
    __tablename__ = 'separation_results'

    id = Column( Integer, primary_key = True )
    point_id = Column( Integer, ForeignKey('separation_test.id', ondelete='CASCADE') )
    point = relation( SeparationTest, backref = backref('separation_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class MultifingerTapTest( Base ):

    #Multifinger tap results are defined here
    __tablename__ = 'multi_finger_tap_test'

    id = Column(Integer, primary_key=True)
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref=backref('multi_finger_tap_test', order_by=id) )

    #Is measurement 2-, 3-, 4-, or 5-finger
    number_of_fingers = Column( Integer )

    robot_x = Column( Float )
    robot_y = Column( Float )
    robot_z = Column( Float )
    separation_distance = Column( Float )
    separation_angle = Column( Float )
    first_finger_offset = Column( Float )

class MultifingerTapResults( Base ):

    #Multifinger Tap results are defined here
    __tablename__ = 'multi_finger_tap_results'

    id = Column( Integer, primary_key = True )
    point_id = Column( Integer, ForeignKey('multi_finger_tap_test.id', ondelete='CASCADE') )
    point = relation( MultifingerTapTest, backref = backref('multi_finger_tap_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class MultifingerSwipeTest( Base ):

    #One-finger swipe test is defined here
    __tablename__ = 'multi_finger_swipe_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('multi_finger_swipe_test', order_by = id) )

    #Is measurement 2-, 3-, 4-, or 5-finger
    number_of_fingers = Column( Integer )

    #For straight lines, start and stop positions are defined
    start_x = Column( Float )
    start_y = Column( Float )
    end_x = Column( Float )
    end_y = Column( Float )
    separation_distance = Column( Float )
    separation_angle = Column( Float )
    first_finger_offset = Column( Float )

    #Is test zoom, pinch or swipe
    test_type = Column( String )


class MultifingerSwipeResults( Base ):

    #Multifinger pinch results are defined here
    __tablename__ = 'multi_finger_swipe_results'

    id = Column( Integer, primary_key = True )
    swipe_id = Column( Integer, ForeignKey('multi_finger_swipe_test.id', ondelete='CASCADE'), nullable=False )
    swipe = relation( MultifingerSwipeTest, backref = backref('multi_finger_swipe_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class GridAccuracyTest(Base):

    # Test is defined here
    __tablename__ = 'grid_accuracy_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('grid_accuracy_test', order_by = id) )

    # Robot tap position
    robot_x = Column( Float )
    robot_y = Column( Float )

    border_width = Column(Float)

    finger_name = Column(Text)
    finger_type = Column(Text) # Metal or soft
    finger_size = Column(Float)
    num_fingers = Column(Float)

    lift_off_distance = Column(Float)
    step_size = Column(Float)
    ground_status = Column(Text) # "ground" or "low_ground"
    noise_status = Column(Text)  # charger name
    display_background = Column(Text)
    touch_area = Column(Text) # "edge_area" or "center_area"
    contact_duration = Column(Float) # duration in ms


class GridAccuracyResults(Base):

    # Results are defined here
    __tablename__ = 'grid_accuracy_results'

    id = Column( Integer, primary_key = True )
    point_id = Column( Integer, ForeignKey('grid_accuracy_test' + '.id', ondelete='CASCADE'), nullable=False )
    point = relation( GridAccuracyTest, backref = backref('grid_accuracy_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class StationaryJitterStaticNoiseTest(Base):

    # Test is defined here
    __tablename__ = 'stationary_jitter_static_noise_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('stationary_jitter_static_noise_test', order_by = id) )

    # Robot tap position
    robot_x = Column( Float )
    robot_y = Column( Float )

    border_width = Column(Float)
    test_type = Column(Text)

    finger_name = Column(Text)
    finger_type = Column(Text) # Metal or soft
    finger_size = Column(Float)
    finger2_name = Column(Text)
    separation = Column(Float)

    lift_off_distance = Column(Float)
    step_size = Column(Float)
    ground_status = Column(Text) # "ground" or "low_ground"
    noise_status = Column(Text) # charger name
    display_background = Column(Text)
    touch_area = Column(Text) # "edge_area" or "center_area"
    contact_duration = Column(Float) # duration in ms
    number_of_fingers_on_screen = Column(Integer)


class StationaryJitterStaticNoiseResults(Base):

    # Results are defined here
    __tablename__ = 'stationary_jitter_static_noise_results'

    id = Column( Integer, primary_key = True )
    point_id = Column( Integer, ForeignKey('stationary_jitter_static_noise_test' + '.id', ondelete='CASCADE'), nullable=False )
    point = relation( StationaryJitterStaticNoiseTest, backref = backref('stationary_jitter_static_noise_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class Setting(Base):

    __tablename__ = 'settings'
    id = Column(String,primary_key = True)
    value = Column(Float,nullable=False)
    unit = Column(String)
    desc = Column(String)
    def __init__(self,id,value,unit,desc):
        self.id = id
        self.value = value
        self.unit = unit
        self.desc = desc

class TestResult(Base):
    __tablename__ = 'test_result'
    id = Column(Integer, primary_key = True)
    test_id = Column(Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('test_results') )
    result = Column(String)
    calculated = Column(DateTime)


# The global database singleton instance
db = None

""" Returns the global database instance """
# If there is an existing database given as config, let's use that one
# If not, a database with that name is created, if there is no config
# the last used datapath is used
def get_database():
    global db
    if db is None and database is None:
        db = ResultDatabase(getLastPath())
    elif db is None and database is not None:
        db = ResultDatabase(database)
    return db
