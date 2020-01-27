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
from TPPTAnalysisSW.measurementdb import get_database, MultifingerSwipeTest, MultifingerSwipeResults
from TPPTAnalysisSW.info.version import Version
from TPPTAnalysisSW.utils import Timer
from TPPTAnalysisSW.settings import settings
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.analyzers as analyzers


class MultiFingerSwipeTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(5)
    def create_testclass(*args, **kwargs):
        return MultiFingerSwipeTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.ddttest (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new MultiFingerSwipeTest class """
        super(MultiFingerSwipeTest, self).__init__(ddtest_row, *args, **kwargs)

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        results = self.read_test_results()
        verdict = results['missing_swipes_verdict'] and results['errors_verdict']
        if verdict:
            if results['offset_verdict'] is None:
                verdict = None
            elif results['jitter_verdict'] is None:
                # what to do???
                verdict = results['offset_verdict']
            else:
                verdict = results['offset_verdict'] and results['jitter_verdict']

        return "N/A" if verdict is None else "Pass" if verdict else "Fail"

    # Override to make necessary operations for clearing test results
    # Clearing the test result from the results table is done elsewhere
    def clearanalysis(self, *args, **kwargs):
        """ Clears analysis results """
        ImageFactory.delete_images(self.test_id)

    # Create the test report. Return the created HTML, or raise cherrypy.HTTPError
    def createreport(self, *args, **kwargs):
        self.clearanalysis()

        # Create common template parameters (including ddttest dictionary, testsession dictionary, test_id, test_type_name etc)
        templateParams = super(MultiFingerSwipeTest, self).create_common_templateparams(**kwargs)

        t = Timer()

        # data for the report
        results = self.read_test_results()
        templateParams['results'] = results

        t.Time("Results")

        # set the content to be used
        templateParams['test_page'] = 'test_multifinger_swipe.html'
        templateParams['test_script'] = 'test_page_subplots.js'
        templateParams['version'] = Version

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        t.Time("Markup")

        verdict = results['missing_swipes_verdict'] and results['errors_verdict']
        if verdict:
            if results['offset_verdict'] is None:
                verdict = None
            elif results['jitter_verdict'] is None:
                # what to do???
                verdict = results['offset_verdict']
            else:
                verdict = results['offset_verdict'] and results['jitter_verdict']

        return stream.render('xhtml'), "N/A" if verdict is None else "Pass" if verdict else "Fail"

    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'swpgen':
            t = Timer(1)
            dbsession = get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
            passed_points = []
            failed_points = []
            lines = []
            for multiswipe in results['swipes']:
                for finger in multiswipe['fingers']:
                    for points in finger['passed_points'].values():
                        passed_points.extend(points)
                    for points in finger['failed_points'].values():
                        failed_points.extend(points)
                    lines.append((finger['swipe_start'], finger['swipe_end']))
            pinfo = {'passed_points': passed_points,
                     'failed_points': failed_points,
                     'lines': lines}
            t.Time("Results")
            title = 'Preview: Multifinger swipe overview ' + self.dut['program']
            plot_factory.plot_swipes_on_target(imagepath, pinfo, dutinfo, *args, title=title, **kwargs)
            t.Time("Image")
        elif image_name == 'swpdtls':
            t = Timer(1)
            dbsession = get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_swipe_results(args[0], dbsession=dbsession, dutinfo=dutinfo, **kwargs)
            t.Time("Results")
            title = 'Preview: Multifinger swipe details ID:' + args[0]
            plot_factory.plot_multifinger_swipedetails(imagepath, results, dutinfo, title=title, **kwargs)
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
        results = dbsession.query(MultifingerSwipeTest).filter(MultifingerSwipeTest.test_id == self.test_id). \
            order_by(MultifingerSwipeTest.id).options(joinedload('multi_finger_swipe_results')).all()

        s.Time("DB Results")
        swipes = []
        errors = set()
        max_offset = None
        max_jitter = None
        missing_swipes = 0
        total_swipes = 0
        swipe_id = 0

        for multiswipe in results:
            swipe = self.calculate_swipe_details(multiswipe, dutinfo, **kwargs)
            swipe_id += 1
            swipe['id'] = swipe_id
            swipes.append(swipe)

            # Calculate common parameters
            errors = errors.union(swipe['errors'])
            max_offset = swipe['max_offset'] if max_offset is None else max(swipe['max_offset'], max_offset)
            max_jitter = swipe['max_jitter'] if max_jitter is None else max(swipe['max_jitter'], max_jitter)
            missing_swipes += swipe['missing_swipes']
            total_swipes += swipe['num_fingers']

        s.Time("Analysis")

        results = {'swipes': swipes,
                   'errors': errors,
                   'offset_verdict': None if max_offset is None else max_offset <= settings['maxoffset'],
                   'jitter_verdict': None if max_jitter is None else max_jitter <= settings['maxjitter'],
                   'max_offset': max_offset,
                   'max_jitter': max_jitter,
                   'edge_analysis_done': False,
                   'total_swipes': total_swipes,
                   'missing_swipes': missing_swipes,
                   'missing_swipes_verdict': (missing_swipes <= settings['maxmissingswipes']),
                   'errors_verdict': len(errors) == 0,
                   'images': [(ImageFactory.create_image_name(self.test_id, 'swpgen'),
                               ImageFactory.create_image_name(self.test_id, 'swpgen', 'detailed')),
                              ],
                   }

        return results

    def read_swipe_results(self, swipe_id, dbsession=None, dutinfo=None, **kwargs):
        if dbsession is None:
            dbsession = get_database().session()
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        multiswipe = dbsession.query(MultifingerSwipeTest).filter(MultifingerSwipeTest.id == swipe_id). \
            options(joinedload('multi_finger_swipe_results')).first()

        return self.calculate_swipe_details(multiswipe, dutinfo, **kwargs)

    def calculate_swipe_details(self, multiswipe, dutinfo, **kwargs):
        # Transfer swipe info to individual swipes
        start_point, end_point = analyzers.robot_to_target([(multiswipe.start_x, multiswipe.start_y),
                                                            (multiswipe.end_x, multiswipe.end_y)], dutinfo)
        separation_x = multiswipe.separation_distance * math.cos(math.radians(multiswipe.separation_angle))
        separation_y = multiswipe.separation_distance * math.sin(math.radians(multiswipe.separation_angle))
        start_points_x = [start_point[0] + i * separation_x for i in range(multiswipe.number_of_fingers)]
        start_points_y = [start_point[1] + i * separation_y for i in range(multiswipe.number_of_fingers)]
        end_points_x = [end_point[0] + i * separation_x for i in range(multiswipe.number_of_fingers)]
        end_points_y = [end_point[1] + i * separation_y for i in range(multiswipe.number_of_fingers)]
        startpoints = list(zip(start_points_x, start_points_y))
        endpoints = list(zip(end_points_x, end_points_y))

        allpoints = analyzers.panel_to_target([(p.panel_x, p.panel_y) for p in multiswipe.multi_finger_swipe_results],
                                              dutinfo)
        swipepoints = analyzers.target_to_swipe(allpoints, startpoints[0], endpoints[0])
        swipestarts = analyzers.target_to_swipe(startpoints, startpoints[0], endpoints[0])
        fingerids = np.array([p.finger_id for p in multiswipe.multi_finger_swipe_results])

        swipe_errors = set()
        # Check if we have the correct number of finger ids
        uniqids = np.unique(fingerids)
        if len(uniqids) > multiswipe.number_of_fingers:
            swipe_errors.add('Too many fingers were detected in input')

        pointsbyid = {}
        swipepointsbyid = {}
        for id in uniqids:
            pointsbyid[id] = [p for pid, p in zip(fingerids, allpoints) if pid == id]
            swipepointsbyid[id] = np.array([np.array(p) for pid, p in zip(fingerids, swipepoints) if pid == id])

        # Map the finger ids in the database to the id's in the points list
        max_jitter = None
        fingers = []
        finger_offsets = []
        missing_fingers = 0

        fingerids = self.find_fingerids(swipestarts, swipepointsbyid, swipe_errors)
        for startpoint, endpoint, swipestart, ids_in_place in zip(startpoints, endpoints, swipestarts, fingerids):
            fingerpoints = {}
            swipepoints = {}
            passed = {}
            failed = {}
            jitters = {}
            results = []
            finger = {'swipe_start': startpoint,
                      'swipe_end': endpoint,
                      'points': fingerpoints,
                      'passed_points': passed,
                      'failed_points': failed,
                      'swipe_points': swipepoints,
                      'jitters': jitters,
                      'results': results,
                      'verdict': False}
            fingers.append(finger)
            if ids_in_place is None:
                # Missing finger
                # swipe_errors.add('Not all fingers were detected in input')
                finger_offsets.append(None)
                missing_fingers += 1
                continue

            max_finger_offset = None
            max_finger_jitter = None
            for id in ids_in_place:
                fingerpoints[id] = pointsbyid[id]
                swipepoints[id] = swipepointsbyid[
                                      id] - swipestart  # Transform coordinates to individual swipe coordinates
                results = analyzers.analyze_swipe_jitter(swipepointsbyid[id], float(settings['jittermask']))
                jitters[id] = results['jitters']
                offsets = np.abs(swipepointsbyid[id][:, 1] - swipestart[1])
                max_id_offset = analyzers.round_dec(np.max(offsets))
                results['max_offset'] = max_id_offset
                # Passed/failed points to visualization
                passfail_values = [analyzers.round_dec(o) <= settings['maxoffset'] for p, o in
                                   zip(swipepoints[id], offsets)]
                passed[id] = [fingerpoints[id][i] for (i, t) in enumerate(passfail_values) if t]
                failed[id] = [fingerpoints[id][i] for (i, t) in enumerate(passfail_values) if not t]
                max_finger_offset = max_id_offset if max_finger_offset is None else max(max_id_offset,
                                                                                        max_finger_offset)
                max_id_jitter = analyzers.round_dec(results['max_jitter'])
                max_finger_jitter = max_id_jitter if max_finger_jitter is None else max(max_id_jitter,
                                                                                        max_finger_jitter)
            finger['max_offset'] = max_finger_offset
            finger_offsets.append(max_finger_offset)
            finger['max_jitter'] = max_finger_jitter
            if max_finger_jitter is not None:
                max_jitter = max_finger_jitter if max_jitter is None else max(max_jitter, max_finger_jitter)

            if max_finger_offset <= settings['maxoffset']:
                finger['verdict'] = True
            # else:
            # swipe_errors.add('Maximum offset exceeded')

        max_offset = None
        # Find max offset from non-None offsets
        if finger_offsets.count(None) < len(finger_offsets):
            max_offset = max([o for o in finger_offsets if o is not None])

        if max_offset is None:
            verdict = None
            verdict_text = 'N/A'
            verdict_class = ''
        else:
            verdict = max_offset <= settings['maxoffset'] and max_jitter <= settings['maxjitter'] and (
                        len(swipe_errors) == 0)
            verdict_text = 'Pass' if verdict else 'Fail'
            verdict_class = 'passed' if verdict else 'failed'

        swipe = {'num_fingers': multiswipe.number_of_fingers,
                 'startpoints': startpoints,
                 'endpoints': endpoints,
                 'missing_swipes': missing_fingers,
                 'offsets': finger_offsets,
                 'fingerids': fingerids,
                 'fingers': fingers,
                 'max_offset': max_offset,
                 'max_jitter': max_jitter,
                 'errors': swipe_errors,
                 'verdict': verdict,
                 'verdict_text': verdict_text,
                 'verdict_class': verdict_class,
                 'image': ImageFactory.create_image_name(self.test_id, 'swpdtls', str(multiswipe.id))}

        return swipe

    def find_fingerids(self, swipestarts, swipepointsbyid, swipe_errors):
        ''' Find finger ids for the points sorted by ids. Returns an array,
            where each id gives the finger_id for the specified point in targetpoints '''

        numids = len(swipepointsbyid.keys())
        numpoints = len(swipestarts)

        if numids == 0:
            # No measurements found
            return [None] * numpoints

        # Find the distances from each median point per id to each of the target points
        distances = {}
        # print str(targetpoints)
        for id in swipepointsbyid.keys():
            # For each fingerid check the closest target swipe - very easy in swipe coordinates
            median_offset = np.median([p[1] for p in swipepointsbyid[id]])
            dists = [np.abs(median_offset - p[1]) for p in swipestarts]
            distances[id] = dists

        return analyzers.find_closest_id_match(distances)
