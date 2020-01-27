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

from TPPTAnalysisSW.testbase import TestBase, testclasscreator
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.settings import settings
from TPPTAnalysisSW.utils import Timer
from TPPTAnalysisSW.info.version import Version
import TPPTAnalysisSW.measurementdb as measurementdb
import TPPTAnalysisSW.analyzers as analyzers
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.plot_factory as plot_factory

class OneFingerSwipeTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(1)
    def create_testclass(*args, **kwargs):
        return OneFingerSwipeTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new OneFingerSwipeTest class """
        super(OneFingerSwipeTest, self).__init__(ddtest_row, *args, **kwargs)

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        verdict = "N/A"
        results = self.read_test_results()
        if results['jitter_verdict'] == "Pass" and results['offset_verdict'] == "Pass" and results['missing_count'] <= settings['maxmissingswipes']:
            verdict = "Pass"
        elif results['jitter_verdict'] == "Fail" or results['offset_verdict'] == "Fail" or results['missing_count'] > settings['maxmissingswipes']:
            verdict = "Fail"
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
        templateParams = super(OneFingerSwipeTest, self).create_common_templateparams(**kwargs)

        s = Timer()
        s.Time("START")

        results = self.read_test_results()

        s.Time("Results")

        templateParams['results'] = results
        templateParams['figure'] = ImageFactory.create_image_name(self.test_id, "swipes")
        templateParams['detailed_figure'] = ImageFactory.create_image_name(self.test_id, "swipes", "detailed")
        templateParams['test_page'] = 'test_one_finger_swipe.html'
        templateParams['test_script'] = 'test_page_subplots.js'
        templateParams['version'] = Version

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        s.Time("READY")

        # Start creating the preview image already - the call will probably come soon
        # NOTE: this is not necessary in summary tests
        if 'noimages' not in kwargs:
            threading.Thread(target = self.createpreviewimage, args = (results,)).start()

        if results['jitter_verdict'] == "Pass" and results['offset_verdict'] == "Pass" and results['missing_count'] <= settings['maxmissingswipes']:
            verdict = "Pass"
        elif results['jitter_verdict'] == "Fail" or results['offset_verdict'] == "Fail" or results['missing_count'] > settings['maxmissingswipes']:
            verdict = "Fail"

        return stream.render('xhtml'), verdict

    def createpreviewimage(self, results):
        """ Creates a swipe preview image with the specified results """
        imagepath = ImageFactory.create_image_path(self.test_id, "swipes")
        dbsession = measurementdb.get_database().session()
        dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
        title = 'Preview: One Finger Swipe ' + self.dut['program']
        plot_factory.plot_swipes_on_target(imagepath, results, dutinfo, title=title)

    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'swipes':
            # See above: preview image is normally generated after the report creation
            dbsession = measurementdb.get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            pinfo = self.read_test_results(dbsession=dbsession, dutinfo=dutinfo)
            title = 'Preview: One Finger Swipe ' + self.dut['program']
            plot_factory.plot_swipes_on_target(imagepath, pinfo, dutinfo, *args, title=title, **kwargs)
        elif image_name == 'jittdtls':
            dbsession = measurementdb.get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_swipe_details(args[0], dbsession=dbsession, dutinfo=dutinfo)
            title = 'Preview: One Finger Swipe details ' + self.dut['program']
            plot_factory.plot_one_finger_swipe_with_linear_fit(imagepath, results, dutinfo, title=title, **kwargs)
        else:
            raise cherrypy.HTTPError(message = "No such image in the report")

        return None

    def read_test_results(self, dutinfo = None, dbsession = None):

        s = Timer(2)
        if dbsession is None:
            dbsession = measurementdb.get_database().session()
        if dutinfo is None:
            dutinfo = dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        dbswipes = dbsession.query(measurementdb.OneFingerSwipeTest).filter(measurementdb.OneFingerSwipeTest.test_id==self.test_id).\
                                                                     options(joinedload('one_finger_swipe_results')).\
                                                                     order_by(measurementdb.OneFingerSwipeTest.id)

        s.Time('DB')

        max_jitter = None
        jitter_verdict = "N/A"
        max_offset = None
        offset_verdict = "N/A"
        max_offsets_from_linear_fit = []
        swipes = []
        missing_swipes = []
        swipe_id = 1
        lines = []
        passed_points = []
        failed_points = []

        for swipe in dbswipes:
            assert(swipe.start_x is not None)
            assert(swipe.start_y is not None)
            assert(swipe.end_x is not None)
            assert(swipe.end_y is not None)

            panel_points = [(p.panel_x, p.panel_y) for p in swipe.one_finger_swipe_results]
            # Transform panel -> robot -> swipe
            target_points = analyzers.panel_to_target(panel_points, dutinfo)
            swipe_start, swipe_end = analyzers.robot_to_target([(swipe.start_x, swipe.start_y), (swipe.end_x, swipe.end_y)], dutinfo)
            lines.append((swipe_start, swipe_end))
            swipe_points = analyzers.target_to_swipe(target_points, swipe_start, swipe_end)
            swipe_results = analyzers.analyze_swipe_jitter(swipe_points, float(settings['jittermask']))
            linearity_results = analyzers.analyze_swipe_linearity(swipe_points)

            # Check is NaN
            if linearity_results['lin_error_max'] == linearity_results['lin_error_max']:
                max_offsets_from_linear_fit.append(linearity_results['lin_error_max'])

            passfail_values = [analyzers.round_dec(abs(p[1])) <= settings['maxoffset'] for p in swipe_points]
            passed = [target_points[i] for (i,t) in enumerate(passfail_values) if t]
            failed = [target_points[i] for (i,t) in enumerate(passfail_values) if not t]
            passed_points.extend(passed)
            failed_points.extend(failed)

            swipe_verdict = "N/A"

            offset = None
            if len(swipe_points) > 0:
                offset = analyzers.round_dec(max([abs(p[1]) for p in swipe_points]))
                if max_offset is None or offset > max_offset:
                    max_offset = offset
                if offset > settings['maxoffset']:
                    offset_verdict = "Fail"
                    swipe_verdict = "Fail"
                else:
                    swipe_verdict = "Pass"
                    if offset_verdict == "N/A":
                        offset_verdict = "Pass"

                jitter = analyzers.round_dec(swipe_results['max_jitter']) if 'max_jitter' in swipe_results else None
                if jitter is not None:
                    if max_jitter is None or jitter > max_jitter:
                        max_jitter = jitter
                    if jitter > settings['maxjitter']:
                        jitter_verdict = "Fail"
                        swipe_verdict = "Fail"
                    else:
                        if swipe_verdict != "Fail":
                            swipe_verdict = "Pass"
                        if jitter_verdict == "N/A":
                            jitter_verdict = "Pass"
            else:
                swipe_verdict = "Fail"
                missing_swipes.append(swipe.id)

            swipes.append((swipe_id, jitter, offset, swipe_verdict, ImageFactory.create_image_name(self.test_id, "jittdtls", str(swipe.id))))
            swipe_id += 1

        s.Time('Analysis')
        if len(max_offsets_from_linear_fit) > 0:
            linear_fit_avg = float(sum(max_offsets_from_linear_fit)) / len(max_offsets_from_linear_fit)
        else:
            linear_fit_avg = None

        results = {'max_jitter': max_jitter,
                   'jitter_verdict': jitter_verdict,
                   'max_offset': max_offset,
                   'offset_verdict': offset_verdict,
                   'swipes': swipes,
                   'swipe_count': len(swipes),
                   'missing_swipes': missing_swipes,
                   'missing_count': len(missing_swipes),
                   'lines': lines,
                   'passed_points': passed_points,
                   'failed_points': failed_points,
                   'max_offset_from_linear_fit': max(max_offsets_from_linear_fit) if max_offsets_from_linear_fit != [] else 0,
                   'avg_of_offsets_from_linear_fit': linear_fit_avg
                  }

        return results

    def read_swipe_details(self, swipe_id, dbsession=None, dutinfo=None):
        if dbsession is None:
            dbsession = measurementdb.get_database().session()
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(self.testsession['id'], dbsession)

        line = dbsession.query(measurementdb.OneFingerSwipeTest).filter(measurementdb.OneFingerSwipeTest.id == swipe_id).\
                                                                 order_by(measurementdb.OneFingerSwipeTest.id).\
                                                                 options(joinedload('one_finger_swipe_results')).first()

        panel_points = [(point.panel_x, point.panel_y) for point in line.one_finger_swipe_results]
        target_points = analyzers.panel_to_target(panel_points, dutinfo)
        line_start, line_end = analyzers.robot_to_target([(line.start_x, line.start_y), (line.end_x, line.end_y)], dutinfo)
        swipe_points = analyzers.target_to_swipe(target_points, line_start, line_end)
        jitterinfo = analyzers.analyze_swipe_jitter(swipe_points, float(settings['jittermask']))
        linearity_results = analyzers.analyze_swipe_linearity(swipe_points)

        passfail_values = [abs(p[1]) <= settings['maxoffset'] for p in swipe_points]
        passed = [target_points[i] for (i,t) in enumerate(passfail_values) if t]
        failed = [target_points[i] for (i,t) in enumerate(passfail_values) if not t]

        return {'passed_points': passed, 'failed_points': failed, 'swipe_points': swipe_points,
                'line_start': line_start, 'line_end': line_end, 'jitters': jitterinfo['jitters'],
                'linear_error': linearity_results['linear_error'], 'lin_error_max': linearity_results['lin_error_max'],
                'lin_error_rms': linearity_results['lin_error_rms'], 'lin_error_avg': linearity_results['lin_error_avg']}
