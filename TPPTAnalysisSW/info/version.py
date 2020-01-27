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
class MetaVersion(type):
    # DON'T CHANGE THE ATTRIBUTE BELOW: These are updated programmatically when
    # CI builds an installation package.
    #
    # _major    -- Major version
    # _minor    -- Release version increases by one on every public release
    # _build    -- CI build number increases by one on every CI build (~commit)
    # _revision -- SVN revision number (VCS used by CI for the build)
    # _data     -- date of the build
    #
    _major = "2"
    _minor = "0"
    _build = "0 (rnd)"
    _revision = "0"
    _date = ""

    @property
    def major(cls):
        """ Major version """
        return cls._major

    @property
    def build(cls):
        """ Build number """
        return cls._build

    @property
    def minor(cls):
        """ Release number """
        return cls._minor

    @property
    def revision(cls):
        """ Revision number """
        return cls._revision

    @property
    def date(cls):
        """ Build date """
        return cls._date

    @property
    def simple(cls):
        """
        Software version: <major>.<release>

        Access software version from software:
            #>>> from info.version import Version
            ... Version.simple
        """
        return "%s.%s" % (
            cls.major,
            cls.minor)

    @property
    def software(cls):
        """
        Software version: <major>.<release>.<build> rev. <number> [date]

        Access software version from software:
         from info.version import Version
            ... Version.software
        """
        return "%s.%s.%s rev. %s %s" % (
            cls.major,
            cls.minor,
            cls.build,
            cls.revision,
            cls.date)

    @property
    def api(self):
        """
        RESTful API version: <major>.<minor>

        Major -- Change(s) breaking current API increases major number by one:

            * Not backwards compatible
            * Removing something from API (methods or parameters)
            * Changing how method functions or meaning of a parameter

        Minor -- Changes(s) adding something to API but not breaking it
        increases the minor version by one:

            * 100% backwards compatible
            * Adding new methods (e.g., robot/Move)
            * Adding new parameters (e.g., robot/Move + x=2)

        API version is always a string. Access from software:
            #>>> from info.version import Version
            ... Version.api_version

        """
        return '1.0'

#
# Example of API update
#
# API 1.2
#   Finger API:
#       * Tap [x, y, z, duration]
#       * DoubleTap [x, y, z, duration, lift, interval]
#
class Version(object,  metaclass=MetaVersion):
    """
    API 1.0
        Initial version by Sami Laine
    """

    #__metaclass__ = MetaVersion


__version__ = Version.software
