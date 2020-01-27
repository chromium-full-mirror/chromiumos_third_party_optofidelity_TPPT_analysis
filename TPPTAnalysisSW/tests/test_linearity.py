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
import threading
from genshi.template import MarkupTemplate
from sqlalchemy.orm import joinedload
from sqlalchemy import Column, DECIMAL, INTEGER, TIMESTAMP, DATETIME, VARCHAR, ForeignKey, BOOLEAN, func
from sqlalchemy.dialects.mysql import LONGTEXT

import numpy as np

from TPPTAnalysisSW.testbase import TestBase, testclasscreator, timestr_to_datetime
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.settings import settings
from TPPTAnalysisSW.utils import Timer
from TPPTAnalysisSW.info.version import Version
from TPPTAnalysisSW.sqluploader import Base
import TPPTAnalysisSW.measurementdb as measurementdb
import TPPTAnalysisSW.analyzers as analyzers
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.plot_factory as plot_factory
from TPPTAnalysisSW.analyzers import filter_points, float_for_db
from TPPTAnalysisSW import toolbox

import base64


ALLOWED_EVENTS = [0, 1, 2]  # going down, getting up, continous touch
TOUCH_DOWN = 0
CONTINUOUS_TOUCH = 2
TOUCH_UP = 1

def is_point_in_center(x, y, width, height, border_width, dut_svg = None, contour = None):
    """
    Check if point is in the center area of dut. If dut has svg form defined, please use
    precalculated contour for faster analysis
    :param x: point x coordinate
    :param y: point y coordinate
    :param width: dut width
    :param height: dut height
    :param border_width: width of the edge area
    :param dut_svg: toolbox.dut.SvgRegion object
    :param contour: contour calculated from the dut svg with toolbox
    :return: True if point is in the center area, false if not
    """
    # We might have only SvgRegion object but no precalculated region
    if dut_svg is not None and contour is None:
        return is_point_in_center_svg(x, y, border_width, dut_svg)
    elif dut_svg is not None and contour is not None:
        return is_point_in_center_contour(x, y, border_width, dut_svg, contour)
    else: # If there is no svg we assume the dut is square
        return is_point_in_center_square(x, y, width, height, border_width)

def is_point_in_center_svg(x, y, border_width, dut_svg):
    """
    Uses svg image through toolbox to define if point is inside center area
    :param x: point x coordinate
    :param y: point y coordinate
    :param border_width: width of the edge area
    :param dut_svg: toolbox.dut.SvgRegion object
    :return: True if point is in the center area, false if not
    """
    res = dut_svg.filter_points_str_region([[x, y]], 'test_region', margin=border_width)
    # If point is not in the center area filtering will return empty list
    if len(res) > 0:
        return True
    else:
        return False

def is_point_in_center_contour(x, y, border_width, dut_svg, contour):
    """
    Uses precalculated contour through toolbox to define if point is inside center area
    :param x: point x coordinate
    :param y: point y coordinate
    :param border_width: width of the edge area
    :param dut_svg: toolbox.SvgRegion object
    :param contour: precalculated contour
    :return: True if point is in the center area, false if not
    """
    # If point is not in the center area filtering will return empty list
    res = dut_svg.filter_points_contour([[x, y]], border_width, contour)
    if len(res) > 0:
        return True
    else:
        return False


def is_point_in_center_square(x, y, width, height, border_width):
    """
    Check if given point is center point within region [0, width] x [0, height]
    that has given border.
    """
    if x < border_width or x > width - border_width:
        return False

    if y < border_width or y > height - border_width:
        return False

    return True


def get_passed_failed_target_points(swipe_points, target_points):
    passfail_values = [analyzers.float_for_db(abs(p[1])) <= settings['max_avg_of_max_errors'] for p in swipe_points]

    passed = [target_points[i] for (i, t) in enumerate(passfail_values) if t]
    failed = [target_points[i] for (i, t) in enumerate(passfail_values) if not t]

    return passed, failed

class LinearitySummarySQL(Base):
    __tablename__ = 'touch_linearity_lower_sensitivity_moving_noise_summary'

    meta_id = Column(INTEGER, primary_key=True)
    test_id = Column(DECIMAL(10, 0))

    # "Pass-through" settings that are not needed for anything in the analysis
    time_test_start = Column(DATETIME)
    time_sequence_start = Column(DATETIME)
    time_sequence_end = Column(DATETIME)
    border_width = Column(DECIMAL(8,2))
    finger_name = Column(VARCHAR(40))
    finger_type = Column(VARCHAR(40))
    finger_size = Column(DECIMAL(8,2))
    step_size = Column(DECIMAL(8,2))
    display_background = Column(VARCHAR(40))

    test_type = Column(VARCHAR(40))
    lift_off_distance = Column(DECIMAL(8,2))
    swipe_speed = Column(DECIMAL(8,2))
    ground_status = Column(VARCHAR(40))
    noise_status = Column(VARCHAR(40))
    swipe_direction = Column(VARCHAR(40))
    log = Column(LONGTEXT)

    number_of_fingers = Column(DECIMAL(8,2))

    # Settings we need for analysis and that might still
    # also be passed through

    touch_area = Column(VARCHAR(40))

    # Results that are created here in analysis

    total_number_of_broken_lines = Column(DECIMAL(10,3))
    total_number_of_missing_swipes = Column(INTEGER)

    linearity_avg_of_error_avgs = Column(DECIMAL(10,3))
    linearity_total_stdev_error = Column(DECIMAL(10,3))
    linearity_avg_of_max_errors = Column(DECIMAL(10,3))
    linearity_max_of_max_errors = Column(DECIMAL(10,3))
    total_linearity_rms_error = Column(DECIMAL(10, 3))

    moving_jitter_avg_of_error_avgs = Column(DECIMAL(10,3))
    moving_jitter_total_stdev_error = Column(DECIMAL(10,3))
    moving_jitter_avg_of_max_errors = Column(DECIMAL(10,3))
    moving_jitter_max_of_max_errors = Column(DECIMAL(10,3))

    offset_avg_of_error_avgs = Column(DECIMAL(10,3))
    offset_total_stdev_error = Column(DECIMAL(10, 3))
    offset_avg_of_max_errors = Column(DECIMAL(10, 3))
    offset_max_of_max_errors = Column(DECIMAL(10, 3))
    total_offset_rms_error = Column(DECIMAL(10, 3))

    avg_of_avg_report_rate = Column(DECIMAL(8, 2))
    total_std_report_rate = Column(DECIMAL(8, 2))
    avg_of_min_report_rate = Column(DECIMAL(8, 2))
    min_of_min_report_rate = Column(DECIMAL(8, 2))

    successful_swipe_percentage = Column(DECIMAL(8, 2))

    # The time of database entry creation set by the database server
    created = Column(TIMESTAMP(), server_default=func.current_timestamp())



class LinearityResultsSQL(Base):
    __tablename__ = 'touch_linearity_lower_sensitivity_moving_noise_results'
    meta_id = Column(INTEGER, primary_key=True)
    test_meta_id = Column(INTEGER, ForeignKey('touch_linearity_lower_sensitivity_moving_noise_summary.meta_id', ondelete='CASCADE'), nullable=False)
    line_id = Column(INTEGER)

    linearity_mean_error = Column(DECIMAL(10,3))
    linearity_stdev_error = Column(DECIMAL(10,3))
    linearity_max_error = Column(DECIMAL(10,3))
    linearity_rms_mean_error = Column(DECIMAL(10,3))

    moving_jitter_mean_error = Column(DECIMAL(10,3))
    moving_jitter_stdev_error = Column(DECIMAL(10,3))
    moving_jitter_max_error = Column(DECIMAL(10,3))

    offset_mean_error = Column(DECIMAL(10,3))
    offset_stdev_error = Column(DECIMAL(10,3))
    offset_max_error = Column(DECIMAL(10,3))
    offset_rms_mean_error = Column(DECIMAL(10,3))

    line_broken = Column(BOOLEAN)
    number_of_fingers = Column(DECIMAL(8,2))

    avg_report_rate = Column(DECIMAL(8, 2))
    std_report_rate = Column(DECIMAL(8, 2))
    min_report_rate = Column(DECIMAL(8, 2))


class LinearityTest(TestBase):
    """ Contains one linearity test and, thus, a new instance is  created for each individual test"""

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(13)
    def create_testclass(*args, **kwargs):
        return LinearityTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new OneFingerSwipeTest class """
        super(LinearityTest, self).__init__(ddtest_row, *args, **kwargs)
        self.meta_id = None
        self.sql_summary_class = LinearitySummarySQL

        # These are used if dut has an svg file for boundaries
        self.dut_svg = None
        self.test_region_contour = None

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        results = self.read_test_results()

        return results['verdict']

    # Override to make necessary operations for clearing test results
    # Clearing the test result from the results table is done elsewhere
    def clearanalysis(self, *args, **kwargs):
        """ Clears analysis results """
        ImageFactory.delete_images(self.test_id)

    # Create the test report. Return the created HTML, or raise cherrypy.HTTPError
    def createreport(self, *args, **kwargs):

        self.clearanalysis()

        # Create common template parameters (including test_item dictionary, testsession dictionary, test_id, test_type_name etc)
        template_params = super(LinearityTest, self).create_common_templateparams(**kwargs)

        s = Timer()
        s.Time("START")

        results = self.read_test_results()

        s.Time("Results")

        template_params['test_parameters'] = (('Border width [mm]', results['border_width']),
                                             ('Finger name', results['finger_name']),
                                             ('Finger type', results['finger_type']),
                                             ('Finger size [mm]', results['finger_size']),
                                             ('Number of fingers', results['num_fingers']),
                                             ('Display background', results['display_background']),
                                             ('Step size [mm]', results['step_size']),
                                             ('Lift off distance [mm]', results['lift_off_distance']),
                                             ('Swipe speed [mm/s]', results['swipe_speed']),
                                             ('Ground status', results['ground_status']),
                                             ('Noise status', results['noise_status']),
                                             ('Touch area', results['touch_area']),
                                             ('Swipe direction', results['swipe_direction']))
        template_params['results'] = results
        template_params['figure'] = ImageFactory.create_image_name(self.test_id, "swipes")
        template_params['detailed_figure'] = ImageFactory.create_image_name(self.test_id, "swipes", "detailed")
        template_params['test_page'] = 'test_linearity.html'
        template_params['test_script'] = 'test_page_subplots.js'
        template_params['version'] = Version

        self.disable_upload_button_if_already_uploaded(template_params)

        template = MarkupTemplate(open("templates/test_configured_body.html"))
        stream = template.generate(**(template_params))
        s.Time("READY")

        # Start creating the preview image already - the call will probably come soon
        # NOTE: this is not necessary in summary tests
        if 'noimages' not in kwargs:
            threading.Thread(target = self.createpreviewimage, args = (results,)).start()

        return stream.render('xhtml'), results['verdict']

    def createpreviewimage(self, results):
        """ Creates a swipe preview image with the specified results """
        imagepath = ImageFactory.create_image_path(self.test_id, "swipes")
        dbsession = measurementdb.get_database().session()
        dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
        title = 'Preview: Linearity ' + self.dut['program']
        plot_factory.plot_swipes_on_target(imagepath, results, dutinfo, title=title)

    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'swipes':
            # See above: preview image is normally generated after the report creation
            dbsession = measurementdb.get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            pinfo = self.read_test_results(dbsession=dbsession, dutinfo=dutinfo)
            title = 'Preview: Linearity ' + self.dut['program']
            plot_factory.plot_swipes_on_target(imagepath, pinfo, dutinfo, *args, title=title, **kwargs)
        elif image_name == 'jittdtls':
            dbsession = measurementdb.get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_swipe_details(args[0], dbsession=dbsession, dutinfo=dutinfo)
            title = 'Preview: Linearity details ' + self.dut['program']
            plot_factory.plot_one_finger_swipe_with_linear_fit(imagepath, results, dutinfo, title=title, **kwargs)
        else:
            raise cherrypy.HTTPError(message = "No such image in the report")

        return None

    # This is only used in createimage, do not get mixed up with read test results that partially
    # does same things
    def read_swipe_details(self, swipe_id, dbsession=None, dutinfo=None):
        if dbsession is None:
            dbsession = measurementdb.get_database().session()
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(self.testsession['id'], dbsession)

        line = dbsession.query(measurementdb.LinearityTest).filter(measurementdb.LinearityTest.id == swipe_id). \
            order_by(measurementdb.LinearityTest.id). \
            options(joinedload('linearity_results')).first()

        panel_points = []

        dut_width = dutinfo.dimensions[0]
        dut_height = dutinfo.dimensions[1]

        touch_area = line.touch_area
        is_edge_area = (touch_area == "edge_area")
        border_width = line.border_width

        # If we have svg file for dut and have not yet defined the SvgRegion object
        # for dut we should do it here
        if self.dut_svg is None and dutinfo.svg_data is not None:
            try:
                self.dut_svg = toolbox.dut.SvgRegion()
                self.dut_svg.load_string(base64.b64decode(dutinfo.svg_data).decode('ascii'))
                # Pre-calculating the contour greatly speeds up the calculations
                # (then the contour is only calculated once)
                self.test_region_contour = self.dut_svg.region_str_to_contour('test_region')
            except:
                raise Exception('Failed to load dut svg file')

        for point in line.linearity_results:
            target_point = analyzers.panel_to_target_transform(dutinfo).transform((point.panel_x, point.panel_y))

            # If test area is center, all points go through. With edge as test area, one has to filter the center
            # points away
            x, y = target_point[0], target_point[1]
            if not is_edge_area or not is_point_in_center(x, y, dut_width, dut_height, border_width,
                                                          self.dut_svg, self.test_region_contour):
                panel_points.append((point.panel_x, point.panel_y))

        target_points = analyzers.panel_to_target(panel_points, dutinfo)
        line_start, line_end = analyzers.robot_to_target([(line.start_x, line.start_y), (line.end_x, line.end_y)],
                                                         dutinfo)
        swipe_points = analyzers.target_to_swipe(target_points, line_start, line_end)
        jitterinfo = analyzers.analyze_swipe_jitter(swipe_points, float(settings['jitter_mask']))
        linearity_results = analyzers.analyze_swipe_linearity(swipe_points)

        passed, failed = get_passed_failed_target_points(swipe_points, target_points)

        return {'passed_points': passed, 'failed_points': failed, 'swipe_points': swipe_points,
                'line_start': line_start, 'line_end': line_end, 'jitters': jitterinfo['jitters'],
                'linear_error': linearity_results['linear_error'], 'lin_error_max': linearity_results['lin_error_max'],
                'lin_error_rms': linearity_results['lin_error_rms'],
                'lin_error_avg': linearity_results['lin_error_avg']}


    def read_test_results(self, dutinfo = None, dbsession = None):
        s = Timer(2)
        if dbsession is None:
            dbsession = measurementdb.get_database().session()

        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        dbswipes = dbsession.query(measurementdb.LinearityTest).filter(measurementdb.LinearityTest.test_id==self.test_id).\
                                                                     options(joinedload('linearity_results')).\
                                                                     order_by(measurementdb.LinearityTest.id)

        dut_width = dutinfo.dimensions[0]
        dut_height = dutinfo.dimensions[1]

        # If we have svg file for dut and have not yet defined the SvgRegion object
        # for dut we should do it here
        if self.dut_svg is None and dutinfo.svg_data is not None:
            try:
                self.dut_svg = toolbox.dut.SvgRegion()
                self.dut_svg.load_string(base64.b64decode(dutinfo.svg_data).decode('ascii'))
                # Pre-calculating the contour greatly speeds up the calculations
                # (then the contour is only calculated once)
                self.test_region_contour = self.dut_svg.region_str_to_contour('test_region')
            except:
                raise Exception('Failed to load dut svg file')

        s.Time('DB')

        swipes = []
        # swipe_additions is used to store values from individual swipes that are not
        # included in the swipes (this is done not to break anything)
        swipe_additions = {}
        missing_swipes = []
        swipe_id = 1
        lines = []
        passed_points = []
        failed_points = []
        num_of_broken_lines = 0
        ghost_fingers = 0

        num_valid_lines = 0
        linearity_avg_of_error_avgs = None
        linearity_avg_of_max_errors = None
        linearity_max_of_max_errors = None
        fitted_y = []

        moving_jitter_avg_of_error_avgs = None
        moving_jitter_avg_of_max_errors = None
        moving_jitter_max_of_max_errors = None
        jitters = []

        offset_avg_of_error_avgs = None
        offset_avg_of_max_errors = None
        offset_max_of_max_errors = None
        signed_offsets = []

        avg_of_avg_report_rate = None
        avg_of_min_report_rate = None
        min_of_min_report_rate = None
        report_rates = []
        num_report_rates = 0

        num_swipes = len(list(dbswipes))

        touch_area = dbswipes[0].touch_area if num_swipes > 0 else ""
        is_edge_area = (touch_area == "edge_area")
        border_width = dbswipes[0].border_width if num_swipes > 0 else 0

        # Checking/collecting all the conditions that might change the pass/faill limits
        test_type = dbswipes[0].test_type if num_swipes > 0 else ""

        if num_swipes > 0 and len(dbswipes[0].noise_status) == 0:
            noise_inserted = False
        else:
            noise_inserted = True

        # Accepted fingers list define which fingers we consider in the analysis
        # as real fingers. All other fingers are ghost fingers
        num_fingers = int(dbswipes[0].num_fingers) if num_swipes > 0 else 1
        accepted_fingers = [i for i in range(num_fingers)]
        if num_fingers > 1: # tool is multifinger
            multifinger = True
        else:
            multifinger = False


        # Setting the report rate limits based on noise insertion
        # The limit is used for both single swipes and for total result
        if not noise_inserted:
            report_rate_limit = settings['min_report_rate']
        elif not multifinger:
            report_rate_limit = settings['min_report_rate_noise_inj_single']
        else:  # multifinger and noise inserted
            report_rate_limit = settings['min_report_rate_noise_inj_multi']

        if test_type == 'sensitivity_lower':
            # This will be typecasted to string after the value comparison is done
            max_broken_lines = settings['max_broken_lines']
        else:
            max_broken_lines = 'N/A'

        if test_type == 'noise_test_moving':
            # This will be typecasted to string after the value comparison is done
            max_ghost_fingers = settings['max_ghost_fingers']
        else:
            max_ghost_fingers = 'N/A'



        for swipe in dbswipes:
            assert(swipe.start_x is not None)
            assert(swipe.start_y is not None)
            assert(swipe.end_x is not None)
            assert(swipe.end_y is not None)

            finger_ids = []
            touch_events = []
            panel_points = []
            swipe_report_rates = []
            prev_timestamp = None
            line_broken = False
            ghost_finger = False

            # Get points between first touch down and last touch up.
            filtered_points = filter_points(swipe.linearity_results)

            for point in filtered_points:
                # we need to store all the finger_values that appear
                if point.finger_id not in finger_ids:
                    finger_ids.append(point.finger_id)
                # any other event that allowed will cause the line to be "broken"
                if point.event not in ALLOWED_EVENTS:
                    line_broken = True
                # We assume that the first finger(s) to touch the screen are the actual fingers and
                # other fingers are ghosts. The accepted fingers list is based on amount of fingers in tool
                if int(point.finger_id) in accepted_fingers and point.event in ALLOWED_EVENTS:
                    # these points go forward to analysis
                    target_point = analyzers.panel_to_target_transform(dutinfo).transform((point.panel_x, point.panel_y))

                    # If test area is center, all points go through. With edge as test area, one has to
                    # filter the center points away
                    x, y = target_point[0], target_point[1]
                    if not is_edge_area or not is_point_in_center(x, y, dut_width, dut_height, border_width,
                                                                  self.dut_svg, self.test_region_contour):
                        panel_points.append((point.panel_x, point.panel_y))
                        touch_events.append((point.id, point.event))  # we need to know the order of touch events

            # Compute delays between adjacent events. Finger ID and event type is ignored.
            for point in swipe.linearity_results:
                target_point = analyzers.panel_to_target_transform(dutinfo).transform((point.panel_x, point.panel_y))
                x, y = target_point[0], target_point[1]
                if is_point_in_center(x, y, dut_width, dut_height, border_width, self.dut_svg, self.test_region_contour):
                    point_area = "center_area"
                else:
                    point_area = "edge_area"

                # Only calculate report rate from points within the target area.
                if prev_timestamp is None or point_area != touch_area:
                    prev_timestamp = point.time
                # If adjacent times are the same for some reason, ignore it.
                elif point.time != prev_timestamp:
                    report_rate = 1000.0 / (point.time - prev_timestamp)
                    prev_timestamp = point.time

                    swipe_report_rates.append(report_rate)
                    report_rates.append(report_rate)

            min_report_rate = None
            avg_report_rate = None
            std_report_rate = None

            # if the whole swipe missed, there won't be any panel points
            if len(panel_points) >= 2:
                # it is assumed that touch events are read from database in order, so first
                # and last are removed and there should only be continuous touch events left
                if touch_events[0][1] != TOUCH_DOWN:
                    line_broken = True
                if touch_events[-1][1] != TOUCH_UP:
                    line_broken = True

                for event in touch_events[1:-1]:
                    if event[1] != CONTINUOUS_TOUCH:
                        line_broken = True

                # Line is not empty but is broken.
                # If line is empty i.e. len(panel_points) == 0 then can't be broken.
                if line_broken:
                    num_of_broken_lines += 1

                # If we have more than one finger id appearing in one swipe it means we have ghost finger
                if len(finger_ids) > 1:
                    ghost_fingers += 1
                    ghost_finger = True

            # Compute report rate measures for the swipe.
            if len(swipe_report_rates) > 0:
                # num_report_rates is used to compute the average values over each swipe.
                num_report_rates += 1
                min_report_rate = min(swipe_report_rates)
                avg_report_rate = np.average(swipe_report_rates)

                std_report_rate = np.std(swipe_report_rates)

                # Accumulate reporting rate values to later compute average values for the whole test.
                if avg_of_avg_report_rate is None: avg_of_avg_report_rate = 0.0
                avg_of_avg_report_rate += avg_report_rate

                if avg_of_min_report_rate is None: avg_of_min_report_rate = 0.0
                avg_of_min_report_rate += min_report_rate

                if min_of_min_report_rate is None:
                    min_of_min_report_rate = min_report_rate
                else:
                    min_of_min_report_rate = min(min_of_min_report_rate, min_report_rate)

            # Transform panel -> robot -> swipe
            target_points = analyzers.panel_to_target(panel_points, dutinfo)
            swipe_start, swipe_end = analyzers.robot_to_target([(swipe.start_x, swipe.start_y), (swipe.end_x, swipe.end_y)], dutinfo)
            lines.append((swipe_start, swipe_end))

            # Transform swipe points to frame where x-axis is the robot swipe line and y-axis is perpendicular to that.
            # Swipe points is a list of tuples (x, y).
            swipe_points = analyzers.target_to_swipe(target_points, swipe_start, swipe_end)

            swipe_linearity = analyzers.analyze_swipe_linearity(swipe_points)
            swipe_jitter = analyzers.analyze_swipe_jitter(swipe_points, float(settings['jitter_mask']))
            swipe_offset = analyzers.analyze_swipe_offset(swipe_points)

            # There needs to be at least 1 non-repeated point in jitter data for swipe to be valid.
            if len(panel_points) > 0 and len(swipe_jitter['jitters_no_none']) > 0:
                swipe_empty = False
                num_valid_lines += 1
            else:
                swipe_empty = True

            swipe_additions[swipe_id] = {'linearity_mean_error': float_for_db(swipe_linearity['lin_error_avg']),
                                         'linearity_stdev_error': float_for_db(swipe_linearity['lin_error_stdev']),
                                         'linearity_max_error': float_for_db(swipe_linearity['lin_error_max']),
                                         'linearity_rms_mean_error': float_for_db(swipe_linearity['lin_error_rms']),
                                         'moving_jitter_mean_error': float_for_db(swipe_jitter['jitter_avg']),
                                         'moving_jitter_stdev_error': float_for_db(swipe_jitter['jitter_stdev']),
                                         'moving_jitter_max_error': float_for_db(swipe_jitter['max_jitter']),
                                         'offset_mean_error': float_for_db(swipe_offset['offset_mean']),
                                         'offset_stdev_error': float_for_db(swipe_offset['offset_stdev']),
                                         'offset_max_error': float_for_db(swipe_offset['offset_max']),
                                         'offset_rms_mean_error': float_for_db(swipe_offset['offset_rms_mean']),
                                         'min_report_rate': float_for_db(min_report_rate),
                                         'avg_report_rate': float_for_db(avg_report_rate),
                                         'std_report_rate': float_for_db(std_report_rate),
                                         'line_broken': line_broken,
                                         'num_of_fingers': len(finger_ids), #ghost finger detection
                                         'ghost_finger_detected': ghost_finger,
                                         'swipe_empty': swipe_empty
                                        }

            # Accumulate linearity, jitter and offset values to later compute average values for the whole test.
            if not swipe_empty:
                assert isinstance(swipe_linearity['fitted_y'], list)
                fitted_y += swipe_linearity['fitted_y']

                assert isinstance(swipe_jitter['jitters_no_none'], list)
                jitters += swipe_jitter['jitters_no_none']

                signed_offsets += [point[1] for point in swipe_points]

                if linearity_avg_of_error_avgs is None: linearity_avg_of_error_avgs = 0.0
                linearity_avg_of_error_avgs += swipe_linearity['lin_error_avg']

                if linearity_avg_of_max_errors is None: linearity_avg_of_max_errors = 0.0
                linearity_avg_of_max_errors += swipe_linearity['lin_error_max']

                if linearity_max_of_max_errors is None: linearity_max_of_max_errors = 0.0
                linearity_max_of_max_errors = max(linearity_max_of_max_errors, swipe_linearity['lin_error_max'])

                if moving_jitter_avg_of_error_avgs is None: moving_jitter_avg_of_error_avgs = 0.0
                moving_jitter_avg_of_error_avgs += swipe_jitter['jitter_avg']

                if moving_jitter_avg_of_max_errors is None: moving_jitter_avg_of_max_errors = 0.0
                moving_jitter_avg_of_max_errors += swipe_jitter['max_jitter']

                if moving_jitter_max_of_max_errors is None: moving_jitter_max_of_max_errors = 0.0
                moving_jitter_max_of_max_errors = max(moving_jitter_max_of_max_errors, swipe_jitter['max_jitter'])

                if offset_avg_of_error_avgs is None: offset_avg_of_error_avgs = 0.0
                offset_avg_of_error_avgs += swipe_offset['offset_mean']

                if offset_avg_of_max_errors is None: offset_avg_of_max_errors = 0.0
                offset_avg_of_max_errors += swipe_offset['offset_max']

                if offset_max_of_max_errors is None: offset_max_of_max_errors = 0.0
                offset_max_of_max_errors = max(offset_max_of_max_errors, swipe_offset['offset_max'])

            passed, failed = get_passed_failed_target_points(swipe_points, target_points)
            passed_points.extend(passed)
            failed_points.extend(failed)

            # Swipe is missing if there are no points in it.
            if len(swipe_points) == 0:
                missing_swipes.append(swipe.id)

            # Verdict of individual swipe.
            swipe_verdict = "N/A"

            # Determine individual swipe linearity verdict. This affects swipe verdict.
            swipe_max_linearity = None
            if len(swipe_points) > 0:
                swipe_max_linearity = analyzers.float_for_db(swipe_linearity['lin_error_max'])
                swipe_verdict = "Fail" if swipe_max_linearity > settings['max_avg_of_max_errors'] else "Pass"

            # Determine individual swipe offset verdict.
            swipe_max_offset = None
            if len(swipe_points) > 0:
                swipe_max_offset = analyzers.float_for_db(swipe_offset['offset_max'])

            # Determine individual swipe jitter verdict.
            swipe_max_jitter = None
            if len(swipe_points) > 0:
                swipe_max_jitter = analyzers.float_for_db(swipe_jitter['max_jitter'])


            # Report rate affects swipe verdict.
            swipe_min_report_rate = None
            if min_report_rate is not None:
                swipe_min_report_rate = analyzers.float_for_db(min_report_rate)
                if swipe_verdict != "Fail":
                    swipe_verdict = "Pass" if min_report_rate >= report_rate_limit else "Fail"

            # Broken line makes swipe fail.
            if line_broken:
                swipe_verdict = "Fail"

            swipes.append({
                "id": swipe_id,
                "max_linearity": swipe_max_linearity,
                "max_jitter": swipe_max_jitter,
                "max_offset": swipe_max_offset,
                "min_report_rate": swipe_min_report_rate,
                "verdict": swipe_verdict,
                "image_name": ImageFactory.create_image_name(self.test_id, "jittdtls", str(swipe.id))
            })
            swipe_id += 1

        s.Time('Analysis')

        total_std_report_rate = None

        # Compute average of report rate from values accumulated from individual swipes.
        if num_report_rates > 0:
            avg_of_avg_report_rate = avg_of_avg_report_rate / num_report_rates
            avg_of_min_report_rate = avg_of_min_report_rate / num_report_rates

        if len(report_rates) > 0:
            total_std_report_rate = np.std(report_rates)

        # Compute total averages of linearity, jitter and offset from values accumulated from individual swipes.
        if num_valid_lines > 0:
            if linearity_avg_of_error_avgs is not None:
                linearity_avg_of_error_avgs = linearity_avg_of_error_avgs / num_valid_lines

            if linearity_avg_of_max_errors is not None:
                linearity_avg_of_max_errors = linearity_avg_of_max_errors / num_valid_lines

            if moving_jitter_avg_of_error_avgs is not None:
                moving_jitter_avg_of_error_avgs = moving_jitter_avg_of_error_avgs / num_valid_lines

            if moving_jitter_avg_of_max_errors is not None:
                moving_jitter_avg_of_max_errors = moving_jitter_avg_of_max_errors / num_valid_lines

            if offset_avg_of_error_avgs is not None:
                offset_avg_of_error_avgs = offset_avg_of_error_avgs / num_valid_lines

            if offset_avg_of_max_errors is not None:
                offset_avg_of_max_errors = offset_avg_of_max_errors / num_valid_lines

        linearity_total_stdev_error = None
        total_linearity_rms_error = None
        moving_jitter_total_stdev_error = None
        offset_total_stdev_error = None
        total_offset_rms_error = None

        if len(fitted_y) > 0:
            linearity_total_stdev_error = np.std(fitted_y, ddof=1)
            total_linearity_rms_error = np.sqrt(np.mean(np.power(fitted_y, 2)))

        if len(jitters) > 0:
            moving_jitter_total_stdev_error = np.sqrt(np.mean(np.power(jitters, 2)))

        if len(signed_offsets) > 0:
            offset_total_stdev_error = np.std(signed_offsets, ddof=1)
            total_offset_rms_error = np.sqrt(np.mean(np.power(signed_offsets, 2)))

        missing_count = len(missing_swipes)

        # Determine total test case verdicts. Note that some verdicts can be "N/A" and these should not affect total verdict.
        verdict = "N/A"

        # Linearity verdict for average of maxima affects the total test case verdict
        linearity_max_verdict = "N/A"
        if linearity_avg_of_max_errors is not None:
            if linearity_avg_of_max_errors <= settings["max_avg_of_max_errors"]:
                linearity_max_verdict = "Pass"
                if verdict != "Fail": verdict = "Pass"
            else:
                linearity_max_verdict = "Fail"
                verdict = "Fail"

        # Linearity total rms verdict affects the total test case verdict
        linearity_rms_verdict = "N/A"
        if total_linearity_rms_error is not None:
            if total_linearity_rms_error <= settings["max_rms_error"]:
                linearity_rms_verdict = "Pass"
                if verdict != "Fail": verdict = "Pass"
            else:
                linearity_rms_verdict = "Fail"
                verdict = "Fail"

        # Report rate affects the total test case verdict and report rate
        # limit depends on test conditions
        report_rate_verdict = "N/A"
        if avg_of_min_report_rate is not None:
            if avg_of_min_report_rate >= report_rate_limit:
                report_rate_verdict = "Pass"
                if verdict != "Fail": verdict = "Pass"
            else:
                report_rate_verdict = "Fail"
                verdict = "Fail"

        # Broken lines affect the total test case verdict in the sensitivity (lower) test case
        broken_lines_verdict = 'Pass'
        if test_type == 'sensitivity_lower':
            if num_of_broken_lines != max_broken_lines:
                broken_lines_verdict = "Pass"
                if verdict != "Fail": verdict = "Pass"
            else:
                broken_lines_verdict = "Fail"
                verdict = "Fail"
            max_broken_lines = str(max_broken_lines)

        # Broken lines affect the total test case verdict in the noise test (moving) test case
        ghost_fingers_verdict = "Pass"
        if test_type == 'noise_test_moving':
            if ghost_fingers <= max_ghost_fingers:
                ghost_fingers_verdict = "Pass"
                if verdict != "Fail": verdict = "Pass"
            else:
                ghost_fingers_verdict = "Fail"
                verdict = "Fail"
            max_ghost_fingers = str(max_ghost_fingers)


        if len(swipes) > 0:
            # Successful swipes are ones that are not missing nor broken. Not that missing line is not broken.
            successful_swipe_percentage = 100.0 * (len(swipes) - missing_count - num_of_broken_lines) / len(swipes)
            # Missing swipes are the one that are completely lost
            missing_swipe_percentage = 100*(missing_count/len(swipes))
        else:
            successful_swipe_percentage = 0.0
            missing_swipe_percentage = 100

        if missing_swipe_percentage <= settings['max_missing_swipes']:
            missing_swipes_verdict = "Pass"
        else:
            missing_swipes_verdict = "Fail"

        results = {'verdict': verdict,
                   'linearity_max_verdict': linearity_max_verdict,
                   'linearity_rms_verdict': linearity_rms_verdict,
                   'report_rate_verdict': report_rate_verdict,
                   'report_rate_limit': report_rate_limit,
                   'missing_swipes_verdict': missing_swipes_verdict,
                   'ghost_fingers_verdict': ghost_fingers_verdict,
                   'max_ghost_fingers': max_ghost_fingers,
                   'broken_lines_verdict': broken_lines_verdict,
                   'swipes': swipes,
                   'swipe_additions': swipe_additions,
                   'swipe_count': len(swipes),
                   'missing_swipes': missing_swipes,
                   'missing_swipes_percentage': missing_swipe_percentage,
                   'missing_count': missing_count,
                   'lines': lines,
                   'num_of_broken_lines': num_of_broken_lines,
                   'max_broken_lines': max_broken_lines,
                   'num_of_ghost_fingers': ghost_fingers,
                   'passed_points': passed_points,
                   'failed_points': failed_points,
                   'linearity_avg_of_error_avgs': float_for_db(linearity_avg_of_error_avgs),
                   'linearity_avg_of_max_errors': float_for_db(linearity_avg_of_max_errors),
                   'linearity_max_of_max_errors': float_for_db(linearity_max_of_max_errors),
                   'linearity_total_stdev_error': float_for_db(linearity_total_stdev_error),
                   'total_linearity_rms_error': float_for_db(total_linearity_rms_error),
                   'moving_jitter_avg_of_error_avgs': float_for_db(moving_jitter_avg_of_error_avgs),
                   'moving_jitter_avg_of_max_errors': float_for_db(moving_jitter_avg_of_max_errors),
                   'moving_jitter_max_of_max_errors': float_for_db(moving_jitter_max_of_max_errors),
                   'moving_jitter_total_stdev_error': float_for_db(moving_jitter_total_stdev_error),
                   'offset_avg_of_error_avgs': float_for_db(offset_avg_of_error_avgs),
                   'offset_avg_of_max_errors': float_for_db(offset_avg_of_max_errors),
                   'offset_max_of_max_errors': float_for_db(offset_max_of_max_errors),
                   'offset_total_stdev_error': float_for_db(offset_total_stdev_error),
                   'total_offset_rms_error': float_for_db(total_offset_rms_error),
                   'avg_of_avg_report_rate': float_for_db(avg_of_avg_report_rate),
                   'avg_of_min_report_rate': float_for_db(avg_of_min_report_rate),
                   'min_of_min_report_rate': float_for_db(min_of_min_report_rate),
                   'total_std_report_rate': float_for_db(total_std_report_rate),
                   'successful_swipe_percentage': successful_swipe_percentage,
                   'finger_name': dbswipes[0].finger_name if num_swipes > 0 else "",
                   'finger_type': dbswipes[0].finger_type if num_swipes > 0 else "",
                   'finger_size': dbswipes[0].finger_size if num_swipes > 0 else 0,
                   'num_fingers': num_fingers,
                   'step_size': dbswipes[0].step_size if num_swipes > 0 else 0,
                   'border_width': dbswipes[0].border_width if num_swipes > 0 else 0,
                   'display_background': dbswipes[0].display_background if num_swipes > 0 else "",
                   'lift_off_distance': dbswipes[0].lift_off_distance if num_swipes > 0 else 0,
                   'swipe_speed': dbswipes[0].swipe_speed if num_swipes > 0 else 0,
                   'ground_status': dbswipes[0].ground_status if num_swipes > 0 else "",
                   'noise_status': dbswipes[0].noise_status if num_swipes > 0 else "",
                   'swipe_direction': dbswipes[0].swipe_direction if num_swipes > 0 else "",
                   'touch_area': dbswipes[0].touch_area if num_swipes > 0 else "",
                   'test_type': test_type
                  }

        return results

    def upload_sql_data(self, session):
        # Add test summary to database
        test_results = self.read_test_results()
        linearitysummary = LinearitySummarySQL()
        linearitysummary.test_id = self.test_id

        test_item = self.get_test_item()
        test_session = self.get_test_session()

        linearitysummary.time_test_start = timestr_to_datetime(test_item.starttime)
        linearitysummary.time_sequence_start = timestr_to_datetime(test_session.starttime)

        # End time is None if sequence was not completed.
        if test_session.endtime is not None:
            linearitysummary.time_sequence_end = timestr_to_datetime(test_session.endtime)

        linearitysummary.finger_name = test_results["finger_name"]
        linearitysummary.finger_type = test_results["finger_type"]
        linearitysummary.finger_size = test_results["finger_size"]
        linearitysummary.number_of_fingers = test_results["num_fingers"]
        linearitysummary.step_size = test_results["step_size"]
        linearitysummary.border_width = test_results["border_width"]
        linearitysummary.display_background = test_results["display_background"]
        linearitysummary.lift_off_distance = test_results["lift_off_distance"]
        linearitysummary.swipe_speed = test_results["swipe_speed"]
        linearitysummary.ground_status = test_results["ground_status"]
        linearitysummary.noise_status = test_results["noise_status"]
        linearitysummary.swipe_direction = test_results["swipe_direction"]
        linearitysummary.touch_area = test_results["touch_area"]
        linearitysummary.log = self.test_item['kmsg_log'] # The test_item comes form Testbase
        linearitysummary.test_type = test_results['test_type']

        linearitysummary.total_number_of_broken_lines = test_results['num_of_broken_lines']
        linearitysummary.total_number_of_missing_swipes = test_results['missing_count']

        linearitysummary.linearity_avg_of_error_avgs = test_results['linearity_avg_of_error_avgs']
        linearitysummary.linearity_avg_of_max_errors = test_results['linearity_avg_of_max_errors']
        linearitysummary.linearity_max_of_max_errors = test_results['linearity_max_of_max_errors']
        linearitysummary.linearity_total_stdev_error = test_results['linearity_total_stdev_error']
        linearitysummary.total_linearity_rms_error = test_results['total_linearity_rms_error']

        linearitysummary.moving_jitter_avg_of_error_avgs = test_results['moving_jitter_avg_of_error_avgs']
        linearitysummary.moving_jitter_avg_of_max_errors = test_results['moving_jitter_avg_of_max_errors']
        linearitysummary.moving_jitter_max_of_max_errors = test_results['moving_jitter_max_of_max_errors']
        linearitysummary.moving_jitter_total_stdev_error = test_results['moving_jitter_total_stdev_error']

        linearitysummary.offset_avg_of_error_avgs = test_results['offset_avg_of_error_avgs']
        linearitysummary.offset_avg_of_max_errors = test_results['offset_avg_of_max_errors']
        linearitysummary.offset_max_of_max_errors = test_results['offset_max_of_max_errors']
        linearitysummary.offset_total_stdev_error = test_results['offset_total_stdev_error']
        linearitysummary.total_offset_rms_error = test_results['total_offset_rms_error']

        linearitysummary.avg_of_avg_report_rate = test_results['avg_of_avg_report_rate']
        linearitysummary.avg_of_min_report_rate = test_results['avg_of_min_report_rate']
        linearitysummary.min_of_min_report_rate = test_results['min_of_min_report_rate']
        linearitysummary.total_std_report_rate = test_results['total_std_report_rate']

        linearitysummary.successful_swipe_percentage = test_results['successful_swipe_percentage']

        session.add(linearitysummary)
        session.commit()

        # Add individual swipes to database (NOTE: test meta_id is only created when
        # the test summary is added to database)
        test_meta_id = linearitysummary.meta_id
        for swipe in test_results["swipes"]:
            # Reading values from swipe list
            swipe_id = int(swipe["id"])

            # metadata
            linearityresults = LinearityResultsSQL()
            linearityresults.test_meta_id = test_meta_id
            linearityresults.line_id = swipe_id

            swipe_additions = test_results['swipe_additions'][swipe_id]

            linearityresults.linearity_mean_error = swipe_additions['linearity_mean_error']
            linearityresults.linearity_stdev_error = swipe_additions['linearity_stdev_error']
            linearityresults.linearity_max_error = swipe_additions['linearity_max_error']
            linearityresults.linearity_rms_mean_error = swipe_additions['linearity_rms_mean_error']

            linearityresults.moving_jitter_mean_error = swipe_additions['moving_jitter_mean_error']
            linearityresults.moving_jitter_stdev_error = swipe_additions['moving_jitter_stdev_error']
            linearityresults.moving_jitter_max_error = swipe_additions['moving_jitter_max_error']

            linearityresults.offset_mean_error = swipe_additions['offset_mean_error']
            linearityresults.offset_stdev_error = swipe_additions['offset_stdev_error']
            linearityresults.offset_max_error = swipe_additions['offset_max_error']
            linearityresults.offset_rms_mean_error = swipe_additions['offset_rms_mean_error']

            linearityresults.avg_report_rate = swipe_additions['avg_report_rate']
            linearityresults.std_report_rate = swipe_additions['std_report_rate']
            linearityresults.min_report_rate = swipe_additions['min_report_rate']

            linearityresults.line_broken = swipe_additions['line_broken']
            linearityresults.number_of_fingers = swipe_additions['num_of_fingers']

            session.add(linearityresults)
            session.commit()