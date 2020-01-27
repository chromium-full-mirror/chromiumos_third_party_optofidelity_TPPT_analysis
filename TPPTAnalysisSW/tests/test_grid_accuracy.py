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
from genshi.template import MarkupTemplate
import numpy as np
from sqlalchemy import *
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import joinedload

from ..testbase import TestBase, testclasscreator, timestr_to_datetime
from ..imagefactory import ImageFactory
from ..settings import settings, precision
from ..utils import Timer
from ..info.version import Version
import TPPTAnalysisSW.measurementdb as db
import TPPTAnalysisSW.analyzers as analyzers
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.plotinfo as plotinfo
from TPPTAnalysisSW.analyzers import filter_points
from TPPTAnalysisSW.sqluploader import Base
import datetime
from math import sqrt
from TPPTAnalysisSW import toolbox

import base64

class GridAccuracySummarySQL(Base):
    __tablename__ = 'touch_grid_accuracy_summary'

    meta_id = Column(INTEGER, primary_key=True)

    time_test_start = Column(DATETIME)
    test_id = Column(DECIMAL(10,0))
    time_sequence_start = Column(DATETIME)
    time_sequence_end = Column(DATETIME)

    border_width = Column(DECIMAL(8,2))
    finger_name = Column(VARCHAR(40))
    finger_type = Column(VARCHAR(40))
    finger_size = Column(DECIMAL(8,2))
    step_size = Column(DECIMAL(8, 2))
    num_fingers = Column(DECIMAL(8, 2))
    lift_off_distance = Column(DECIMAL(8,2))
    ground_status = Column(VARCHAR(40))
    display_background = Column(VARCHAR(40))
    touch_area = Column(VARCHAR(40))
    touch_direction = Column(VARCHAR(40))
    contact_duration = Column(DECIMAL(8,2))
    log = Column(LONGTEXT)

    grid_accuracy_avg_of_error_avgs = Column(DECIMAL(16, 3))
    grid_accuracy_total_stdev_error = Column(DECIMAL(16, 3))
    grid_accuracy_avg_of_max_errors = Column(DECIMAL(16, 3))
    grid_accuracy_max_of_max_errors = Column(DECIMAL(16, 3))

    total_number_of_missing_points = Column(Integer)

    # The time of database entry creation set by the database server
    created = Column(TIMESTAMP(), server_default=func.current_timestamp())

class GridAccuracyTest(TestBase):
    """
    Grid accuracy test measures how close reported touch events are to actual tap positions.
    """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(15)
    def create_testclass(*args, **kwargs):
        return GridAccuracyTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new test case class """
        super(GridAccuracyTest, self).__init__(ddtest_row, *args, **kwargs)
        self.sql_summary_class = GridAccuracySummarySQL

        # These are used if dut has an svg file for boundaries
        self.dut_svg = None
        self.analysis_region_countour = None
        self.dut_has_notch = None

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        results = self.read_test_results()

        # Test case verdict is only affected by average of maximum input error verdict.
        verdict = "Pass" if results['avg_max_input_verdict'] else "Fail"

        return verdict

    # Override to make necessary operations for clearing test results
    # Clearing the test result from the results table is done elsewhere
    def clearanalysis(self, *args, **kwargs):
        """ Clears analysis results """
        ImageFactory.delete_images(self.test_id)

    # Create the test report. Return the created HTML, or raise cherrypy.HTTPError
    def createreport(self, *args, **kwargs):

        self.clearanalysis()

        # Create common template parameters (including test_item dictionary, testsession dictionary, test_id, test_type_name etc)
        template_params = super(GridAccuracyTest, self).create_common_templateparams(**kwargs)

        t = Timer()

        # data for the report
        results = self.read_test_results()
        template_params['results'] = results

        t.Time("Results")

        # set the content to be used
        template_params['test_page'] = 'test_grid_accuracy.html'
        template_params['version'] = Version

        template_params['test_parameters'] = (('Border width [mm]', results['border_width']),
                                             ('Finger name', results['finger_name']),
                                             ('Finger type', results['finger_type']),
                                             ('Finger size [mm]', results['finger_size']),
                                             ('Number of fingers', results['num_fingers']),
                                             ('Step size [mm]', results['step_size']),
                                             ('Lift off distance [mm]', results['lift_off_distance']),
                                             ('Ground status', results['ground_status']),
                                             ('Noise status', results['noise_status']),
                                             ('Touch area', results['touch_area']),
                                             ('Contact duration [ms]', results['contact_duration']),
                                             ('Display background', results['display_background'])
                                             )

        self.disable_upload_button_if_already_uploaded(template_params)

        template = MarkupTemplate(open("templates/test_configured_body.html"))
        stream = template.generate(**(template_params))
        t.Time("Markup")

        # Test case verdict is only affected by average of maximum input error verdict.
        verdict = "Pass" if results['avg_max_input_verdict'] and results['avg_max_edge_only_verdict'] else "Fail"

        return stream.render('xhtml'), verdict


    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'p2pdiff':
            t = Timer(1)
            dbsession = db.get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
            t.Time("Results")
            title = 'Preview: Grid Accuracy ' + self.dut['program']
            plot_factory.plot_taptest_on_target(imagepath, results["touch_down"], dutinfo, *args, title=title, **kwargs)
            plot_factory.plot_taptest_on_target(imagepath, results["touch_up"], dutinfo, *args, title=title, **kwargs)
            t.Time("Image")
        elif image_name == 'p2pdxdy':
            t = Timer(1)
            results = self.read_test_results(**kwargs)
            t.Time("Results")
            plot_factory.plot_dxdy_graph(imagepath, results["touch_down"], 0.0, *args, **kwargs)
            plot_factory.plot_dxdy_graph(imagepath, results["touch_up"], 0.0, *args, **kwargs)
            t.Time("Image")
        elif image_name == 'p2pdxdyltd':
            t = Timer(1)
            results = self.read_test_results(**kwargs)
            t.Time("Results")
            plot_factory.plot_dxdy_graph(imagepath, results["touch_down"], 1.0, *args, **kwargs)
            plot_factory.plot_dxdy_graph(imagepath, results["touch_up"], 1.0, *args, **kwargs)
            t.Time("Image")
        elif image_name == 'p2phistogram':
            t = Timer(1)
            results = self.read_test_results()
            t.Time("Results")
            plot_factory.plot_p2p_err_histogram(imagepath, results["touch_down"], 1.0, *args, edge_only=False, **kwargs)
            plot_factory.plot_p2p_err_histogram(imagepath, results["touch_up"], 1.0, *args, edge_only=False, **kwargs)
            t.Time("Image")

        return None

    def is_point_on_edge_only(self, point, dutinfo, border_width):
        '''
        Checks if point (robot point) is in edge area but not in corner or notch area. Corner detection is done
        by using rectangle model of DUT
        :param point: point object
        :param dutinfo: dutinfo object
        :param border_width: width of edge area
        :return: True if point is in edge area, False if point is in center, corner, or notch
        '''
        dut_width = dutinfo.dimensions[0]
        dut_height = dutinfo.dimensions[1]
        x = point.robot_x
        y = point.robot_y
        if x < border_width and border_width < y <(dut_height - border_width):
            # left vertical edge
            return True
        elif x > (dut_width - border_width) and border_width < y <(dut_height - border_width):
            # right vertical edge
            return True
        elif y > (dut_height - border_width) and border_width < x < (dut_width - border_width):
            # lower horizontal edge
            return True
        elif y < border_width and border_width < x < (dut_width - border_width):
            # upper horizontal edge
            if not self.dut_has_notch:
                return True
            else:
                # if there is notch, the whole upper horizontal edge is considered
                # as notch area and thus discarded
                return False
        else:
            return False

    def has_notch(self, dutinfo):
        '''
        Checks if dut has notch or not based on the difference of svg "test_region" and
        "analysis_region" (draws vertical line in the middle of dut and sees if it is cut by notch)
        :param dutinfo:
        :return: True if there is not notch, False if not
        '''
        mid_point = dutinfo.dimensions[0] / 2
        start_x, end_x = mid_point, mid_point
        start_y, end_y = 0, dutinfo.dimensions[1]
        filtered_points = self.dut_svg.filter_lines_str_region([(start_x, start_y, end_x, end_y)], 'analysis_region', 0)
        return filtered_points[0][0][1] > 0.1 # True if there is notch

    def read_test_results(self, dutinfo = None, dbsession = None):
        if dbsession is None:
            dbsession = db.get_database().session()
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        query = dbsession.query(db.GridAccuracyTest).filter(
            db.GridAccuracyTest.test_id == self.test_id). \
            options(joinedload(db.GridAccuracyTest.grid_accuracy_results)). \
            order_by(db.GridAccuracyTest.id)

        if self.dut_svg is None and dutinfo.svg_data is not None:
            try:
                self.dut_svg = toolbox.dut.SvgRegion()
                self.dut_svg.load_string(base64.b64decode(dutinfo.svg_data).decode('ascii'))
            except Exception as e:
                raise Exception('Failed to load dut svg file: ' + str(e))

        if self.dut_has_notch is None and dutinfo.svg_data is not None:
            self.dut_has_notch = self.has_notch(dutinfo)

        num_points = len(list(query))

        # Is test case over edge area?
        is_edge_area = (query[0].touch_area == "edge_area") if num_points > 0 else False

        max_pos_error = (settings['max_error_edge_corner_notch'] if is_edge_area else settings['max_error_center'])

        # Total points is 2 times the number of locations because "touch down" and "touch up" are analyzed separately.
        # Both cases contribute to the number of missing points that is compared to total points.
        total_points = num_points * 2

        # Total results contains both touch down and touch up results and combined verdicts.
        total_results = {'avg_max_input_error': None,
                         'avg_max_input_verdict': None,
                         'avg_max_edge_only_error': None,
                         'avg_max_edge_only_verdict': None,
                         'total_points': total_points,
                         'missing_inputs': None,
                         'missing_inputs_verdict': None,
                         'passed_points': None,
                         'failed_points': None,
                         'maxposerror': max_pos_error,
                         'maxposerror_edge_only': settings["max_error_edge"],
                         'touch_down': None,
                         'touch_up': None,
                         'border_width': query[0].border_width if num_points > 0 else 0,
                         'finger_name': query[0].finger_name if num_points > 0 else "",
                         'finger_type': query[0].finger_type if num_points > 0 else "",
                         'step_size': query[0].step_size if num_points > 0 else 0,
                         'finger_size': query[0].finger_size if num_points > 0 else 0,
                         'num_fingers': int(query[0].num_fingers) if num_points > 0 else 0,
                         'lift_off_distance': query[0].lift_off_distance if num_points > 0 else 0,
                         'ground_status': query[0].ground_status if num_points > 0 else 0,
                         'display_background': query[0].display_background if num_points > 0 else "",
                         'touch_area': query[0].touch_area if num_points > 0 else "",
                         'contact_duration': query[0].contact_duration if num_points > 0 else 0,
                         'noise_status': query[0].noise_status if num_points > 0 else 0,
                         'calculation_time': datetime.datetime.now(),
                         'ghost_finger_found': False
                         }

        # Distances from both "touch down" and "touch up".
        # This is dict of lists where dict key is point id and the list contains touch down and touch up point.
        all_distances = {}

        # There is additional collection of edge only points, since they have smaller max error limit
        edge_only_distances = {}

        # Analyze separately touch down and touch up events.
        for touch_dir in ['touch_down', 'touch_up']:
            passed_points = [] # These are tuple-tuples: ((target_x, target_y), (hit_x, hit_y))
            failed_points = []
            targets = []
            hits = [] # target points: ((target_x, target_y), radius)
            missing = [] # target points ((target_x, target_y), radius)

            distances = []

            for point in query:
                # Ghost fingers are recognized in the TPPT scripts and indicated
                # by setting point robot positions to (None, None)
                if point.robot_x is None:
                    total_results['ghost_finger_found'] = True
                    continue

                is_point_edge_only = self.is_point_on_edge_only(point, dutinfo, total_results['border_width'])

                target = analyzers.robot_to_target((point.robot_x, point.robot_y), dutinfo)
                targets.append(target)

                result_point = None

                # Find touch down or touch up events from recorded event stream.
                filtered_point = filter_points(point.grid_accuracy_results)

                if len(filtered_point) > 0:
                    if touch_dir == "touch_down":
                        # Make sure the first filtered point is "touch down".
                        result_point = filtered_point[0] if filtered_point[0].event == 0 else None
                    elif touch_dir == "touch_up":
                        # Make sure the last filtered point is "touch up".
                        result_point = filtered_point[-1] if filtered_point[-1].event == 1 else None
                    else:
                        raise Exception("Invalid touch direction")

                if result_point is None or result_point.panel_x is None or result_point.panel_y is None:

                    missing.append((target, analyzers.get_max_error(target, dutinfo)))
                else:
                    max_error = analyzers.float_for_db(analyzers.get_max_error(target, dutinfo))
                    hits.append((target, max_error))
                    hit = analyzers.panel_to_target((result_point.panel_x, result_point.panel_y), dutinfo)
                    distance = analyzers.float_for_db(np.linalg.norm((hit[0]-target[0], hit[1]-target[1])))
                    distances.append(float(distance))

                    point_id = int(point.id)

                    if point_id in all_distances:
                        all_distances[point_id].append(float(distance))
                    else:
                        all_distances[point_id] = [float(distance)]

                    if distance > max_error:
                        failed_points.append((target, hit))
                    else:
                        passed_points.append((target, hit))

                    # We need to collect separately points that are on edge only:
                    if is_edge_area and is_point_edge_only:
                        if point_id in edge_only_distances:
                            edge_only_distances[point_id].append(float(distance))
                        else:
                            edge_only_distances[point_id] = [float(distance)]

            max_input_error = None
            avg_input_error = None
            stdev_input_error = None

            if len(distances) > 0:
                darray = np.array(distances)
                max_input_error = float(np.max(darray))
                avg_input_error = float(np.mean(darray))
                stdev_input_error = float(sqrt(np.mean(darray**2)))

            results = {'max_input_error': analyzers.float_for_db(max_input_error),
                       'avg_input_error': analyzers.float_for_db(avg_input_error),
                       'stdev_input_error': analyzers.float_for_db(stdev_input_error),
                       'missing_inputs': len(missing),
                       'maxposerror': analyzers.float_for_db(max_pos_error),
                       'passed_points': passed_points,
                       'failed_points': failed_points,
                       'targets': targets,
                       'hits': hits,
                       'missing': missing,
                       'distances': distances,
                       'images': [(ImageFactory.create_image_name(self.test_id, 'p2pdiff'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdiff', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2pdxdy'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdxdy', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2pdxdyltd'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdxdyltd', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2phistogram'),
                                  ImageFactory.create_image_name(self.test_id, 'p2phistogram', 'detailed'))]
                       }

            total_results[touch_dir] = results

        avg_max_input_error = None
        max_max_input_error = None
        avg_avg_input_error = None
        stdev_input_error = None
        avg_max_input_verdict = False

        # Compute input error for total results that considers both "touch up" and "touch down" events.
        if len(all_distances) > 0:
            num_valid_locations = 0

            # Loop through all tap locations. Each location may have produced 0, 1 or 2 distances.
            for dist in all_distances.values():
                # dist is a list that has 0, 1 or 2 values.
                if len(dist) > 0:
                    max_dist = max(dist)

                    # When first valid location is discovered the error values are zeroed.
                    if avg_max_input_error is None: avg_max_input_error = 0.0
                    if max_max_input_error is None: max_max_input_error = 0.0
                    if avg_avg_input_error is None: avg_avg_input_error = 0.0

                    avg_max_input_error += max_dist
                    max_max_input_error = max(max_max_input_error, max_dist)
                    avg_avg_input_error += np.mean(dist)

                    num_valid_locations += 1

            if num_valid_locations > 0:
                avg_max_input_error /= num_valid_locations
                avg_avg_input_error /= num_valid_locations

                avg_max_input_verdict = (avg_max_input_error < max_pos_error)

            # Create array that has all distance values i.e. "touch up" and "touch down".
            darray = []
            for dist in all_distances.values():
                darray += dist

            if len(darray) > 0:
                darray = np.array(darray)

                # Compute standard deviation from all distance values.
                stdev_input_error = float(sqrt(np.mean(darray**2)))

        # Checking the edge only error value and whether it is pass or fail
        avg_max_edge_only_error = 0.0
        # needs to be true by default because it is not checked every time
        # and affects total verdict
        avg_max_edge_only_verdict = True
        # Compute input error for edge only results that considers both "touch up" and "touch down" events
        if len(edge_only_distances) > 0:
            num_valid_locations = 0
            # Loop through all tap locations. Each location may have produced 0, 1 or 2 distances.
            for dist in edge_only_distances.values():
                # dist is a list that has 0, 1 or 2 values.
                if len(dist) > 0:
                    max_dist = max(dist)

                    # When first valid location is discovered the error values are zeroed.
                    if avg_max_edge_only_error is None: avg_max_edge_only_error = 0.0

                    avg_max_edge_only_error += max_dist
                    num_valid_locations += 1

            if num_valid_locations > 0:
                avg_max_edge_only_error /= num_valid_locations
                avg_max_edge_only_verdict = (avg_max_edge_only_error < settings["max_error_edge"])


        # Compute total result verdicts from touch down and touch up cases.
        total_results["avg_max_input_error"] = analyzers.float_for_db(avg_max_input_error)
        total_results["max_max_input_error"] = analyzers.float_for_db(max_max_input_error)
        total_results["avg_avg_input_error"] = analyzers.float_for_db(avg_avg_input_error)
        total_results["stdev_input_error"] = analyzers.float_for_db(stdev_input_error)
        total_results["avg_max_input_verdict"] = avg_max_input_verdict
        total_results["missing_inputs"] = total_results["touch_down"]["missing_inputs"] + total_results["touch_up"]["missing_inputs"]
        total_results["avg_max_edge_only_error"] = analyzers.float_for_db(avg_max_edge_only_error)
        total_results["avg_max_edge_only_verdict"] = avg_max_edge_only_verdict

        # Calculating the percentage of missing inputs and the verdict for it
        if total_results["total_points"] > 0:
            total_results["missing_inputs_percentage"] = analyzers.float_for_db(100*total_results["missing_inputs"]/total_results["total_points"])
        else:
            total_results["missing_inputs_percentage"] = 100
        if total_results["missing_inputs_percentage"] <= settings["grid_acc_missing_points"]:
            total_results["missing_inputs_verdict"] = "Pass"
        else:
            total_results["missing_inputs_verdict"] = "Fail"

        return total_results

    def upload_sql_data(self, session):
        test_results = self.read_test_results()

        test_item = self.get_test_item()
        test_session = self.get_test_session()

        # Write SQL row for both touch directions and combined results.
        for touch_dir in ['touch_down', 'touch_up', 'both']:
            summary = GridAccuracySummarySQL()

            summary.test_id = self.test_id

            summary.time_test_start = timestr_to_datetime(test_item.starttime)
            summary.time_sequence_start = timestr_to_datetime(test_session.starttime)

            # End time is None if sequence was not completed.
            if test_session.endtime is not None:
                summary.time_sequence_end = timestr_to_datetime(test_session.endtime)

            summary.border_width = test_results["border_width"]
            summary.finger_name = test_results["finger_name"]
            summary.finger_type = test_results["finger_type"]
            summary.finger_size = test_results["finger_size"]
            summary.num_fingers = test_results["num_fingers"]
            summary.step_size = test_results["step_size"]
            summary.lift_off_distance = test_results["lift_off_distance"]
            summary.ground_status = test_results["ground_status"]
            summary.display_background = test_results["display_background"]
            summary.touch_area = test_results["touch_area"]
            summary.touch_direction = touch_dir
            summary.contact_duration = test_results["contact_duration"]
            summary.log = self.test_item['kmsg_log'] # The test_item comes form Testbase

            if touch_dir == 'both':
                summary.grid_accuracy_avg_of_error_avgs = test_results["avg_avg_input_error"]
                summary.grid_accuracy_avg_of_max_errors = test_results["avg_max_input_error"]

                summary.grid_accuracy_max_of_max_errors = test_results["max_max_input_error"]
                summary.grid_accuracy_total_stdev_error = test_results["stdev_input_error"]

                summary.total_number_of_missing_points = test_results["missing_inputs"]
            else:
                # In grid accuracy there is only one point per grid location so "avg of avg" and "avg of max" are the same.
                summary.grid_accuracy_avg_of_error_avgs = test_results[touch_dir]["avg_input_error"]
                summary.grid_accuracy_avg_of_max_errors = test_results[touch_dir]["avg_input_error"]

                summary.grid_accuracy_max_of_max_errors = test_results[touch_dir]["max_input_error"]
                summary.grid_accuracy_total_stdev_error = test_results[touch_dir]["stdev_input_error"]

                summary.total_number_of_missing_points = test_results[touch_dir]["missing_inputs"]

            session.add(summary)
            session.commit()