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

from TPPTAnalysisSW.testbase import TestBase, testclasscreator
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.utils import Timer
from TPPTAnalysisSW.measurementdb import get_database, OneFingerStationaryJitterTest, OneFingerStationaryJitterResults
from TPPTAnalysisSW.settings import settings
from TPPTAnalysisSW.info.version import Version
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.analyzers as analyzers

class StationaryJitterTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(9)
    def create_testclass(*args, **kwargs):
        return StationaryJitterTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new StationaryJitterTest class """
        super(StationaryJitterTest, self).__init__(ddtest_row, *args, **kwargs)

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
        templateParams = super(StationaryJitterTest, self).create_common_templateparams(**kwargs)

        results = self.read_test_results()

        t.Time("Results")

        # Add the image name and parameters to the report
        templateParams['results'] = results
        templateParams['figure'] = ImageFactory.create_image_name(self.test_id, 'stjitt')
        templateParams['detailed_figure'] = ImageFactory.create_image_name(self.test_id, 'stjitt', 'detailed')
        templateParams['test_page'] = 'test_stationary_jitter.html'
        templateParams['test_script'] = 'test_page_subplots.js'
        templateParams['version'] = Version

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        t.Time("Markup")
        return stream.render('xhtml'), results['verdict']


    # Create images for the report. If the function returns a value, it is used as the new image name (without image path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        # Dummy test has only one image: dummyimage.
        if image_name == 'stjitt':
            dbsession = get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_test_results(dutinfo, dbsession)
            title = 'Preview: Stationary Jitter ' + self.dut['program']
            plot_factory.plot_passfail_labels_on_target(imagepath, results, dutinfo, *args, title=title, **kwargs)
        elif image_name == 'stjittdtls':
            dbsession = get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_point_details(args[0], dutinfo, dbsession)
            title = 'Preview: Stationary Jitter details ' + self.dut['program']
            plot_factory.plot_passfail_labels(imagepath, results, title=title, **kwargs)
        else:
            raise cherrypy.HTTPError(message = "No such image in the report")

        return None


    def read_test_results(self, dutinfo = None, dbsession = None):
        if dbsession is None:
            dbsession = get_database().session()
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        pts = dbsession.query(OneFingerStationaryJitterTest).filter(OneFingerStationaryJitterTest.test_id==self.test_id).\
                                                             options(joinedload(OneFingerStationaryJitterTest.one_finger_stationary_jitter_results)).\
                                                             order_by(OneFingerStationaryJitterTest.id)

        passed = []
        failed = []
        points = []
        max_jitter = None
        verdict = "N/A"
        point_id = 1

        for point in pts:
            panel_points = [(p.panel_x, p.panel_y) for p in point.one_finger_stationary_jitter_results]
            target_points = analyzers.panel_to_target(panel_points, dutinfo)

            if len(target_points) == 0:
                # No measurements for point
                target = analyzers.robot_to_target((point.robot_x, point.robot_y), dutinfo)
                failed.append(list(target) + [str(point_id)])
                points.append((point_id, None, "N/A", None))
                point_id += 1
            else:
                jitter = 0.0
                if len(target_points) > 1:
                    orig = np.array(target_points[0])
                    distances = np.array([np.linalg.norm(np.array(p) - orig) for p in target_points[1:]])
                    jitter = analyzers.round_dec(np.max(distances))

                point_verdict = "Fail" if jitter > settings['maxstationaryjitter'] else "Pass"
                points.append((point_id, jitter, point_verdict, ImageFactory.create_image_name(self.test_id, 'stjittdtls', str(point.id))))

                if max_jitter is None or jitter > max_jitter:
                    max_jitter = jitter

                if point_verdict == "Pass":
                    passed.append(list(target_points[0]) + [point_id])
                    if verdict == "N/A":
                        verdict = "Pass"
                else:
                    failed.append(list(target_points[0]) + [point_id])
                    verdict = "Fail"

                point_id += 1

        results = {'passed_points': passed,
                   'failed_points': failed,
                   'max_jitter': max_jitter,
                   'verdict': verdict,
                   'points': points
                   }

        return results

    def read_point_details(self, point_id, dutinfo = None, dbsession = None):
        if dbsession is None:
            dbsession = get_database().session()
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        points = dbsession.query(OneFingerStationaryJitterResults).filter(OneFingerStationaryJitterResults.point_id==point_id).\
                                                                   order_by(OneFingerStationaryJitterResults.id)

        robot_point = dbsession.query(OneFingerStationaryJitterTest).filter(OneFingerStationaryJitterTest.id==point_id).\
                                                                    order_by(OneFingerStationaryJitterTest.id)

        target_points = analyzers.panel_to_target([(p.panel_x, p.panel_y) for p in points], dutinfo)

        points = []
        point_count = []

        for point in target_points:
            if point in points:
                point_count[points.index(point)] += 1
            else:
                points.append(point)
                point_count.append(1)

        if len(points) > 1:
            orig = np.array(points[0])
            distances = np.array([np.linalg.norm(np.array(p) - orig) for p in points])
            passed = []
            failed = []
            for point, distance, count in zip(points, distances, point_count):
                if distance > settings['maxstationaryjitter']:
                    failed.append((point[0], point[1], str(count) if count > 1 else ''))
                else:
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
