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

import traceback
import json

import cherrypy
from cherrypy import HTTPError
from genshi.template import MarkupTemplate

from .base_page import BasePage
from optofidelity_protocols.measurementdb import get_database, Setting
import TPPTAnalysisSW.test_session as test_session
import TPPTAnalysisSW.imagefactory as imagefactory
from .settings import settings, setting_categories, loadSettings
from .info.version import Version
import TPPTAnalysisSW.progressstatus as progressstatus
import TPPTAnalysisSW.test_refs as test_refs


#Settings controller for settings-view
class SettingsController(BasePage):

    SAVEPATH = ""

    def GET(self, *args, **kwargs):

        if "event" in kwargs:
            cherrypy.response.headers["Content-Type"] = "text/event-stream"
            cherrypy.response.headers["Transfer-Encoding"] = "identity"
            return "data: " + str(progressstatus.progress) + "\ndata:\nretry:500\n\n"

        dbsession = get_database().session()
        with open("templates/settings.html") as f:

            tmpl = MarkupTemplate(f)
            settings = dbsession.query(Setting).all()
            groups = self.settings_by_group(settings)
            stream = tmpl.generate(groups=groups, version=Version)

            return stream.render('xhtml')

    def POST(self, *args, **kwargs):

        dbsession = get_database().session()
        data = json.loads(kwargs['params'])

        for i in data:
            setting = dbsession.query(Setting).filter(Setting.id == i['id']).first()
            try:
                strvalue = i['value']
                strvalue = strvalue.replace(',', '.') # Allow comma decimal separator
                setting.value = float(strvalue)
            except ValueError:
                print(traceback.format_exc())
                dbsession.rollback()
                raise HTTPError("500", "Float value required for %s" % setting.desc)

        dbsession.commit()
        loadSettings(dbsession) # from settings.py

        # clear cache
        test_refs.testclass_refs.clear()
        imagefactory.ImageFactory.delete_all_images()

        if kwargs['mode'] == "recalculate":

            testsessions = get_database().get_test_sessions()
            length = len(testsessions)

            for idx, ts in enumerate(testsessions):
                test_session.TestSession.eval_tests_results(dbsession, ts.id)
                if idx == 0:
                    progressstatus.progress = 0
                else:
                    progressstatus.progress = round(idx / float(length), 2)

            progressstatus.progress = 0

            return "Settings saved and analyses recalculated."

        testsessions = get_database().get_test_sessions()

        for ts in testsessions:
            test_session.TestSession.eval_tests_results(dbsession, ts.id, recalculate=False)

        return "Settings saved but analyses were not recalculated."

    def settings_by_group(self, settings):
        # Copy settings to safety
        settings = list(settings)
        groups, groups_settings = self.parse_groups()

        # Replace setting_id with given setting
        for group_settings in groups_settings:
            for i, setting_id in enumerate(group_settings):
                setting = [s for s in settings if s.id == setting_id]
                if len(setting) == 0:
                    raise HTTPError(status="500", message="Internal error: setting %s not found in database" % setting)
                else:
                    settings.remove(setting[0])
                    group_settings[i] = setting[0]

        if len(settings) > 0:
            # There are non-categorized settings
            groups.append(None)
            groups_settings.append(settings)

        # Note: this will break if some of the settings given in settings_categories
        # is not found in the database. This should be rare condition, as missing
        # settings are inserted in the startup sequence

        return zip(groups, groups_settings)

    def parse_groups(self):
        """
        Parses the group to list of categories. Creates separate categories
        for settings that are in multiple categories
        """

        settings_dict = {}

        # Create settings list (reverse: setting_id -> categories)
        # Note: generated lists are equal if they are included in the same categories
        for name, settings_list in setting_categories.items():
            for setting_id in settings_list:
                if setting_id in settings_dict:
                    settings_dict[setting_id].append(name)
                else:
                    settings_dict[setting_id] = [name]

        # List of different categories
        groups = []
        # Settings in each category
        groups_settings = []

        for setting_id, groups_list in settings_dict.items():
            if groups_list in groups:
                # Append setting to the specific group
                groups_settings[groups.index(groups_list)].append(setting_id)
            else:
                # Create a new group in list and add the settings to it
                # order groups by number of categories in group and alphabetically
                for index_to in range(len(groups)):
                    if len(groups[index_to]) < len(groups_list):
                        continue
                    elif (len(groups[index_to]) > len(groups_list) or
                          groups[index_to][0] > groups_list[0]):
                        groups.insert(index_to, groups_list)
                        groups_settings.insert(index_to, [setting_id])
                        break
                else:
                    # Append
                    groups.append(groups_list)
                    groups_settings.append([setting_id])

        return (groups, groups_settings)

    exposed = True
