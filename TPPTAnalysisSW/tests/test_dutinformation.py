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
import math

from TPPTAnalysisSW.testbase import TestBase, testclasscreator
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.measurementdb import get_database
from TPPTAnalysisSW.settings import settings
from TPPTAnalysisSW.info.version import Version
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.plot_factory as plot_factory

class DutInformationTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(6)
    def create_testclass(*args, **kwargs):
        return DutInformationTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new DutInformationTest class """
        super(DutInformationTest, self).__init__(ddtest_row, *args, **kwargs)

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        results = self.read_test_results()
        passed = (results['resolutionTestPassed'] and results['physicalDimensionTestPassed'])
        return "Pass" if passed else "Fail"

    # Override to make necessary operations for clearing test results
    # Clearing the test result from the results table is done elsewhere
    def clearanalysis(self, *args, **kwargs):
        """ Clears analysis results """
        pass

    # Create the test report. Return the created HTML, or raise cherrypy.HTTPError
    def createreport(self, *args, **kwargs):

        # Create common template parameters (including test_item dictionary, testsession dictionary, test_id, test_type_name etc)
        templateParams = super(DutInformationTest, self).create_common_templateparams(**kwargs)
        dbsession = get_database().session()

        # data for the report
        results = self.read_test_results()
        templateParams['results'] = results

        # set the content to be used
        templateParams['test_page'] = 'test_dutinformation.html'
        templateParams['version'] = Version

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))

        passed = (results['resolutionTestPassed'] and results['physicalDimensionTestPassed'])

        return stream.render('xhtml'), "Pass" if passed else "Fail"


    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        # We have no images
        raise cherrypy.HTTPError(message = "No such image in the report")

    def read_test_results(self):

        dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'])


        results = {}
        results["digitizerResolution"] = dutinfo.digitizer_resolution
        results["nativeResolution"] = dutinfo.native_resolution
        results["dimensions"] = dutinfo.dimensions

        results["resolutionTestPassed"] = dutinfo.digitizer_resolution[0] >= dutinfo.native_resolution[0] and \
                                          dutinfo.digitizer_resolution[1] >= dutinfo.native_resolution[1]

        # Pixels per inch. Calculation of sqrt(x^2 + y^2)/diagonal screen size in inches, where x is the number of pixels on the horizontal axis and y is the number of pixels on the vertical axis.
        INCH_PER_MM = 0.0393700787
        results["ppi"] = (math.sqrt(dutinfo.digitizer_resolution[0]**2 + dutinfo.digitizer_resolution[1]**2) /
                          math.sqrt((dutinfo.dimensions[0]*INCH_PER_MM)**2 + (dutinfo.dimensions[1]*INCH_PER_MM)**2))

        results["physicalDimensionTestPassed"] = (results["ppi"] >= settings["minppi"])

        return results
