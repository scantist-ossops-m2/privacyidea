# -*- coding: utf-8 -*-
#
#  privacyIDEA
#  Jul 18, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from privacyidea.lib.applications import MachineApplicationBase
import logging
log = logging.getLogger(__name__)
# from privacyidea.lib.log import log_with
from privacyidea.lib.token import get_tokens


class MachineApplication(MachineApplicationBase):
    """
    This is the application for SSH.

    Possible options:
        user

    """
    application_name = "ssh"
    '''as the authentication item is no sensitive information,
    we can set bulk_call to True. Thus the admin can call
    all public keys to distribute them via salt.
    FIXME: THis is only true for SSH pub keys.
    If we would support OTP with SSH, this might be sensitive information!
    '''
    allow_bulk_call = True

    @classmethod
    def get_authentication_item(cls,
                                token_type,
                                serial,
                                challenge=None, options=None):
        """
        :param token_type: the type of the token. At the moment
                           we support the tokenype "sshkey"
        :param serial:     the serial number of the token.
        :return auth_item: For Yubikey token type it
                           returns a dictionary with a "challenge" and
                           a "response".
        """
        options = options or {}
        ret = {}
        if token_type.lower() == "sshkey":
            toks = get_tokens(serial=serial, active=True)
            if len(toks) == 1:
                # tokenclass is a SSHkeyTokenClass
                tokclass = toks[0]
                # We just return the ssh public key, so that
                # it can be included into authorized keys.
                ret["sshkey"] = tokclass.get_sshkey()
                # We return the username if the token is assigned to a
                # user, so that this username could be used to save
                # the ssh key accordingly
                user_object = toks[0].get_user()
                if user_object:
                    uInfo = user_object.get_user_info()
                    if "username" in uInfo:
                        ret["username"] = uInfo.get("username")
                # ret["info"] = uInfo
        else:
            log.info("Token %r, type %r is not supported by"
                     "SSH application module" % (serial, token_type))

        return ret

    @classmethod
    def get_options(cls):
        """
        returns a dictionary with a list of required and optional options
        """
        return {'required': [],
                'optional': ['user']}
