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
import math
import numpy as np
import numpy.linalg as npl
from sqlalchemy.orm import joinedload
from genshi.template import MarkupTemplate

from TPPTAnalysisSW.testbase import TestBase, testclasscreator
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.measurementdb import get_database, MultifingerTapTest, MultifingerTapResults
from TPPTAnalysisSW.info.version import Version
from TPPTAnalysisSW.utils import Timer
from TPPTAnalysisSW.settings import settings
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.analyzers as analyzers


class MultiFingerTapTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(8)
    def create_testclass(*args, **kwargs):
        return MultiFingerTapTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.ddttest (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new MultiFingerTapTest class """
        super(MultiFingerTapTest, self).__init__(ddtest_row, *args, **kwargs)

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        results = self.read_test_results()
        verdict = "Pass" if results['verdict'] else "Fail"
        # No measurements - special case
        if results['verdict'] and results['max_input_offset'] is None:
            verdict = 'N/A'
        return verdict

    # Override to make necessary operations for clearing test results
    # Clearing the test result from the results table is done elsewhere
    def clearanalysis(self, *args, **kwargs):
        """ Clears analysis results """
        ImageFactory.delete_images(self.test_id)

    # Create the test report. Return the created HTML, or raise cherrypy.HTTPError
    def createreport(self, *args, **kwargs):
        self.clearanalysis()

        # Create common template parameters (including ddttest dictionary, testsession dictionary, test_id, test_type_name etc)
        templateParams = super(MultiFingerTapTest, self).create_common_templateparams(**kwargs)

        t = Timer()

        # data for the report
        results = self.read_test_results()
        templateParams['results'] = results

        t.Time("Results")

        # set the content to be used
        templateParams['test_page'] = 'test_multifinger_tap.html'
        templateParams['test_script'] = 'test_page_subplots.js'
        templateParams['version'] = Version

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        t.Time("Markup")

        verdict = "Pass" if results['verdict'] else "Fail"
        # No measurements - special case
        if results['verdict'] and results['max_input_offset'] is None:
            verdict = 'N/A'

        return stream.render('xhtml'), verdict

    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'passfailgen':
            t = Timer(1)
            dbsession = get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
            pinfo = {'passed_points': [tap['targetpoints'][0] for tap in results['taps'] if tap['verdict']],
                     'failed_points': [tap['targetpoints'][0] for tap in results['taps'] if not tap['verdict']],
                     }
            t.Time("Results")
            title = 'Preview: Multifinger Tap overview ' + self.dut['program']
            plot_factory.plot_passfail_on_target(imagepath, pinfo, dutinfo, *args, title=title, **kwargs)
            t.Time("Image")
        elif image_name == 'passfaildet':
            t = Timer(1)
            dbsession = get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
            t.Time("Results")
            title = 'Preview: Multifinger Tap detailed overview ' + self.dut['program']
            plot_factory.plot_multifinger_p2p(imagepath, results, dutinfo, *args, title=title, **kwargs)
            t.Time("Image")
        elif image_name == 'p2pdxdy':
            t = Timer(1)
            results = self.read_dxdy_results(**kwargs)
            t.Time("Results")
            # Avoid glitches - use 2.0 limit for display
            plot_factory.plot_dxdy_graph(imagepath, results, 2.0, *args, **kwargs)
            t.Time("Image")
        elif image_name == 'tapdtls':
            t = Timer(1)
            results = self.read_tap_results(args[0], **kwargs)
            t.Time("Results")
            title = 'Preview: Multifinger Tap details'
            plot_factory.plot_multifinger_tapdetails(imagepath, results, *args, title=title, **kwargs)
            t.Time("Image")
        else:
            raise cherrypy.HTTPError(message="No such image in the report")

        return None

    def read_test_results(self, dutinfo=None, dbsession=None, **kwargs):
        if dbsession is None:
            dbsession = get_database().session()
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        s = Timer(2)
        results = dbsession.query(MultifingerTapTest).filter(MultifingerTapTest.test_id == self.test_id). \
            order_by(MultifingerTapTest.id).options(joinedload('multi_finger_tap_results')).all()

        s.Time("DB Results")
        taps = []
        errors = set()
        max_offset = None
        missing_inputs = 0
        missing_edge_inputs = 0
        total_points = 0
        point_id = 0

        for multitap in results:
            tap = self.calculate_tap_details(multitap, dutinfo, **kwargs)
            point_id += 1
            tap['id'] = point_id
            taps.append(tap)

            # Calculate common parameters
            errors = errors.union(tap['errors'])
            if tap['max_input_offset'] is not None:
                max_offset = tap['max_input_offset'] if max_offset is None else max(tap['max_input_offset'], max_offset)
            missing_inputs += tap['missing_inputs']
            total_points += tap['num_fingers']

        s.Time("Analysis")

        results = {'taps': taps,
                   'errors': errors,
                   'maxposerror': float(settings['maxposerror']),
                   'verdict': (max_offset <= settings['maxposerror']
                               and missing_inputs - missing_edge_inputs <= settings['maxmissing']
                               and len(errors) == 0),
                   'max_input_offset_verdict': 'N/A' if max_offset is None else 'Pass' if max_offset <= settings[
                       'maxposerror'] else 'Fail',
                   'max_input_offset': max_offset,
                   'edge_analysis_done': False,
                   'missing_inputs': missing_inputs,
                   'missing_inputs_verdict': (missing_inputs - missing_edge_inputs <= settings['maxmissing']),
                   'total_points': total_points,
                   'images': [(ImageFactory.create_image_name(self.test_id, 'passfailgen'),
                               ImageFactory.create_image_name(self.test_id, 'passfailgen', 'detailed')),
                              (ImageFactory.create_image_name(self.test_id, 'passfaildet'),
                               ImageFactory.create_image_name(self.test_id, 'passfaildet', 'detailed')),
                              (ImageFactory.create_image_name(self.test_id, 'p2pdxdy'),
                               ImageFactory.create_image_name(self.test_id, 'p2pdxdy', 'detailed')),
                              ],
                   }

        return results

    def read_dxdy_results(self, **kwargs):
        results = self.read_test_results(**kwargs)

        # Parse failed and passed points
        passed_points = []
        failed_points = []
        for tap in results['taps']:
            for finger in tap['fingers']:
                for id in finger['points'].keys():
                    passed_points.extend([(finger['target'], p) for d, p
                                          in zip(finger['distances'][id], finger['points'][id])
                                          if d <= finger['maxposerror']])
                    failed_points.extend([(finger['target'], p) for d, p
                                          in zip(finger['distances'][id], finger['points'][id])
                                          if d > finger['maxposerror']])

        results['passed_points'] = passed_points
        results['failed_points'] = failed_points

        return results

    def read_tap_results(self, tap_id, dbsession=None, dutinfo=None, **kwargs):
        if dbsession is None:
            dbsession = get_database().session()
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        multitap = dbsession.query(MultifingerTapTest).filter(MultifingerTapTest.id == tap_id). \
            options(joinedload('multi_finger_tap_results')).first()

        return self.calculate_tap_details(multitap, dutinfo, **kwargs)

    def calculate_tap_details(self, multitap, dutinfo, **kwargs):
        missing_tap_inputs = 0

        # Transfer the tap info to individual points
        robot_point = analyzers.robot_to_target((multitap.robot_x, multitap.robot_y), dutinfo)
        points_x = [
            robot_point[0] + i * multitap.separation_distance * math.cos(math.radians(multitap.separation_angle))
            for i in range(multitap.number_of_fingers)]
        points_y = [
            robot_point[1] + i * multitap.separation_distance * math.sin(math.radians(multitap.separation_angle))
            for i in range(multitap.number_of_fingers)]
        targetpoints = list(zip(points_x, points_y))

        allpoints = analyzers.panel_to_target([(p.panel_x, p.panel_y) for p in multitap.multi_finger_tap_results],
                                              dutinfo)
        fingerids = np.array([p.finger_id for p in multitap.multi_finger_tap_results])

        taperrors = set()
        # Check if we have the correct number of finger ids
        uniqids = np.unique(fingerids)
        if len(uniqids) > multitap.number_of_fingers:
            taperrors.add('Too many fingers were detected in input')

        pointsbyid = {}
        for id in uniqids:
            pointsbyid[id] = np.array([np.array(p) for pid, p in zip(fingerids, allpoints) if pid == id])

        # Map the finger ids in the database to the id's in the points list
        max_tap_offset = None
        fingers = []
        finger_offsets = []

        fingerids = self.find_fingerids(targetpoints, pointsbyid, taperrors)
        for target_point, ids_in_place in zip(targetpoints, fingerids):
            fingerpoints = {}
            distances = {}
            finger = {'target': target_point,
                      'maxposerror': float(settings['maxposerror']),
                      'points': fingerpoints,
                      'distances': distances,
                      'verdict': False}
            fingers.append(finger)
            if ids_in_place is None or len(ids_in_place) == 0:
                # Missing finger
                # taperrors.add('Not all fingers were detected in input')
                finger_offsets.append(None)
                missing_tap_inputs += 1
                continue

            max_finger_offset = None
            for id in ids_in_place:
                fingerpoints[id] = pointsbyid[id]
                fdistances = npl.norm(fingerpoints[id] - target_point, axis=1)
                distances[id] = [analyzers.round_dec(d) for d in fdistances]
                max_id_offset = analyzers.round_dec(np.max(fdistances))
                max_finger_offset = max_id_offset if max_finger_offset is None else max(max_id_offset,
                                                                                        max_finger_offset)
            finger['max_input_error'] = max_finger_offset
            finger_offsets.append(max_finger_offset)

            if max_finger_offset <= settings['maxposerror']:
                finger['verdict'] = True
            # else:
            # taperrors.add('Maximum offset exceeded')

        max_tap_offset = None
        # Find max offset from non-None offsets
        if finger_offsets.count(None) < len(finger_offsets):
            max_tap_offset = max([o for o in finger_offsets if o is not None])

        verdict = (max_tap_offset is not None and max_tap_offset <= settings['maxposerror'] and len(taperrors) == 0)
        tap = {'num_fingers': multitap.number_of_fingers,
               'targetpoints': targetpoints,
               'missing_inputs': missing_tap_inputs,
               'offsets': finger_offsets,
               'fingerids': fingerids,
               'fingers': fingers,
               'max_input_offset': max_tap_offset,
               'errors': taperrors,
               'verdict': verdict,
               'verdict_text': 'N/A' if max_tap_offset is None else 'Pass' if verdict else 'Fail',
               'image': ImageFactory.create_image_name(self.test_id, 'tapdtls', str(multitap.id))}

        return tap

    def find_fingerids(self, targetpoints, pointsbyid, taperrors):
        ''' Find finger ids for the points sorted by ids. Returns an array,
            where each id gives the finger_id for the specified point in targetpoints '''

        numids = len(pointsbyid.keys())
        numpoints = len(targetpoints)

        if numids == 0:
            # No measurements found
            return [None] * numpoints

        # Find the distances from each median point per id to each of the target points
        distances = {}
        # print str(targetpoints)
        for id in pointsbyid.keys():
            # For each fingerid check the closest target point
            median = np.median(pointsbyid[id], axis=0)
            # print str(median)
            dists = [npl.norm(median - p) for p in targetpoints]
            distances[id] = dists

        return analyzers.find_closest_id_match(distances)
