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
import TPPTAnalysisSW.start_webserver as start_webserver
import argparse
from inspect import getsourcefile
from os import chdir
from os.path import realpath, join, dirname
import TPPTAnalysisSW.sqluploader as sqluploader
from optofidelity_protocols import measurementdb

# Change current working directory to ./TPPTAnalysisSW to allow launching from main.py without changing all the
# relative paths currently in the codebase
basedir = dirname(realpath(getsourcefile(lambda: 0)))
chdir(join(basedir, "TPPTAnalysisSW"))


if __name__ == '__main__':
    print('Starting TPPT Analysis...')
    # Address must be localhost not e.g. '127.0.0.1'.
    address = 'localhost'
    port = 8081

    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', default=False, help='Startup check for CI usage')
    parser.add_argument('--database', type=str, default='C:/OptoFidelity/TPPT/database.sqlite',
                        help='Path to used database file')
    parser.add_argument('--config', type=str, default='C:/OptoFidelity/TPPT/config.json',
                        help='Path to used configuration file')
    parser.add_argument('--dbconfig', type=str, default='C:/OptoFidelity/TPPT Analysis/dbconfig.yaml',
                        help='Path to database configuration file')
    args = parser.parse_args()

    if not args.check:
        # Comment this out to disable the possibility to upload results to SQL database.
        sqluploader.initialize(args.dbconfig)

        measurementdb.setup_database(args.database, args.config)
        start_webserver.start(address, port)
