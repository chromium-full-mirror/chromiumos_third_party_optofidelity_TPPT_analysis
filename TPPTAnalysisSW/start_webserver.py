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
from .main_page import MainPage
from .test_session import TestSession
from .test import Test
from .test_session_report import TestSessionReport
from .imagefactory import ImageFactory
from .settings_page import SettingsController
from .test_session_settings import TestSessionSettingsController
from .settings import *
from .test_summary import SummaryController
from .utils import Timer
import TPPTAnalysisSW.test_refs as test_refs
import TPPTAnalysisSW.measurementdb as measurementdb
import TPPTAnalysisSW.progressstatus as progressstatus

# We need to import the different test types somewhere - a small kludge

import os
import sys
import webbrowser


def start(address, port):

    conf = {
        '/': {
              'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
              'response.timeout': 3600,
        },
        '/static' : {
            'tools.staticdir.root': os.getcwd(),
            'tools.staticdir.on' : True,
            'tools.staticdir.dir' : 'static',
        }
    }

    test_refs.init()
    progressstatus.initProgress()

    dbsession = measurementdb.get_database().session()
    loadSettings(dbsession) # from settings.py
    dbsession.close()

    root = MainPage()
    root.testsessions = TestSession()
    root.tests = Test()
    root.testsessionreports = TestSessionReport()

    # create generated image path if none exists
    if not os.path.isdir('static/img/generated'):
        os.mkdir('static/img/generated')

    root.img = ImageFactory()
    root.img.configuration['root_dir'] = os.getcwd()
    root.settings = SettingsController()
    root.testsessionsettings = TestSessionSettingsController()
    root.summary = SummaryController()

    if "--timer" in sys.argv:
        # Used in Plotinfo
        Timer.do_timing = True

    web_address = 'http://%s:%s/' % (address, port)

    def browse():
        webbrowser.open(web_address)

    cherrypy.engine.subscribe('start', browse, priority=90)

    cherrypy.config.update({'server.socket_host': address,})
    cherrypy.config.update({'server.socket_port': port,})

    cherrypy.quickstart(root,'/',conf)
