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
import numpy as np
import numpy.linalg
from math import sqrt
from sqlalchemy import *
from sqlalchemy.dialects.mysql import LONGTEXT


from TPPTAnalysisSW.sqluploader import Base
from TPPTAnalysisSW.testbase import TestBase, testclasscreator, timestr_to_datetime
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.utils import Timer
import TPPTAnalysisSW.measurementdb as db
from TPPTAnalysisSW.settings import settings
from TPPTAnalysisSW.info.version import Version
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.analyzers as analyzers
import datetime


class StationaryJitterStaticNoiseSummarySQL(Base):
    __tablename__ = 'touch_stationary_jitter_static_noise_summary'

    meta_id = Column(Integer, primary_key=True)

    time_test_start = Column(DATETIME)
    test_id = Column(DECIMAL(10, 0))
    time_sequence_start = Column(DATETIME)
    time_sequence_end = Column(DATETIME)

    border_width = Column(DECIMAL(8, 2))
    finger_name = Column(VARCHAR(40))
    finger_type = Column(VARCHAR(40))
    finger_size = Column(DECIMAL(8, 2))
    step_size = Column(DECIMAL(8, 2))
    lift_off_distance = Column(DECIMAL(8, 2))
    ground_status = Column(VARCHAR(40))
    display_background = Column(VARCHAR(40))
    noise_status = Column(VARCHAR(40))
    touch_area = Column(VARCHAR(40))
    contact_duration = Column(DECIMAL(8, 2))
    number_of_fingers_on_screen = Column(DECIMAL(6, 2))
    log = Column(LONGTEXT)
    test_type = Column(VARCHAR(40))

    stationary_jitter_avg_of_error_avgs = Column(DECIMAL(16, 3))
    stationary_jitter_total_stdev_error = Column(DECIMAL(16, 3))
    stationary_jitter_avg_of_max_errors = Column(DECIMAL(16, 3))
    stationary_jitter_max_of_max_errors = Column(DECIMAL(16, 3))

    total_number_of_missing_points = Column(Integer)

    # The time of database entry creation set by the database server
    created = Column(TIMESTAMP(), server_default=func.current_timestamp())

class StationaryJitterStaticNoiseTest(TestBase):
    """
    Stationary jitter static noise test measures how much reported touch locations vary
    from actual robot position under different conditions.
    """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(16)
    def create_testclass(*args, **kwargs):
        return StationaryJitterStaticNoiseTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new test case class """
        super(StationaryJitterStaticNoiseTest, self).__init__(ddtest_row, *args, **kwargs)
        self.sql_summary_class = StationaryJitterStaticNoiseSummarySQL

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

        t = Timer(1)

        self.clearanalysis()

        # Create common template parameters (including test_item dictionary, testsession dictionary, test_id, test_type_name etc)
        template_params = super(StationaryJitterStaticNoiseTest, self).create_common_templateparams(**kwargs)

        results = self.read_test_results()

        t.Time("Results")

        # Add the image name and parameters to the report
        template_params['results'] = results
        template_params['figure'] = ImageFactory.create_image_name(self.test_id, 'stjitt')
        template_params['detailed_figure'] = ImageFactory.create_image_name(self.test_id, 'stjitt', 'detailed')
        template_params['test_page'] = 'test_stationary_jitter_static_noise.html'
        template_params['test_script'] = 'test_page_subplots.js'
        template_params['version'] = Version

        template_params['test_parameters'] = (('Border width [mm]', results['border_width']),
                                             ('Finger name', results['finger_name']),
                                             ('Finger type', results['finger_type']),
                                             ('Finger size [mm]', results['finger_size']),
                                             ('Finger 2 name', results['finger2_name']),
                                             ('Separation [mm]', results['separation']),
                                             ('Step size [mm]', results['step_size']),
                                             ('Lift off distance [mm]', results['lift_off_distance']),
                                             ('Ground status', results['ground_status']),
                                             ('Touch area', results['touch_area']),
                                             ('Contact duration [ms]', results['contact_duration']),
                                             ('Noise status', results['noise_status']),
                                             ('Display background', results['display_background']),
                                             ('Number of fingers on screen', results['number_of_fingers_on_screen']),
                                             )

        self.disable_upload_button_if_already_uploaded(template_params)

        template = MarkupTemplate(open("templates/test_configured_body.html"))
        stream = template.generate(**(template_params))
        t.Time("Markup")
        return stream.render('xhtml'), results['verdict']


    # Create images for the report. If the function returns a value, it is used as the new image name (without image path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        # Dummy test has only one image: dummyimage.
        if image_name == 'stjitt':
            dbsession = db.get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_test_results(dutinfo, dbsession)
            title = 'Preview: Stationary Jitter Static Noise ' + self.dut['program']
            plot_factory.plot_passfail_labels_on_target(imagepath, results, dutinfo, *args, title=title, **kwargs)
        elif image_name == 'stjittdtls':
            dbsession = db.get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_point_details(args[0], dutinfo, dbsession)
            title = 'Preview: Stationary Jitter Static Noise details ' + self.dut['program']
            plot_factory.plot_passfail_labels(imagepath, results, title=title, **kwargs)
        else:
            raise cherrypy.HTTPError(message = "No such image in the report")

        return None


    def read_test_results(self, dutinfo = None, dbsession = None):
        if dbsession is None:
            dbsession = db.get_database().session()
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        pts = dbsession.query(db.StationaryJitterStaticNoiseTest).filter(db.StationaryJitterStaticNoiseTest.test_id==self.test_id).\
                                                             options(joinedload(db.StationaryJitterStaticNoiseTest.stationary_jitter_static_noise_results)).\
                                                             order_by(db.StationaryJitterStaticNoiseTest.id)

        num_pts = len(list(pts))

        passed = []
        failed = []
        points = []
        all_deviations = []
        avg_max_jitter = 0
        avg_mean_jitter = 0
        total_stdev_jitter = 0
        max_max_jitter = None
        verdict = "N/A"
        point_id = 1

        noise_status = pts[0].noise_status if num_pts > 0 else ""
        test_type = pts[0].test_type if num_pts > 0 else ""

        # The pass/fail limit depends on the test case
        if noise_status == '':
            jitter_limit = settings['max_stat_jitter_no_noise']
        else:
            jitter_limit = settings['max_stat_jitter_noise']
        if test_type == 'noise_test':
            jitter_limit = settings['max_noise_test_jitter']

        num_missing_points = 0
        num_valid_points = 0

        # For each touch location, compute maximum and standard deviation jitter.
        for point in pts:
            # Get panel points that result from the first finger (ID 0).
            panel_points = []
            for p in point.stationary_jitter_static_noise_results:
                if p.finger_id == 0:
                    panel_points.append((p.panel_x, p.panel_y))

            target_points = analyzers.panel_to_target(panel_points, dutinfo)

            robot_point = analyzers.robot_to_target((point.robot_x, point.robot_y), dutinfo)

            if len(target_points) == 0:
                # No measurements for point

                failed.append(list(robot_point) + [str(point_id)])
                points.append((point_id, None, "N/A", None))
                point_id += 1

                num_missing_points += 1
            else:
                num_valid_points += 1

                points_np = np.array([np.array(p) for p in target_points])

                min_point = np.min(points_np, axis=0)
                max_point = np.max(points_np, axis=0)
                point_max_jitter = np.linalg.norm(max_point - min_point)

                point_max_jitter_rounded = analyzers.float_for_db(point_max_jitter)

                mean_point = np.mean(points_np, axis=0)
                mean_points = np.tile(mean_point, (len(target_points), 1))
                deviations = np.linalg.norm(mean_points - points_np, axis=1)

                all_deviations = np.concatenate((all_deviations, deviations))

                point_avg_jitter = np.mean(deviations)
                avg_mean_jitter += point_avg_jitter

                point_verdict = "Fail" if point_max_jitter > jitter_limit else "Pass"
                points.append((point_id, point_max_jitter_rounded, point_verdict, ImageFactory.create_image_name(self.test_id, 'stjittdtls', str(point.id))))

                if max_max_jitter is None or point_max_jitter > max_max_jitter:
                    max_max_jitter = point_max_jitter

                avg_max_jitter += point_max_jitter

                if point_verdict == "Pass":
                    passed.append(list(target_points[0]) + [point_id])
                else:
                    failed.append(list(target_points[0]) + [point_id])

                point_id += 1

        if num_valid_points > 0:
            avg_mean_jitter = analyzers.float_for_db(avg_mean_jitter / num_valid_points)
            avg_max_jitter = analyzers.float_for_db(avg_max_jitter / num_valid_points)
            max_max_jitter = analyzers.float_for_db(max_max_jitter)

            verdict = "Fail" if avg_max_jitter > jitter_limit else "Pass"

            # Compute standard deviation of all deviations.
            total_stdev_jitter = analyzers.float_for_db(sqrt(np.mean(all_deviations ** 2)))
        else:
            # None values show up as "N/A" in the result page.
            avg_mean_jitter = None
            avg_max_jitter = None
            max_max_jitter = None
            total_stdev_jitter = None

        if num_pts > 0:
            missing_points_percentage = 100*num_missing_points / num_pts
        else:
            missing_points_percentage = 100

        if missing_points_percentage <= settings['jitter_missing_points']:
            missing_inputs_verdict = 'Pass'
        else:
            missing_inputs_verdict = 'Fail'

        results = {'passed_points': passed,
                   'failed_points': failed,
                   'total_points': num_pts,
                   'missing_points_percentage': missing_points_percentage,
                   'missing_inputs_verdict': missing_inputs_verdict,
                   'avg_mean_jitter': avg_mean_jitter,
                   'avg_max_jitter': avg_max_jitter,
                   'max_max_jitter': max_max_jitter,
                   'total_stdev_jitter': total_stdev_jitter,
                   'verdict': verdict,
                   'points': points,
                   'border_width': pts[0].border_width if num_pts > 0 else 0,
                   'finger_name': pts[0].finger_name if num_pts > 0 else "",
                   'finger_type': pts[0].finger_type if num_pts > 0 else "",
                   'finger2_name': pts[0].finger2_name if num_pts > 0 else "",
                   'separation': pts[0].separation if num_pts > 0 else 0,
                   'step_size': pts[0].step_size if num_pts > 0 else 0,
                   'finger_size': pts[0].finger_size if num_pts > 0 else 0,
                   'lift_off_distance': pts[0].lift_off_distance if num_pts > 0 else 0,
                   'noise_status': pts[0].noise_status if num_pts > 0 else "",
                   'ground_status': pts[0].ground_status if num_pts > 0 else "",
                   'display_background': pts[0].display_background if num_pts > 0 else "",
                   'touch_area': pts[0].touch_area if num_pts > 0 else "",
                   'contact_duration': pts[0].contact_duration if num_pts > 0 else 0,
                   'number_of_fingers_on_screen': pts[0].number_of_fingers_on_screen if num_pts > 0 else 0,
                   'missing_inputs': num_missing_points,
                   'test_type': test_type
                   }

        return results

    def read_point_details(self, point_id, dutinfo = None, dbsession = None):
        if dbsession is None:
            dbsession = db.get_database().session()
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        points = dbsession.query(db.StationaryJitterStaticNoiseResults).filter(db.StationaryJitterStaticNoiseResults.point_id==point_id).\
                                                                   order_by(db.StationaryJitterStaticNoiseResults.id)

        robot_point = dbsession.query(db.StationaryJitterStaticNoiseTest).filter(db.StationaryJitterStaticNoiseTest.id==point_id).\
                                                                    order_by(db.StationaryJitterStaticNoiseTest.id)

        # Get panel points that result from the first finger (ID 0).
        panel_points = []
        for p in points:
            if p.finger_id == 0:
                panel_points.append((p.panel_x, p.panel_y))

        target_points = analyzers.panel_to_target(panel_points, dutinfo)

        points = []
        point_count = []

        for point in target_points:
            if point in points:
                point_count[points.index(point)] += 1
            else:
                points.append(point)
                point_count.append(1)

        result = None

        # When using max error metric it is not possible to separate passed and failed points.
        # Just put all points in passed list.
        if len(points) > 1:
            orig = np.array(points[0])
            distances = np.array([np.linalg.norm(np.array(p) - orig) for p in points])
            passed = []
            failed = []

            for point, distance, count in zip(points, distances, point_count):
                passed.append((point[0], point[1], str(count) if count > 1 else ''))

            result = {'passed_points': passed, 'failed_points': failed, 'robot_point': robot_point}
        elif len(points) == 1:
            # Only one point in lists...
            points = [(points[0][0], points[0][1], str(point_count[0]) if point_count[0] > 1 else '')]
            result = {'passed_points': points, 'failed_points': [], 'robot_point': robot_point}
        if len(points) == 0:
            # No points
            result = {'passed_points': [], 'failed_points': [], 'robot_point': robot_point}

        return result

    def upload_sql_data(self, session):
        test_results = self.read_test_results()

        test_item = self.get_test_item()
        test_session = self.get_test_session()

        summary = StationaryJitterStaticNoiseSummarySQL()

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
        summary.step_size = test_results["step_size"]
        summary.lift_off_distance = test_results["lift_off_distance"]
        summary.ground_status = test_results["ground_status"]
        summary.display_background = test_results["display_background"]
        summary.touch_area = test_results["touch_area"]
        summary.noise_status = test_results["noise_status"]
        summary.number_of_fingers_on_screen = test_results["number_of_fingers_on_screen"]
        summary.contact_duration = test_results["contact_duration"]
        summary.log = self.test_item['kmsg_log'] # The test_item comes form Testbase
        summary.test_type = test_results['test_type']

        summary.stationary_jitter_avg_of_error_avgs = test_results["avg_mean_jitter"]
        summary.stationary_jitter_total_stdev_error = test_results["total_stdev_jitter"]
        summary.stationary_jitter_avg_of_max_errors = test_results["avg_max_jitter"]
        summary.stationary_jitter_max_of_max_errors = test_results["max_max_jitter"]

        summary.total_number_of_missing_points = test_results["missing_inputs"]

        session.add(summary)
        session.commit()