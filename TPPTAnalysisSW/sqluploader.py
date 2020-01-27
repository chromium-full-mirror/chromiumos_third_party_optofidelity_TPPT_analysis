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
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from ruamel.yaml import YAML

import logging

log = logging.getLogger(__name__)

engine = None
session_maker = sessionmaker()
Session = scoped_session(session_maker)

Base = declarative_base()

def is_sql_uploader_initialized():
    return engine is not None

def initialize(configuration_path):
    try:
        configuration = read_configuration(configuration_path)
    except FileNotFoundError:
        log.warning("Could not find database config file. Upload of results is not possible.")
        return

    # if database usage is not enabled we'll return at this point
    if not configuration["database_enabled"]:
        return

    try:
        host_data = {'database_engine': configuration['database_engine'],
                     'host_name': configuration['host_name'],
                     'port': configuration['port'],
                     'user_name': configuration['user_name'],
                     'password': configuration['password'],
                     'database': configuration['database']}
    except KeyError:
        log.error('Required database configuration data is missing')
        return

    try:
        global engine
        engine = create_engine(
            '{database_engine}://{user_name}:{password}@{host_name}:{port}/{database}'.format(**host_data))
        session_maker.configure(bind=engine)

        # Create summary and result tables if they don't exist
        Base.metadata.create_all(engine)
    except:
        engine = None
        log.error('Failed to initialize database')
        return



def upload_test(test_object):
    if engine is None:
        log.error("Result database was not initialized correctly. Unable to upload test results.")
        return

    # The session is created here and passed to the test object
    # and the test object handles the data write
    session = Session()
    try:
        test_object.upload_sql_data(session)
        return "Upload successful"
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def read_configuration(configuration_path):
    _yaml = YAML(typ='safe')
    with open(configuration_path, 'r') as file:
        config = _yaml.load(file)

    def convert_to_default_types(v):
        if v.__class__.__name__ == 'CommentedSeq':
            r = [convert_to_default_types(a) for a in list(v)]
            return r
        if v.__class__.__name__ == 'CommentedMap':
            r = {}
            for n in v:
                r[n] = convert_to_default_types(v[n])
            return r
        return v

    config = convert_to_default_types(config)

    return config
