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

from .base_page import BasePage
from cherrypy import *
from genshi.template import MarkupTemplate
from genshi.filters import HTMLFormFiller
from .measurementdb import *
from .plotinfo import TestSessionInfo
from .info.version import Version

import json
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.test_session as test_session
import copy

#Settings controller for settings-view
class SummaryController(BasePage):
    exposed = True
    
    def GET(self, testsession_id = None):

        if (testsession_id == None):
            raise HTTPError("404")
        
        dbsession = get_database().session()
        
        sessioninfo = TestSessionInfo(testsession_id=testsession_id, dbsession=dbsession)
        test_query = dbsession.query(TestItem).filter(TestItem.testsession_id==testsession_id).values(TestItem.id)
        test_ids = [id[0] for id in test_query]

        templateparams = copy.copy(sessioninfo.__dict__)

        template = MarkupTemplate(open("templates/test_summary.html"))     
        stream = template.generate(test_ids=test_ids, version=Version, **(templateparams))
        return stream.render('xhtml')
    