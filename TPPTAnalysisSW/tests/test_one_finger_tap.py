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
from sqlalchemy import Column, DECIMAL, Integer, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base

from ..testbase import TestBase, testclasscreator
from ..imagefactory import ImageFactory
from ..settings import settings, precision
from ..utils import Timer
from ..info.version import Version
import TPPTAnalysisSW.measurementdb as db
import TPPTAnalysisSW.analyzers as analyzers
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.plotinfo as plotinfo

Base = declarative_base()


class OneFingerTapTestSQL(Base):
    __tablename__ = 'tapping'

    max_input_error = Column(DECIMAL)
    maxposerror = Column(DECIMAL)
    max_edge_error = Column(DECIMAL)

    META_ID = Column(Integer, primary_key=True)
    CREATED = Column(TIMESTAMP)
    UPDATED = Column(TIMESTAMP)


class OneFingerTapTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(0)
    def create_testclass(*args, **kwargs):
        return OneFingerTapTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new OneFingerTapTest class """
        return super(OneFingerTapTest, self).__init__(ddtest_row, *args, **kwargs)

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        results = self.read_test_results()
        verdict = "Pass" if (results['max_input_verdict'] and results['missing_inputs_verdict']) else "Fail"
        if settings['edgelimit'] >= 0:
            if not results['missing_edge_inputs_verdict']:
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
        templateParams = super(OneFingerTapTest, self).create_common_templateparams(**kwargs)

        t = Timer()

        # data for the report
        results = self.read_test_results()
        templateParams['results'] = results

        t.Time("Results")

        # set the content to be used
        templateParams['test_page'] = 'test_one_finger_tap.html'
        templateParams['version'] = Version

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        t.Time("Markup")

        verdict = "Pass" if (results['max_input_verdict'] and results['missing_inputs_verdict']) else "Fail"
        if settings['edgelimit'] >= 0:
            if not results['missing_edge_inputs_verdict']:
                verdict = "Fail"

        return stream.render('xhtml'), verdict


    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'p2pdiff':
            t = Timer(1)
            dbsession = db.get_database().session()
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
            t.Time("Results")
            title = 'Preview: One Finger Tap ' + self.dut['program']
            plot_factory.plot_taptest_on_target(imagepath, results, dutinfo, *args, title=title, **kwargs)
            t.Time("Image")
        elif image_name == 'p2pdxdy':
            t = Timer(1)
            results = self.read_test_results(**kwargs)
            t.Time("Results")
            plot_factory.plot_dxdy_graph(imagepath, results, 0.0, *args, **kwargs)
            t.Time("Image")
        elif image_name == 'p2pdxdyltd':
            t = Timer(1)
            results = self.read_test_results(**kwargs)
            t.Time("Results")
            plot_factory.plot_dxdy_graph(imagepath, results, 1.0, *args, **kwargs)
            t.Time("Image")
        elif image_name == 'p2pdxdyltdc':
            t = Timer(1)
            results = self.read_test_results(center_only=True)
            t.Time("Results")
            plot_factory.plot_dxdy_graph(imagepath, results, 1.0, *args, center_only=True, **kwargs)
            t.Time("Image")
        elif image_name == 'p2pdxdyltde':
            t = Timer(1)
            results = self.read_test_results(edge_only=True)
            t.Time("Results")
            plot_factory.plot_dxdy_graph(imagepath, results, 1.0, *args, edge_only=True, **kwargs)
            t.Time("Image")
        elif image_name == 'p2phistogram':
            t = Timer(1)
            results = self.read_test_results()
            t.Time("Results")
            plot_factory.plot_p2p_err_histogram(imagepath, results, 1.0, *args, edge_only=False, **kwargs)
            t.Time("Image")

        return None

    def read_test_results(self, dutinfo = None, dbsession = None, **kwargs):
        if dbsession is None:
            dbsession = db.get_database().session()
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        query = dbsession.query(db.OneFingerTapTest).filter(db.OneFingerTapTest.test_id==self.test_id).\
                                                     order_by(db.OneFingerTapTest.id)

        passed_points = [] # These are tuple-tuples: ((target_x, target_y), (hit_x, hit_y))
        failed_points = []
        targets = []
        hits = [] # target points: ((target_x, target_y), radius)
        missing = [] # target points ((target_x, target_y), radius)
        missing_edge = []
        edge_points = 0
        max_input_error = analyzers.round_dec(0.0)
        max_edge_error = analyzers.round_dec(0.0)
        distances = []

        for point in query:
            target = analyzers.robot_to_target((point.robot_x, point.robot_y), dutinfo)
            targets.append(target)

            edge_point = False
            if analyzers.is_edge_point(target, dutinfo):
                edge_point = True
                edge_points += 1
                if 'center_only' in kwargs:
                    continue
            else:
                if 'edge_only' in kwargs:
                    continue

            if point.panel_x is None or point.panel_y is None:
                missing.append((target, analyzers.get_max_error(target, dutinfo)))
                if edge_point:
                    missing_edge.append((target, analyzers.get_max_error(target, dutinfo)))

            else:
                max_error = analyzers.round_dec(analyzers.get_max_error(target, dutinfo))
                hits.append((target, max_error))
                hit = analyzers.panel_to_target((point.panel_x, point.panel_y), dutinfo)
                distance = analyzers.round_dec(np.linalg.norm((hit[0]-target[0], hit[1]-target[1])))
                distances.append(float(distance))
                if distance > max_error:
                    failed_points.append((target, hit))
                else:
                    passed_points.append((target, hit))
                if edge_point:
                    if distance > max_edge_error:
                        max_edge_error = distance
                else:
                    if distance > max_input_error:
                        max_input_error = distance

        max_input_verdict = (max_input_error < settings['maxposerror'])
        if settings['edgelimit'] >= 0:
            max_input_verdict = max_input_verdict and max_edge_error < settings['edgepositioningerror']

        results = {'max_input_error': max_input_error,
                   'edge_analysis_done': (settings['edgelimit'] >= 0),
                   'max_edge_error': max_edge_error,
                   'max_input_verdict': max_input_verdict,
                   'total_points': len(targets),
                   'edge_points': edge_points,
                   'missing_inputs': len(missing),
                   'missing_inputs_verdict': (len(missing) - len(missing_edge) <= settings['maxmissing']),
                   'missing_edge_inputs': len(missing_edge),
                   'missing_edge_inputs_verdict': (len(missing_edge) <= settings['maxedgemissing']),
                   'passed_points': passed_points,
                   'failed_points': failed_points,
                   'targets': targets,
                   'maxposerror': settings['maxposerror'],
                   'hits': hits,
                   'missing': missing,
                   'distances': distances,
                   }

        if settings['edgelimit'] >= 0:
            # Edge analysis
            results['edgepositioningerror'] = settings['edgepositioningerror']
            results['images'] = [(ImageFactory.create_image_name(self.test_id, 'p2pdiff'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdiff', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2pdxdy'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdxdy', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2pdxdyltdc'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdxdyltdc', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2pdxdyltde'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdxdyltde', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2phistogram'),
                                  ImageFactory.create_image_name(self.test_id, 'p2phistogram', 'detailed'))]
        else:
            results['images'] = [(ImageFactory.create_image_name(self.test_id, 'p2pdiff'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdiff', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2pdxdy'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdxdy', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2pdxdyltd'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdxdyltd', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2phistogram'),
                                  ImageFactory.create_image_name(self.test_id, 'p2phistogram', 'detailed'))]

        return results

    def create_sql_rows(self):
        test_results = self.read_test_results()
        rows = []
        rows.append(OneFingerTapTestSQL())
        rows[0].max_input_error = test_results['max_input_error']
        rows[0].maxposerror = test_results['maxposerror']
        rows[0].max_edge_error = test_results['max_edge_error']

        return rows