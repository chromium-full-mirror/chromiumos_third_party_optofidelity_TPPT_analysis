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

from testbase import TestBase, testclasscreator
from imagefactory import ImageFactory
from measurementdb import get_database
from info.version import Version
from utils import Timer
import plotinfo
import plot_factory

class DummyTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(99)
    def create_testclass(*args, **kwargs):
        return DummyTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new DummyTest class """
        return super(DummyTest, self).__init__(ddtest_row, *args, **kwargs)

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        return "None"

    # Override to make necessary operations for clearing test results
    # Clearing the test result from the results table is done elsewhere
    def clearanalysis(self, *args, **kwargs):
        """ Clears analysis results """
        ImageFactory.delete_images(self.test_id)

    # Create the test report. Return the created HTML, or raise cherrypy.HTTPError
    def createreport(self, *args, **kwargs):

        # Create common template parameters (including test_item dictionary, testsession dictionary, test_id, test_type_name etc)
        templateParams = super(DummyTest, self).create_common_templateparams(**kwargs)
        dbsession = get_database().session()

        # Add the image name and parameters to the report
        # Typically image is added like this:
        #
        templateParams['figure'] = ImageFactory.create_image_name(self.test_id, 'dummy')

        t = Timer()

        #
        # A More complicated example:
        # templateParams['figure'] = ImageFactory.create_image_name(self.test_id, 'dummy', str(2)) # If the last parameter is changed, a new image is generated to the report
        # templateParams['figurestring'] = 'HelloWorld' # Just a sample - do not copy: This is used only when the image is generated for the first time

        # Here we can fetch data from the database and add it to the template. E.g.:
        # 1) Create table dummytestdata, with id, dataline and foreign key test_id
        # 2) Create SQLAlchemy object to the measurementdb.py:
        #
        #class DummyTestData( Base ):
        #    #One-finger swipe results are defined here
        #    __tablename__ = 'dummytestdata'
        #    id = Column( Integer, primary_key = True )
        #    test_id = Column( Integer, ForeignKey('test_item.id') )
        #    data = Column(Float)
        #    ...
        #
        # 3) Fetch the data here
        #
        #dataquery = dbsession.query(DummyTestData).filter(DummyTestData.test_id == self.test_id).all()
        #    
        #   ... and handle the query results in for loop, adding information to the templateParams
        #
        # OR
        # Create a new function to analyzers or plotinfo libraries. 

        # data for the report
        templateParams['results'] = self.read_test_results()

        t.Time("Results")

        # set the content to be used
        templateParams['test_page'] = 'test_dummy.html'
        templateParams['version'] = Version
        
        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        t.Time("Markup")
        return stream.render('xhtml')

      
    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):
        
        # Dummy test has only one image: dummyimage.
        if image_name == 'dummy':
            # Create the test image (here we just pass args and kwargs to plotter - not necessarily needed)
            # Normally we would fetch data from the database to the plotinfo-parameter
            plotInfo = self.read_test_results()
            plot_factory.plot_dummy_image(imagepath, plotInfo, *args, title="Temporary image", **kwargs)
        else:
            raise cherrypy.HTTPError(message = "No such image in the report")
            
        return None

    def read_test_results(self, testsessioninfo = None, dbsession = None):
        if dbsession is None:
            dbsession = get_database().session()
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        plotInfo = {}
        plotInfo['points'] = [(0.25, 0.75), (-0.22, 0,45), (-0.75, -0.1), (0.5, -0.6)]
        return plotInfo