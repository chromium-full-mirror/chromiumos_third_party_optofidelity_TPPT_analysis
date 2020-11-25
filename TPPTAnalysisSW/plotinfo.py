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

import TPPTAnalysisSW.transform2d as transform2d
import optofidelity_protocols.measurementdb as db

class TestSessionInfo:
    """ Information class that holds test session information contents """

    def __init__(self, testsession=None, testsession_id=None, dbsession=None):
        """ Initializes the session info """

        if testsession is None:
            if dbsession is None:
                dbsession = db.get_database().session()
            testsession = dbsession.query(db.TestSession).filter(db.TestSession.id == testsession_id).first()

        self.id = testsession.id
        
        self.operator = testsession.operator
        self.starttime = testsession.starttime
        self.endtime = testsession.endtime
        self.notes = testsession.notes
        
        # Fetch the session parameters
        self.parameters = {}
        for param in testsession.session_parameters:
            if param.isFloat:
                self.parameters[param.name] = param.valueFloat
            else:
                self.parameters[param.name] = param.valueString

class TestDUTInfo:
    """ Information class that holds test session information contents """

    def __init__(self, testdut=None, testdut_id=None, dbsession=None):
        """ Initializes the DUT info """

        if testdut is None:
            if dbsession is None:
                dbsession = db.get_database().session()
            testdut = dbsession.query(db.TestDUT).filter(db.TestDUT.id == testdut_id).first()

        self.id = testdut.id
        
        self.program = testdut.program
        self.manufacturer = testdut.manufacturer
        self.batch = testdut.batch
        self.sample_id = testdut.sample_id
        self.svg_data = testdut.svg_data
        
        # Fetch the session parameters
        self.parameters = {}
        for param in testdut.dut_parameters:
            if param.isFloat:
                self.parameters[param.name] = param.valueFloat
            else:
                self.parameters[param.name] = param.valueString

        # Handle the parameters

        # Digitizer resolution (maximum x,y values reported by touch device)
        self.digitizer_resolution = [float(s) for s in self.parameters['DUT resolution [x;y]'].split(';')]
        # Physical dimensions (mm)
        self.dimensions = [float(s) for s in self.parameters['DUT dimensions [x;y, mm]'].split(';')]
        # Offset to be added to the measurements
        self.offset = [float(s) for s in self.parameters['DUT offset [x;y, mm]'].split(';')]
        
        # Flip x-coordinates
        self.flipx = False
        if 'Flip X coordinates' in self.parameters:
            if self.parameters['Flip X coordinates'] is None or self.parameters['Flip X coordinates'] != "0":
                self.flipx = True

        # Flip x-coordinates
        self.flipy = False
        if 'Flip Y coordinates' in self.parameters:
            if self.parameters['Flip Y coordinates'] is None or self.parameters['Flip Y coordinates'] != "0":
                self.flipy = True

        # Switch X->Y
        self.switchxy = False
        if '(X,Y) --> (Y,X)' in self.parameters:
            if self.parameters['(X,Y) --> (Y,X)'] is None or self.parameters['(X,Y) --> (Y,X)'] != "0":
                self.switchxy = True
    
    def save(self, dbsession=None):
        if dbsession is None:
            dbsession = db.get_database().session()

        testdut = dbsession.query(db.TestDUT).filter(db.TestDUT.id == self.id).first()
        saveparams = {
                      'DUT resolution [x;y]': ";".join(str(f) for f in self.digitizer_resolution),
                      'DUT dimensions [x;y, mm]': ';'.join(str(f) for f in self.dimensions),
                      'DUT offset [x;y, mm]': ';'.join(str(f) for f in self.offset),
                      'Flip X coordinates': '1' if self.flipx else '0',
                      'Flip Y coordinates': '1' if self.flipy else '0',
                      '(X,Y) --> (Y,X)': '1' if self.switchxy else '0',
                      }

        testdut.manufacturer = self.manufacturer
        testdut.program = self.program
        testdut.batch = self.batch
        testdut.sample_id = self.sample_id

        for param in testdut.dut_parameters:
            if param.name in saveparams:
                # Update existing value
                param.valueString = saveparams[param.name]
                param.isFloat = None
                del saveparams[param.name]

        for key, value in saveparams.items():
            # Add non-existing values (a strange situation...)
            dbsession.add(db.DutParameters(dut_id=self.id, name=key, valueString=value))

        dbsession.commit()
