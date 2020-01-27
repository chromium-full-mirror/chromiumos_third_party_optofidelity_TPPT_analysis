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
from functools import cmp_to_key

from TPPTAnalysisSW.testbase import TestBase, testclasscreator
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.info.version import Version
from TPPTAnalysisSW.utils import Timer
from TPPTAnalysisSW.settings import settings
import TPPTAnalysisSW.measurementdb as db
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.analyzers as analyzers

# Python 3 version of Python 2 built-in function cmp.
def cmp(a, b):
    return (a>b)-(a<b)

class SeparationTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(14)
    def create_testclass(*args, **kwargs):
        return SeparationTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.ddttest (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new SeparationTest class """
        super(SeparationTest, self).__init__(ddtest_row, *args, **kwargs)

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        results = self.read_test_results()
        if results['verdict'] is None:
            verdict = 'N/A'
        elif results['verdict']:
            verdict = 'Pass'
        else:
            verdict = 'Fail'

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
        templateParams = super(SeparationTest, self).create_common_templateparams(**kwargs)
        t = Timer()
        results = self.read_test_results()

        # data for the report
        templateParams['results'] = results
        templateParams['figures'] = [ImageFactory.create_image_name(self.test_id, 'sepgen'),
                                     ImageFactory.create_image_name(self.test_id, 'sepdet')]

        t.Time("Results")

        # set the content to be used
        templateParams['test_page'] = 'test_separation.html'
        templateParams['test_script'] = 'test_page_subplots.js'
        templateParams['version'] = Version

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        t.Time("Markup")

        if results['verdict'] is None:
            verdict = 'N/A'
        elif results['verdict']:
            verdict = 'Pass'
        else:
            verdict = 'Fail'

        return stream.render('xhtml'), verdict

    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'sepgen':
            t = Timer(1)
            dbsession = db.get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
            t.Time("Results")
            title = 'Preview: Separation overview ' + self.dut['program']
            plot_factory.plot_separation_results(imagepath, results, dutinfo, *args, title=title, **kwargs)
            t.Time("Image")
        elif image_name == 'sepdet':
            t = Timer(1)
            dbsession = db.get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
            t.Time("Results")
            title = 'Preview: Separation details ' + self.dut['program']
            plot_factory.plot_separation_details(imagepath, results, dutinfo, *args, title=title, **kwargs)
            t.Time("Image")
        elif image_name == 'sepdtls':
            t = Timer(1)
            dbsession = db.get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
            t.Time("Results")
            title = 'Separation details for angle %s distance %s ' %(args[0], args[1]) + self.dut['program']
            plot_factory.plot_separation_tapdetails(imagepath, results['angles'][args[0]]['distances'][args[1]], dutinfo, title=title, **kwargs)
            t.Time("Image")
        else:
            raise cherrypy.HTTPError(message = "No such image in the report")

        return None

    def read_test_results(self, dutinfo=None, dbsession=None, **kwargs):
        if dbsession is None:
            dbsession = db.get_database().session()
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        s = Timer(2)
        tests = dbsession.query(db.SeparationTest).filter(db.SeparationTest.test_id == self.test_id).\
                                                   order_by(db.SeparationTest.id).options(joinedload('separation_results')).all()

        s.Time("DB Results")

        # Directory that contains the angles of the measurements
        angles = {}
        errors = set()

        for test in tests:
            # Single separation angle & distance
            angle = "%.1f" % test.separation_angle
            if angle not in angles:
                angles[angle] = {'distances':{}}

            distance = "%.1f" % test.tool_separation
            if distance in angles[angle]:
                # Error - the same angle and distance twice in the same measurement
                # Cannot re-do the analysis, because it would potentially mess up the results
                errors.add('The separation angle %s and distance %f occurs twice in data' % (angle, distance))
                continue
            else:
                dresults = {}
                angles[angle]['distances'][distance] = dresults

            pdist = (math.cos(math.radians(test.separation_angle)) * test.tool_separation,
                     math.sin(math.radians(test.separation_angle)) * test.tool_separation)
            dresults['point']    = analyzers.robot_to_target((test.robot_x, test.robot_y), dutinfo)
            dresults['point_diameter'] = test.finger1_diameter
            dresults['angle']    = test.separation_angle
            dresults['point2']   = [c + d for c, d in zip(dresults['point'], pdist)]
            dresults['point2_diameter'] = test.finger2_diameter
            dresults['errors']   = set()
            dresults['image']    = ImageFactory.create_image_name(self.test_id, 'sepdtls', angle, distance)
            taps = {}
            dresults['taps']     = taps
            for tap in test.separation_results:
                if tap.finger_id not in taps:
                    taps[tap.finger_id] = []
                taps[tap.finger_id].append(analyzers.panel_to_target((tap.panel_x, tap.panel_y), dutinfo))

            if len(taps.keys()) == 0:
                # No measurements found
                dresults['errors'].add('No measurements for tap')
                errors.add('No measurements for tap')
                dresults['verdict'] = False
                dresults['verdict_text'] = 'N/A'
            elif len(taps.keys()) == 1:
                # No separation
                dresults['verdict'] = False
                dresults['verdict_text'] = 'Fail'
            elif len(taps.keys()) == 2:
                # Separation found
                dresults['verdict'] = True
                dresults['verdict_text'] = 'Pass'
            else:
                # Too many id's
                dresults['errors'].add('Too many ids for tap')
                errors.add('Too many ids for tap')
                dresults['verdict'] = False
                dresults['verdict_text'] = 'Fail'

        # Calculate results
        verdict = None
        for angle, values in angles.items():
            sorteddist = sorted(values['distances'].keys(), key=cmp_to_key(lambda x,y: cmp(float(x), float(y))))
            #print "Angle %s - %s" % (angle, str(sorteddist))
            mindist = None
            for dist in sorteddist:
                if values['distances'][dist]['verdict']:
                    if mindist is None:
                        mindist = dist
                else:
                    mindist = None

            values['distance_ids'] = sorteddist
            values['separation'] = mindist
            # Verdict calculation
            if angle == '0.0' or angle == '90.0':
                dverdict = mindist is not None and (float(mindist) <= settings['maxseparation'])
                values['maxseparation'] = settings['maxseparation']
            else:
                dverdict = mindist is not None and (float(mindist) <= settings['maxdiagseparation'])
                values['maxseparation'] = settings['maxdiagseparation']
            values['verdict'] = dverdict
            if verdict is None:
                verdict = dverdict
            elif dverdict == False:
                verdict = False

        angle_ids = sorted(angles.keys(), key=cmp_to_key(lambda x,y: cmp(float(x), float(y))))

        results = {'angles': angles,
                   'angle_ids': angle_ids,
                   'errors': errors,
                   'verdict': verdict,
                   }

        return results
