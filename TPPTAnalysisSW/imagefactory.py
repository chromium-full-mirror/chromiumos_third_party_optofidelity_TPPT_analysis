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
from cherrypy.lib.static import serve_file
import os.path
import threading
import re

import TPPTAnalysisSW.testbase as testbase
import TPPTAnalysisSW.plotinfo as plotinfo
from .base_page import BasePage
import TPPTAnalysisSW.plot_factory as plot_factory
from .plot_factory import *

# generator functions for the different images - will be filled by the decorator
_generators = {}

#decorator class
class reportimagecreator(object):
    """ Creates images for the report. Gets the generated image names as parameter """

    _generators = {}

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        pass

    def __call__(self, f):
        global _generators
        for arg in self.args:
            _generators[arg] = f
        return f

class ImageFactory(BasePage):


    # configuration values, these are the defaults, override in main
    configuration = { 'static_dir': 'static/img/generated/',
                      'root_dir': '',
                    }

    # lock object for the image creation
    _imagelock = threading.RLock()

    def __init__(self, *args, **kwargs):
        super(ImageFactory, self).__init__(*args, **kwargs)

    exposed = True

    def GET(self,imagename=None, **kwargs):
        if imagename is None:
            error = cherrypy.HTTPError(403)
            error.set_response()
            return "Image generator directory browsing disabled"

        # Check if image exists
        target_name = os.path.join(ImageFactory.configuration['root_dir'], ImageFactory.configuration['static_dir'], imagename)
        # print "Target: " + target_name
        force_refresh = ('refresh' in kwargs)

        try:
            ImageFactory._imagelock.acquire()
            # Round 1: if image does not exist - check if its currently being generated
            if not os.path.isfile(target_name) and not force_refresh:
                #print ">>> Waiting..."
                plot_factory.waitForPlot()
                #print ">>> Wait ended..."

            # Round 2: if image still does not exist, generate it
            if force_refresh or not os.path.isfile(target_name):
                #print "Generating image " + target_name
                # Split image name into tokens
                if imagename.endswith(".png"):
                    imagename = imagename[:-4]
                tokens = imagename.split('_')

                # For now: Check if new style generator exists
                #print str(tokens)

                if len(tokens) > 1:
                    reportclass = testbase.TestBase.create(tokens[0], **kwargs)[0]
                    if reportclass:
                        #print "class found: " + str(reportclass)
                        reportclass.createimage(target_name, *tokens[1:], **kwargs)
                    elif tokens[1] in _generators:
                       _generators[tokens[1]](*tokens)
                    else:
                        raise cherrypy.HTTPError(404, "No such image in configuration")

            # Wait for the possible plotting to finish before serving the image because premature serving can create
            # content length header issues causing the image not to show in browser
            plot_factory.waitForPlot()
            return serve_file(target_name, content_type='image/png')

        finally:
            ImageFactory._imagelock.release()

    @staticmethod
    def delete_all_images():
        directory = os.path.join(ImageFactory.configuration['root_dir'], ImageFactory.configuration['static_dir'])
        files = os.listdir(directory)

        for file in files:
            # remove only files with the correct name format
            if re.match("^\d+_\w+", file):
                os.remove(os.path.join(directory, file))

    @staticmethod
    def delete_images(test_id):
        directory = os.path.join(ImageFactory.configuration['root_dir'], ImageFactory.configuration['static_dir'])
        files = os.listdir(directory)

        for file in files:
            # remove only files with the correct name format
            if re.match("%s_\w+" % str(test_id), file):
                os.remove(os.path.join(directory, file))

        pass

    @staticmethod
    def create_image_path(test_id, imagename, *args):
        """ Returns the image name in the filesystem (with full path) """
        filename = "_".join([str(test_id), str(imagename)])
        if len(args) > 0:
            filename += '_' + '_'.join(args)
        filename = filename + ".png"
        path = os.path.join(ImageFactory.configuration['root_dir'], ImageFactory.configuration['static_dir'], filename)
        return path

    @staticmethod
    def create_image_name(test_id, imagename, *args):
        """ Returns the image name in the report (with path from the root) """
        imagename = "_".join([str(test_id), imagename])
        if len(args) > 0:
            imagename += '_' + '_'.join(args)
        return '/img/' + imagename + ".png"
