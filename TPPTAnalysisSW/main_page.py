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
import genshi

from genshi.template import MarkupTemplate
import sqlalchemy.sql.default_comparator
import sqlalchemy.ext.baked

import shutil
import json
import glob
import cherrypy
import os.path

import optofidelity_protocols.measurementdb as db
from .base_page import BasePage
from .test_session import TestSession
from .info.version import version
from .settings import settings
import collections
import TPPTAnalysisSW.progressstatus as progressstatus
import TPPTAnalysisSW.test_refs as test_refs
import TPPTAnalysisSW.imagefactory as imagefactory


#Main page controller
class MainPage(BasePage):

    def __init__(self):
        super(MainPage, self).__init__()

    exposed = True

    def GET(self, *args, **kwargs):

        if "event" in kwargs:
            cherrypy.response.headers["Content-Type"] = "text/event-stream"
            cherrypy.response.headers["Transfer-Encoding"] = "identity"
            return "data: " + str(progressstatus.progress) + "\ndata:\nretry:500\n\n"

        if os.path.isfile("static/AnalysisSoftwareUserGuide.pdf") and os.path.isfile("../../Docs/AnalysisSoftwareUserGuide.pdf"):
            if os.path.getmtime("static/AnalysisSoftwareUserGuide.pdf") < os.path.getmtime("../../Docs/AnalysisSoftwareUserGuide.pdf"):
                try:
                    shutil.copy("../../Docs/AnalysisSoftwareUserGuide.pdf", "static/AnalysisSoftwareUserGuide.pdf")
                except IOError:
                    print("Copying user guide failed.")
        else:
            try:
                shutil.copy("../../Docs/AnalysisSoftwareUserGuide.pdf", "static/AnalysisSoftwareUserGuide.pdf")
            except IOError:
                print("Copying user guide failed.")

        dbsession = db.get_database().session()
        testsessions = dbsession.query(db.TestSession).order_by(db.TestSession.id)

        sessions = []

        for ts in testsessions:

            tests, test_in_database, results, curved = TestSession.sessionResultsFromDB(ts, dbsession)
            if "Error" in results:
                result = "Error"
            elif "Fail" in results and "Requires recalculate" not in results:
                result = "Fail"
            elif ("N/A" in results or len(results) == 0):
                result = "N/A"
            elif "Requires recalculate" in results:
                result = "Requires recalculate"
            else:
                result = "Pass"

            sessions.append((ts, result, TestSession.session_samples_progs_manus(ts, dbsession), curved))

        # Show test sessions
        pagenumber = 1
        if ('page' in kwargs):
            pagenumber = max(1, int(kwargs['page']))
        sessions_per_page = 30
        if len(sessions) >= sessions_per_page:
            latest = sessions[(-1 - sessions_per_page * (pagenumber - 1)):(-sessions_per_page - sessions_per_page * (pagenumber - 1)):-1]
        else:
            latest = sessions[::-1]

        files = glob.glob("C:/OptoFidelity/TPPT/*.sqlite")
        current = db.get_database().dbpath.replace("\\", "/")

        paths = {}

        for f in files:
            if current == f.replace("\\", "/"):
                paths[f] = "selected"
            else:
                paths[f] = None

        # Tree: Manufacturers - Program
        manufacturers = self.manufacturers_tree(dbsession, sessions)

        with open("templates/testsessions_index.html") as f:
            template = MarkupTemplate(f)

            stream = template.generate(latest=latest,
                                   manufacturers=manufacturers,
                                   version=version,
                                   pagenumber=pagenumber,
                                   dbfiles=collections.OrderedDict(sorted(paths.items(), key=lambda t: t[0])))

            return stream.render('xhtml', doctype='html5')

    def POST(self, filepath=None, *args, **kwargs):
        dbsession = db.get_database().session()

        param = ""

        if 'params' in kwargs:
            param = kwargs['params']
        elif filepath:
            test_refs.testclass_refs.clear()
            imagefactory.ImageFactory.delete_all_images()
            db.get_database().change_database(filepath)
            return self.GET()

        if param == "recalculate":

            # clear cache
            test_refs.testclass_refs.clear()
            imagefactory.ImageFactory.delete_all_images()
            dbsessions = dbsession.query(db.TestSession).values(db.TestSession.id)
            sessionids = [ts[0] for ts in dbsessions]
            length = len(sessionids)
            for idx, ts in enumerate(sessionids):
                TestSession.eval_tests_results(dbsession, ts)
                if idx == 0:
                    progressstatus.progress = 0
                else:
                    progressstatus.progress = round(idx / float(length), 2)

            progressstatus.progress = 0

            return "Analysis recalculated."

        if param == "delete":
            print ("Deleting test session id %s and all related data..." % (kwargs['id'],))
            session = dbsession.query(db.TestSession).filter(db.TestSession.id == kwargs['id']).first()
            for item in session.test_items:
                if str(item.id) in test_refs.testclass_refs:
                    imagefactory.ImageFactory.delete_images(str(item.id))
                    test_refs.testclass_refs.pop(str(item.id))
            dbsession.query(db.TestSession).filter(db.TestSession.id == kwargs['id']).delete()
            dbsession.commit()

            return "Deletion successful."

    def manufacturers_tree(self, dbsession, sessions):

        # Structure of the list.
        # [(manufacturer_name, [(program_name, [testsession1, testsession2, ...]), ...]), ...]
        manufacturers = []

        for dut in dbsession.query(db.TestDUT):
            # Manufacturer
            man = dut.manufacturer
            if man is None or len(man) == 0:
                man = "[Empty]"

            p_list = None
            for m in manufacturers:
                if m[0] == man:
                    p_list = m[1]
            if p_list is None:
                p_list = []
                manufacturers.append((man, p_list))

            # Program
            prog = dut.program
            if prog is None or len(prog) == 0:
                prog = "[Empty]"

            prog_set = None
            for p in p_list:
                if p[0] == prog:
                    prog_set = p[1]
            if prog_set is None:
                prog_set = []
                p_list.append((prog, prog_set))

            # Append the test id's to the program set
            for test in dut.test_items:
                if test.testsession_id not in prog_set:
                    prog_set.append(test.testsession_id)

        # Replace testsession id's with test session lists
        testsessions = {ts[0].id: ts for ts in sessions}
        for man in manufacturers:
            for prog in man[1]:
                for i in range(len(prog[1])):
                    prog[1][i] = testsessions[prog[1][i]]

        return manufacturers

