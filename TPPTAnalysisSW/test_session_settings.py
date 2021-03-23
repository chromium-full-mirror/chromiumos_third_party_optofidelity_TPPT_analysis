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
import json

from genshi.template import MarkupTemplate
from genshi.filters import HTMLFormFiller

import optofidelity_protocols.measurementdb as db
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.test_session as test_session
import TPPTAnalysisSW.plotters as plotters
import TPPTAnalysisSW.imagefactory as imagefactory
import TPPTAnalysisSW.test_session as test_session

from .base_page import BasePage

from .info.version import version

# Settings controller for settings-view
class TestSessionSettingsController(BasePage):
    """ These are actually DUT-specific settings """

    def GET(self, testsession_id, dut_id):
        if dut_id is None:
            raise HTTPError("404")

        dbsession = db.get_database().session()
        dutinfo = plotinfo.TestDUTInfo(testdut_id=dut_id, dbsession=dbsession)

        template = MarkupTemplate(open("templates/test_dut_settings.html"))
        stream = template.generate(version=version, testsessionid=testsession_id, dutinfo=dutinfo)
        return stream.render('xhtml')

    def POST(self, testsession_id, dut_id, **kwargs):
        if 'data' not in kwargs:
            raise cherrypy.HTTPError("400", "Expected data not received")

        saveFields = ["size_x", "size_y", "digitizer_resolution_x", "digitizer_resolution_y",
                      "flipx", "flipy", "switchxy",
                      "dut_manufacturer", "dut_program", "dut_batch", "dut_sample_id"]
        data = json.loads(kwargs['data'])

        # Check that each save field exists in the data
        for key in saveFields:
            if key not in data:
                print("Missing key from input: " + key)
                raise cherrypy.HTTPError("400", "Invalid key/value pairs in POST data")
        # Check that no extra fields exists in the data
        for key in data.keys():
            if key not in saveFields:
                print ("Unrecognized key: " + key)
                raise cherrypy.HTTPError("400", "Unrecognized key/value pairs in POST data")

        # Assume that the data is of correct format -> save to DB
        dbsession = db.get_database().session()
        dutinfo = plotinfo.TestDUTInfo(testdut_id=dut_id, dbsession=dbsession)
        dutinfo.dimensions = [float(data['size_x']), float(data['size_y'])]
        dutinfo.digitizer_resolution = [float(data['digitizer_resolution_x']), float(data['digitizer_resolution_y'])]
        dutinfo.offset = [0.0, 0.0]
        dutinfo.flipx = (data['flipx'] == '1')
        dutinfo.flipy = (data['flipy'] == '1')
        dutinfo.switchxy = (data['switchxy'] == '1')

        dutinfo.manufacturer = data['dut_manufacturer']
        dutinfo.program = data['dut_program']
        dutinfo.batch = data['dut_batch']
        dutinfo.sample_id = data['dut_sample_id']

        dutinfo.save(dbsession=dbsession)

        # Recalculate analysis results
        test_session.TestSession.do_evaluation(dbsession, testsession_id)

        cherrypy.response.headers['Content-Type']= 'text/plain'
        return "Saved"

    exposed = True

