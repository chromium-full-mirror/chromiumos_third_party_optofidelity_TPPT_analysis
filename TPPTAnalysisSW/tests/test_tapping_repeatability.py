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
from math import sqrt, isnan

import cherrypy
import numpy as np
from genshi.template import MarkupTemplate
from sqlalchemy import Column, DECIMAL, INTEGER, VARCHAR, ForeignKey, DATETIME, TIMESTAMP, func
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import joinedload

import TPPTAnalysisSW.analyzers as analyzers
import TPPTAnalysisSW.measurementdb as db
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.plotinfo as plotinfo
from TPPTAnalysisSW.sqluploader import Base
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.info.version import Version
from TPPTAnalysisSW.measurementdb import get_database, OneFingerTappingRepeatabilityTest
from TPPTAnalysisSW.settings import settings
from TPPTAnalysisSW.testbase import TestBase, testclasscreator, timestr_to_datetime
from TPPTAnalysisSW.utils import Timer


class TappingRepeatabilitySummarySQL(Base):
    __tablename__ = 'touch_tapping_repeatability_summary'

    meta_id = Column(INTEGER, primary_key=True)
    time_test_start = Column(DATETIME)
    test_id = Column(DECIMAL(10, 3))
    time_sequence_start = Column(DATETIME)
    time_sequence_end = Column(DATETIME)

    border_width = Column(DECIMAL(8, 2))
    finger_name = Column(VARCHAR(40))
    finger_type = Column(VARCHAR(40))
    finger_size = Column(DECIMAL(8,2))
    display_background = Column(VARCHAR(40))

    number_of_random_locations_center = Column(DECIMAL(8, 2))
    number_of_random_locations_edge = Column(DECIMAL(8, 2))
    number_of_random_locations_corner = Column(DECIMAL(8, 2))
    number_of_taps_at_each_location = Column(DECIMAL(8, 2))

    lift_off_distance = Column(DECIMAL(8, 2))
    ground_status = Column(VARCHAR(40))
    noise_status = Column(VARCHAR(40))
    touch_area = Column(VARCHAR(40))
    log = Column(LONGTEXT)


    touch_direction = Column(VARCHAR(40))

    tapping_repeatability_avg_of_error_avgs = Column(DECIMAL(16, 3))
    tapping_repeatability_total_stdev_error = Column(DECIMAL(16, 3))
    tapping_repeatability_avg_of_max_errors = Column(DECIMAL(16, 3))
    tapping_repeatability_max_of_max_errors = Column(DECIMAL(16, 3))

    total_number_of_missing_points = Column(INTEGER)

    # The time of database entry creation set by the database server
    created = Column(TIMESTAMP(), server_default=func.current_timestamp())


class TappingRepeatabilityResultsSQL(Base):
    __tablename__ = 'touch_tapping_repeatability_results'
    meta_id = Column(INTEGER, primary_key=True)
    test_meta_id = Column(INTEGER, ForeignKey('touch_tapping_repeatability_summary.meta_id', ondelete='CASCADE'),
                          nullable=False)
    point_id = Column(INTEGER)
    touch_direction = Column(VARCHAR(40))

    avg_tapping_repeatability = Column(DECIMAL(10, 3))
    stdev_tapping_repeatability = Column(DECIMAL(10, 3))
    max_tapping_repeatability = Column(DECIMAL(10, 3))

    number_of_missing_points = Column(INTEGER)


class TappingRepeatabilityTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(17)
    def create_testclass(*args, **kwargs):
        return TappingRepeatabilityTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name),
    # and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new TappingRepeatabilityTest class """
        super(TappingRepeatabilityTest, self).__init__(ddtest_row, *args, **kwargs)

        # Even though one could collect all this data from many different sources
        # for clarity it is better to put everything in one dict (so that nothing breaks)
        self.point_db_data = {}
        self.point_errors_down = []
        self.point_errors_up = []
        self.results = None
        self.dut_info = None
        self.sql_summary_class = TappingRepeatabilitySummarySQL

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        verdict = "Fail"
        self.results = self.read_test_results()

        max_allowed_error_pen_down, max_allowed_error_pen_lift = get_maximum_errors(self.results['touch_area'])

        up_verdict = True if not isnan(self.results['avg_of_max_up_repeatability_error']) and \
            self.results['avg_of_max_up_repeatability_error'] <= max_allowed_error_pen_lift else False

        down_verdict = True if not isnan(self.results['avg_of_max_down_repeatability_error']) and \
            self.results['avg_of_max_down_repeatability_error'] <= max_allowed_error_pen_down else False

        if up_verdict and down_verdict:
            verdict = "Pass"

        return verdict

    # Override to make necessary operations for clearing test results
    # Clearing the test result from the results table is done elsewhere
    def clearanalysis(self, *args, **kwargs):
        """ Clears analysis results """
        ImageFactory.delete_images(self.test_id)

    # Create the test report. Return the created HTML, or raise cherrypy.HTTPError
    def createreport(self, *args, **kwargs):

        t = Timer(1)

        self.clearanalysis()

        # Create common template parameters,
        # including test_item dictionary, testsession dictionary, test_id, test_type_name etc
        template_params = super(TappingRepeatabilityTest, self).create_common_templateparams(**kwargs)
        verdict = "Pass"
        self.results = self.read_test_results()

        template_params['touch_area'] = self.results['touch_area']
        test_parameters = self.results['test_parameters']

        # We need to use here embedded list (instead of dict) to be able to decide the order of appearance
        template_params['test_parameters'] = (('Border Width [mm]', test_parameters['border_width']),
                                              ('Finger Name', test_parameters['finger_name']),
                                              ('Display Background', test_parameters['display_background']),
                                              ('Number of taps at each location', test_parameters[
                                                  'number_of_taps_at_each_location']),
                                              ('Lift off distance [mm]', test_parameters['lift_off_distance']),
                                              ('Ground status', test_parameters['ground_status']),
                                              ('Touch area', self.results['touch_area']),
                                              ('Noise status', test_parameters['noise_status']))

        if self.results['touch_area'] == 'center_area':
            template_params['test_parameters'] = template_params['test_parameters'] + \
                                                 (('Number of random locations',
                                                   test_parameters['number_of_random_locations_center']),)
        elif self.results['touch_area'] == 'edge_area':
            template_params['test_parameters'] = template_params['test_parameters'] + \
                                                 (('Number of random locations, edge',
                                                   test_parameters['number_of_random_locations_edge']),)
        elif self.results['touch_area'] == 'corner_area':
            template_params['test_parameters'] = template_params['test_parameters'] + \
                                                 (('Number of random locations, corner',
                                                   test_parameters['number_of_random_locations_corner']),)
        else:
            raise Exception('Invalid touch area "' + self.results['touch_area'] + '"')

        template_params['max_allowed_error_pen_down'], template_params[
            'max_allowed_error_pen_lift'] = get_maximum_errors(self.results['touch_area'])

        t.Time("Results")
        # Add the image name and parameters to the report
        template_params['figure'] = ImageFactory.create_image_name(self.test_id, 'rept')
        template_params['detailed_figure'] = ImageFactory.create_image_name(self.test_id, 'rept', 'detailed')

        template_params['max_down_repeatability_error'] = self.results['max_down_repeatability_error']
        template_params['avg_of_max_down_repeatability_error'] = self.results['avg_of_max_down_repeatability_error']
        template_params['avg_down_repeatability_error'] = self.results['avg_down_repeatability_error']
        template_params['std_dev_down_repeatability_error'] = self.results['stdev_down_repeatability_error']
        template_params['verdict_down'] = 'Pass' if not isnan(self.results['avg_of_max_down_repeatability_error']) and \
                                                    self.results['avg_of_max_down_repeatability_error'] <= template_params[
                                                        'max_allowed_error_pen_down'] else 'Fail'

        template_params['max_lift_repeatability_error'] = self.results['max_up_repeatability_error']
        template_params['avg_of_max_lift_repeatability_error'] = self.results['avg_of_max_up_repeatability_error']
        template_params['avg_lift_repeatability_error'] = self.results['avg_up_repeatability_error']
        template_params['std_dev_lift_repeatability_error'] = self.results['stdev_up_repeatability_error']
        template_params['verdict_lift'] = 'Pass' if not isnan(self.results['avg_of_max_up_repeatability_error']) and \
                                                    self.results['avg_of_max_up_repeatability_error'] <= template_params[
                                                        'max_allowed_error_pen_lift'] else 'Fail'

        template_params['num_missing_total'] = self.results['num_missing_total']
        template_params['num_points_total'] = self.results['num_points_total']

        template_params['missing_point_percentage'] = self.results['missing_point_percentage']
        template_params['missing_point_verdict'] = self.results['missing_point_verdict']
        template_params['maxmissing_in_percentage'] = settings['repeatability_missing_points']

        template_params['test_page'] = 'test_tapping_repeatability.html'
        template_params['test_script'] = 'test_page_subplots.js'
        template_params['version'] = Version

        template_params['repeatability_errors_down'] = self.results['repeatability_errors_down']

        subfigures = [None]  # Use one-based indexing
        for point_errors in self.results['repeatability_errors_down']:
            subfigures.append(ImageFactory.create_image_name(self.test_id, "repinfo_down", str(point_errors[4])))
        template_params['pointPlots_down'] = subfigures

        template_params['repeatability_errors_lift'] = self.results['repeatability_errors_up']

        subfigures = [None]  # Use one-based indexing
        for point_errors in self.results['repeatability_errors_up']:
            subfigures.append(ImageFactory.create_image_name(self.test_id, "repinfo_lift", str(point_errors[4])))
        template_params['pointPlots_lift'] = subfigures

        self.disable_upload_button_if_already_uploaded(template_params)

        t.Time("Params")

        template = MarkupTemplate(open("templates/test_configured_body.html"))
        stream = template.generate(**template_params)
        t.Time("Markup")

        if template_params['verdict_down'] == 'Fail' or template_params['verdict_lift'] == 'Fail':
            verdict = "Fail"

        return stream.render('xhtml'), verdict

    # Create images for the report.
    # If the function returns a value, it is used as the new image name (without image path)
    def createimage(self, imagepath, image_name, *args, **kwargs):
        if image_name == 'rept':
            # Overview image
            t = Timer(1)
            results = self.results

            if self.dut_info is None:
                self.dut_info = plotinfo.TestDUTInfo(testdut_id=self.dut['id'])

            t.Time("DB")
            title = 'Preview: One Finger Tapping Repeatability ' + self.dut['program']
            plot_factory.plot_tapping_passfail_labels_on_target(imagepath, results, self.dut_info, *args, title=title,
                                                                **kwargs)
            t.Time("Image")
        elif image_name == 'repinfo':
            # Individual point image
            t = Timer(1)
            point_id = int(args[1])
            # Check if doing pen down or pen lift-off details
            down = args[0] == 'down'
            results = self.read_point_details(point_id, pen_down=down)
            t.Time("DB")
            plot_factory.plot_tapping_repeatability_details(imagepath, results, *args, **kwargs)
            t.Time("Image")
        else:
            raise cherrypy.HTTPError(message="No such image in the report")

        return None

    def read_test_results(self, dutinfo=None):
        dbsession = get_database().session()

        if dutinfo is None:
            self.dut_info = plotinfo.TestDUTInfo(testdut_id=self.dut['id'])
        else:
            self.dut_info = dutinfo

        repeatability_test_points = dbsession.query(db.OneFingerTappingRepeatabilityTest) \
                         .filter(db.OneFingerTappingRepeatabilityTest.test_id == self.test_id) \
                         .options(joinedload(db.OneFingerTappingRepeatabilityTest.one_finger_tapping_repeatability_results)) \
                         .order_by(db.OneFingerTappingRepeatabilityTest.id) \
                         .all()

        num_test_points = len(list(repeatability_test_points))

        number_of_taps_at_each_location = repeatability_test_points[0].number_of_taps_at_each_location if num_test_points > 0 else 0

        # Some information just needs to be passed through the analyses
        test_parameters = {'border_width': repeatability_test_points[0].border_width if num_test_points > 0 else 0,
                           'finger_name': repeatability_test_points[0].finger_name if num_test_points > 0 else "",
                           'finger_type': repeatability_test_points[0].finger_type if num_test_points > 0 else "",
                           'finger_size': repeatability_test_points[0].finger_size if num_test_points > 0 else 0,
                           'display_background': repeatability_test_points[0].display_background if num_test_points > 0 else "",
                           'number_of_random_locations_center': repeatability_test_points[0].number_of_random_locations_center if num_test_points > 0 else 0,
                           'number_of_random_locations_edge': repeatability_test_points[0].number_of_random_locations_edge if num_test_points > 0 else 0,
                           'number_of_random_locations_corner': repeatability_test_points[0].number_of_random_locations_corner if num_test_points > 0 else 0,
                           'number_of_taps_at_each_location': number_of_taps_at_each_location,
                           'lift_off_distance': repeatability_test_points[0].lift_off_distance if num_test_points > 0 else 0,
                           'ground_status': repeatability_test_points[0].ground_status if num_test_points > 0 else "",
                           'noise_status': repeatability_test_points[0].noise_status if num_test_points > 0 else ""
                           }

        # Group the results by the point_id for easier handling
        # At the same time add a running point id as the first member of the array
        results = {}
        point_counter = 0

        num_missing_touch_down_total = 0
        num_missing_touch_up_total = 0

        for point in repeatability_test_points:
            # Collecting all the data per tap in dictionary (since there are multiple taps per point)
            point_counter += 1
            point_number = point.point_number
            results_per_tap = {}

            # Find touch down or touch up events from recorded event stream.
            filtered_points = analyzers.filter_points(point.one_finger_tapping_repeatability_results)

            for touch_data in filtered_points:
                if touch_data.tap_id not in results_per_tap:
                    results_per_tap[touch_data.tap_id] = [touch_data]
                else:
                    results_per_tap[touch_data.tap_id].append(touch_data)

            results[point_number] = {'robot_x': point.robot_x,
                                     'robot_y': point.robot_y,
                                     'taps': {}}
            for tap_id, touch_data in results_per_tap.items():
                touch_down = None
                touch_up = None

                # Make sure first touch event is "touch down".
                if len(touch_data) > 0 and touch_data[0].event == 0:
                    touch_down = (touch_data[0].panel_x, touch_data[0].panel_y)

                # Make sure last touch event is "touch up".
                if len(touch_data) > 0 and touch_data[-1].event == 1:
                    touch_up = (touch_data[-1].panel_x, touch_data[-1].panel_y)

                down_up_per_tap = {'touch_down': touch_down,
                                   'touch_up': touch_up}

                results[point_number]['taps'][tap_id] = down_up_per_tap

        verdicts_down = [None] * point_counter
        verdicts_up = [None] * point_counter
        point_numbers = [None] * point_counter
        passed_points = []
        failed_points = []
        data_for_drawings = {}

        down_accuracy_errors = [0.0] * point_counter
        up_accuracy_errors = [0.0] * point_counter

        for point_number, data in results.items():
            x_coordinates_down = []
            y_coordinates_down = []
            x_coordinates_up = []
            y_coordinates_up = []
            point_id = point_number - 1  # point_number starts from 1

            # Initially set the reference point to be the robot point
            reference_x_down = data['robot_x']
            reference_y_down = data['robot_y']
            reference_x_up = data['robot_x']
            reference_y_up = data['robot_y']

            data_for_drawings[str(point_number)] = {'reference_point_down': (reference_x_down, reference_y_down),
                                                    'reference_point_up': (reference_x_up, reference_y_up),
                                                    'touch_down': [],
                                                    'touch_up': []}

            # Number of taps reported by device for current location.
            num_touch_down = 0
            num_touch_up = 0

            for tap, coords in data['taps'].items():
                touch_down = coords['touch_down']
                touch_up = coords['touch_up']

                if touch_down is not None:
                    point_down = analyzers.panel_to_target((touch_down[0], touch_down[1]), self.dut_info)
                    x_coordinates_down.append(point_down[0])
                    y_coordinates_down.append(point_down[1])
                    data_for_drawings[str(point_number)]['touch_down'].append(point_down)
                    num_touch_down += 1

                if touch_up is not None:
                    point_up = analyzers.panel_to_target((touch_up[0], touch_up[1]), self.dut_info)
                    x_coordinates_up.append(point_up[0])
                    y_coordinates_up.append(point_up[1])
                    data_for_drawings[str(point_number)]['touch_up'].append(point_up)
                    num_touch_up += 1

            number_of_missing_touch_down = number_of_taps_at_each_location - num_touch_down
            number_of_missing_touch_up = number_of_taps_at_each_location - num_touch_up

            num_missing_touch_down_total += number_of_missing_touch_down
            num_missing_touch_up_total += number_of_missing_touch_up

            # Overwrite drawing reference point and calculate errors based on the average location of all the points
            if x_coordinates_down:
                reference_x_down = np.average(x_coordinates_down)
            if y_coordinates_down:
                reference_y_down = np.average(y_coordinates_down)
            data_for_drawings[str(point_number)]['reference_point_down'] = (reference_x_down, reference_y_down)

            down_accuracy_errors[point_id] = calculate_errors(reference_x_down, reference_y_down,
                                                              x_coordinates_down,
                                                              y_coordinates_down)

            self.point_errors_down += down_accuracy_errors[point_id]

            if x_coordinates_up:
                reference_x_up = np.average(x_coordinates_up)
            if y_coordinates_up:
                reference_y_up = np.average(y_coordinates_up)
            data_for_drawings[str(point_number)]['reference_point_up'] = (reference_x_up, reference_y_up)

            up_accuracy_errors[point_id] = calculate_errors(reference_x_up, reference_y_up,
                                                            x_coordinates_up,
                                                            y_coordinates_up)

            self.point_errors_up += up_accuracy_errors[point_id]

            # Calculating the single point values
            if down_accuracy_errors[point_id]:
                down_accuracy_errors_array = np.array(down_accuracy_errors[point_id])
                down_err_avg = np.average(down_accuracy_errors_array)
                down_err_stdev = sqrt(np.mean(down_accuracy_errors_array ** 2))
                down_err_max = max(down_accuracy_errors_array)
            else:
                down_err_avg = None
                down_err_stdev = None
                down_err_max = None

            if up_accuracy_errors[point_id]:
                up_accuracy_errors_array = np.array(up_accuracy_errors[point_id])
                up_err_avg = np.average(up_accuracy_errors_array)
                up_err_stdev = sqrt(np.mean(up_accuracy_errors_array ** 2))
                up_err_max = max(up_accuracy_errors_array)
            else:
                up_err_avg = None
                up_err_stdev = None
                up_err_max = None

            # Storing the single point values, typecasting in string just in case
            self.point_db_data[str(point_number)] = {'touch_down': {'avg': analyzers.float_for_db(down_err_avg),
                                                                    'stdev': analyzers.float_for_db(down_err_stdev),
                                                                    'max': analyzers.float_for_db(down_err_max),
                                                                    'num_missing': number_of_missing_touch_down},
                                                     'touch_up': {'avg': analyzers.float_for_db(up_err_avg),
                                                                  'stdev': analyzers.float_for_db(up_err_stdev),
                                                                  'max': analyzers.float_for_db(up_err_max),
                                                                  'num_missing': number_of_missing_touch_up}
                                                     }

            point_numbers[point_id] = point_number

            max_pen_down_error, max_pen_up_error = get_maximum_errors(repeatability_test_points[0].touch_area)

            if down_accuracy_errors[point_id]:
                # If there are any values in the list, check the maximum against the set limit
                down_error_exceeds_limit = max(down_accuracy_errors[point_id]) > analyzers.float_for_db(max_pen_down_error)
            else:
                # No values, consider it failed
                down_error_exceeds_limit = True

            # Same handling as above
            if up_accuracy_errors[point_id]:
                up_error_exceeds_limit = max(up_accuracy_errors[point_id]) > analyzers.float_for_db(max_pen_up_error)
            else:
                up_error_exceeds_limit = True

            if down_error_exceeds_limit or up_error_exceeds_limit:
                failed_points.append((data['robot_x'], data['robot_y'], point_id + 1))
            else:
                passed_points.append((data['robot_x'], data['robot_y'], point_id + 1))

            verdicts_down[point_id] = "Fail" if down_error_exceeds_limit else "Pass"
            verdicts_up[point_id] = "Fail" if up_error_exceeds_limit else "Pass"

        try:
            down_max = analyzers.float_for_db(np.max([np.max(errors) for errors in down_accuracy_errors if errors]))
            down_avg_of_max = analyzers.float_for_db(np.average([np.max(errors) for errors in down_accuracy_errors if errors]))
            down_avg = analyzers.float_for_db(np.average([np.average(errors) for errors in down_accuracy_errors if errors]))
        except ValueError:
            down_max = np.NaN
            down_avg_of_max = np.NaN
            down_avg = np.NaN

        down_sd = analyzers.float_for_db(sqrt(np.mean(np.array(self.point_errors_down) ** 2))) if self.point_errors_down else np.NaN

        try:
            up_max = analyzers.float_for_db(np.max([np.max(errors) for errors in up_accuracy_errors if errors]))
            up_avg_of_max = analyzers.float_for_db(np.average([np.max(errors) for errors in up_accuracy_errors if errors]))
            up_avg = analyzers.float_for_db(np.average([np.average(errors) for errors in up_accuracy_errors if errors]))
        except ValueError:
            up_max = np.NaN
            up_avg_of_max = np.NaN
            up_avg = np.NaN

        up_sd = analyzers.float_for_db(sqrt(np.mean(np.array(self.point_errors_up) ** 2))) if self.point_errors_up else np.NaN

        # Total number of points including both "touch up" and "touch down".
        num_points_total = len(list(repeatability_test_points)) * number_of_taps_at_each_location * 2
        num_missing_total = num_missing_touch_down_total + num_missing_touch_up_total

        # Missing points do not affect the total verdict
        if num_points_total > 0:
            missing_point_percentage = 100 * num_missing_total / num_points_total
            if missing_point_percentage <= settings['repeatability_missing_points']:
                missing_point_verdict = 'Pass'
            else:
                missing_point_verdict = 'Fail'
        else:
            missing_point_percentage = 100
            missing_point_verdict = 'Fail'

        results = {'border_width': repeatability_test_points[0].border_width if num_test_points > 0 else 0,
                   'max_down_repeatability_error': down_max,
                   'avg_of_max_down_repeatability_error': down_avg_of_max,
                   'avg_down_repeatability_error': down_avg,
                   'stdev_down_repeatability_error': down_sd,
                   'max_up_repeatability_error': up_max,
                   'avg_of_max_up_repeatability_error': up_avg_of_max,
                   'avg_up_repeatability_error': up_avg,
                   'stdev_up_repeatability_error': up_sd,
                   'repeatability_errors_down': format_error_list(down_accuracy_errors, verdicts_down, point_numbers),
                   'repeatability_errors_up': format_error_list(up_accuracy_errors, verdicts_up, point_numbers),
                   'passed_points': passed_points,
                   'failed_points': failed_points,
                   'touch_area': repeatability_test_points[0].touch_area if num_test_points > 0 else "",
                   'test_parameters': test_parameters,
                   'data_for_drawings': data_for_drawings,
                   'num_missing_touch_down_total': num_missing_touch_down_total,
                   'num_missing_touch_up_total': num_missing_touch_up_total,
                   'num_missing_total': num_missing_total,
                   'num_points_total': num_points_total,
                   'missing_point_percentage': missing_point_percentage,
                   'missing_point_verdict': missing_point_verdict}

        dbsession.close()
        return results

    def read_point_details(self, point_id, pen_down):
        """
        Runs read_test_results and collects data from there in the form that the picture drawing function
        requires it
        :param point_id:
        :param pen_down:
        :param dutinfo:
        :return:
        """
        all_results = self.results
        point_results = all_results['data_for_drawings'][str(point_id)]

        error_settings = get_maximum_errors(all_results['touch_area'])
        max_error = error_settings[0] if pen_down else error_settings[1]

        reference_point = point_results['reference_point_down'] if pen_down else point_results['reference_point_up']
        points_arr = []
        results = {}

        if pen_down:
            for point in point_results['touch_down']:
                points_arr.append(point)
        else:  # pen_up
            for point in point_results['touch_up']:
                points_arr.append(point)

        failed, failed_count, passed, passed_count = analyze_points(max_error, points_arr, reference_point)

        results['reference_point'] = reference_point
        results['error_radius'] = max_error
        results['passed_points'] = passed
        results['passed_points_count'] = passed_count
        results['failed_points'] = failed
        results['failed_points_count'] = failed_count

        return results

    def upload_sql_data(self, session):
        # Add test summary to database
        if self.results is not None:
            test_results = self.results
        else:
            self.results = self.read_test_results()
            test_results = self.results

        test_item = self.get_test_item()
        test_session = self.get_test_session()

        for touch_dir in ['touch_down', 'touch_up']:
            summary = TappingRepeatabilitySummarySQL()

            summary.test_id = self.test_id

            test_parameters = test_results['test_parameters']

            summary.time_test_start = timestr_to_datetime(test_item.starttime)
            summary.time_sequence_start = timestr_to_datetime(test_session.starttime)

            # End time is None if sequence was not completed.
            if test_session.endtime is not None:
                summary.time_sequence_end = timestr_to_datetime(test_session.endtime)

            summary.border_width = test_parameters['border_width']
            summary.finger_name = test_parameters['finger_name']
            summary.finger_type = test_parameters['finger_type']
            summary.finger_size = test_parameters['finger_size']
            summary.display_background = test_parameters['display_background']

            summary.number_of_random_locations_center = test_parameters['number_of_random_locations_center']
            summary.number_of_random_locations_edge = test_parameters['number_of_random_locations_edge']
            summary.number_of_random_locations_corner = test_parameters['number_of_random_locations_corner']
            summary.number_of_taps_at_each_location = test_parameters['number_of_taps_at_each_location']

            summary.lift_off_distance = test_parameters['lift_off_distance']
            summary.ground_status = test_parameters['ground_status']
            summary.noise_status = test_parameters['noise_status']
            summary.touch_area = test_results['touch_area']
            summary.log = self.test_item['kmsg_log'] # The test_item comes form Testbase


            summary.touch_direction = touch_dir

            # Separate results for different touch directions
            if touch_dir == 'touch_down':
                summary.tapping_repeatability_avg_of_error_avgs = test_results['avg_down_repeatability_error']
                summary.tapping_repeatability_total_stdev_error = test_results['stdev_down_repeatability_error']
                summary.tapping_repeatability_avg_of_max_errors = test_results['avg_of_max_down_repeatability_error']
                summary.tapping_repeatability_max_of_max_errors = test_results['max_down_repeatability_error']
                summary.total_number_of_missing_points = test_results['num_missing_touch_down_total']
            else:  # touch up
                summary.tapping_repeatability_avg_of_error_avgs = test_results['avg_up_repeatability_error']
                summary.tapping_repeatability_total_stdev_error = test_results['stdev_up_repeatability_error']
                summary.tapping_repeatability_avg_of_max_errors = test_results['avg_of_max_up_repeatability_error']
                summary.tapping_repeatability_max_of_max_errors = test_results['max_up_repeatability_error']
                summary.total_number_of_missing_points = test_results['num_missing_touch_up_total']

            session.add(summary)
            session.commit()

            # Add individual points to database (NOTE: test meta_id is only created
            # when the summary is added to database)
            test_meta_id = summary.meta_id

            # Write results for individual points
            if test_results['touch_area'] == 'center_area':
                num_of_points = test_parameters['number_of_random_locations_center']
            elif test_results['touch_area'] == 'edge_area':
                num_of_points = test_parameters['number_of_random_locations_edge'] * 4  # there are 4 edges
            elif test_results['touch_area'] == 'corner_area':
                num_of_points = test_parameters['number_of_random_locations_corner'] * 4  # there are 4 corners
            else:
                raise Exception('Invalid touch area')

            for point in range(num_of_points):
                point_id = point + 1

                results = TappingRepeatabilityResultsSQL()

                # Writing touch specific data to the database
                results.touch_direction = touch_dir
                results.test_meta_id = test_meta_id
                results.point_id = point_id

                # NOTE: we might not have results for all the points!
                try:
                    touch_data = self.point_db_data[str(point_id)][touch_dir]
                    results.avg_tapping_repeatability = touch_data['avg']
                    results.stdev_tapping_repeatability = touch_data['stdev']
                    results.max_tapping_repeatability = touch_data['max']
                    results.number_of_missing_points = touch_data['num_missing']
                except:
                    results.avg_tapping_repeatability = None
                    results.stdev_tapping_repeatability = None
                    results.max_tapping_repeatability = None
                    pass
                session.add(results)
                session.commit()


##############################################
# Auxiliary functions
##############################################

def analyze_points(max_error, points_arr, reference_point):
    failed = []
    failed_count = []
    passed = []
    passed_count = []

    if len(points_arr) > 0:
        for point in points_arr:
            point_error = sqrt(
                (reference_point[0] - point[0]) ** 2 + (reference_point[1] - point[1]) ** 2)
            if point_error > max_error:
                if point in failed:
                    failed_count[failed.index(point)] += 1
                else:
                    failed.append(point)
                    failed_count.append(1)
            else:
                if point in passed:
                    passed_count[passed.index(point)] += 1
                else:
                    passed.append(point)
                    passed_count.append(1)

    return failed, failed_count, passed, passed_count


def format_error_list(accuracy_errors, verdicts, points):
    max_errors = []
    avg_errors = []
    stdev_errors = []
    for error_list in accuracy_errors:
        try:
            max_errors.append(max(error_list))
            avg_errors.append(np.average(error_list))
            stdev_errors.append(np.std(error_list))
        except ValueError:
            max_errors.append(np.NaN)
            avg_errors.append(np.NaN)
            stdev_errors.append(np.NaN)

    return list(
        zip(analyzers.float_for_db_array(max_errors),
            analyzers.float_for_db_array(avg_errors),
            analyzers.float_for_db_array(stdev_errors),
            verdicts,
            points))


def calculate_errors(reference_x, reference_y, x_coordinates, y_coordinates):
    differences = [(x - reference_x, y - reference_y) for (x, y) in zip(x_coordinates, y_coordinates)]

    return [sqrt(x ** 2 + y ** 2) for (x, y) in differences]


def get_maximum_errors(touch_area):
    max_pen_down_error = 0.0
    max_pen_up_error = 0.0

    if touch_area == 'edge_area':
        max_pen_down_error = settings['max_error_edge_down']
        max_pen_up_error = settings['max_error_edge_up']
    elif touch_area == 'center_area':
        max_pen_down_error = settings['max_error_center_down']
        max_pen_up_error = settings['max_error_center_up']
    elif touch_area == 'corner_area':
        max_pen_down_error = settings['max_error_corner_down']
        max_pen_up_error = settings['max_error_corner_up']

    return max_pen_down_error, max_pen_up_error
