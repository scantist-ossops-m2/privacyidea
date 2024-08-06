# -*- coding: utf-8 -*-
#
#  2015-04-03 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add WebUI logout time.
#  2015-03-27 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add PIN policies in USER scope
#  2015-02-06 Cornelius Kölbel <cornelius@privacyidea.org>
#             Rewrite for flask migration.
#             Policies are not handled by decorators as
#             1. precondition for API calls
#             2. internal modifications of LIB-functions
#             3. postcondition for API calls
#
#  Jul 07, 2014 add check_machine_policy, Cornelius Kölbel
#  May 08, 2014 Cornelius Kölbel
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  privacyIDEA is a fork of LinOTP
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
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
"""
Base function to handle the policy entries in the database.
This module only depends on the db/models.py

The functions of this module are tested in tests/test_lib_policy.py

A policy has the attributes

 * name
 * scope
 * action
 * realm
 * resolver
 * user
 * client
 * active

``name`` is the unique identifier of a policy. ``scope`` is the area,
where this policy is meant for. This can be values like admin, selfservice,
authentication...
``scope`` takes only one value.

``active`` is bool and indicates, whether a policy is active or not.

``action``, ``realm``, ``resolver``, ``user`` and ``client`` can take a comma
separated list of values.

realm and resolver
------------------
If these are empty '*', this policy matches each requested realm.

user
----
If the user is empty or '*', this policy matches each user.
You can exclude users from matching this policy, by prepending a '-' or a '!'.
``*, -admin`` will match for all users except the admin.

client
------
The client is identified by its IP address. A policy can contain a list of
IP addresses or subnets.
You can exclude clients from subnets by prepending the client with a '-' or
a '!'.
``172.16.0.0/24, -172.16.0.17`` will match each client in the subnet except
the 172.16.0.17.
"""

from .log import log_with
from configobj import ConfigObj

from netaddr import IPAddress
from netaddr import IPNetwork
from gettext import gettext as _

import logging
from ..models import (Policy, db)
from privacyidea.lib.error import ParameterError, PolicyError
log = logging.getLogger(__name__)

optional = True
required = False


class SCOPE():
    __doc__ = """This is the list of the allowed scopes that can be used in
    policy definitions.
    """
    AUTHZ = "authorization"
    ADMIN = "admin"
    AUTH = "authentication"
    AUDIT = "audit"
    USER = "user"   # was selfservice
    ENROLL = "enrollment"
    GETTOKEN = "gettoken"
    WEBUI = "webui"


class ACTION():
    __doc__ = """This is the list of usual actions."""
    ASSIGN = "assign"
    AUDIT = "auditlog"
    AUTHITEMS = "fetch_authentication_items"
    AUTOASSIGN = "autoassignment"
    COPYTOKENPIN = "copytokenpin"
    COPYTOKENUSER = "copytokenuser"
    DELETE = "delete"
    DISABLE = "disable"
    ENABLE = "enable"
    ENCRYPTPIN = "encrypt_pin"
    GETSERIAL = "getserial"
    IMPORT = "importtokens"
    LOGINMODE = "login_mode"
    LOGOUTTIME = "logout_time"
    LOSTTOKEN = 'losttoken'
    LOSTTOKENPWLEN = "losttoken_PW_length"
    LOSTTOKENPWCONTENTS = "losttoken_PW_contents"
    LOSTTOKENVALID = "losttoken_valid"
    MACHINERESOLVERWRITE = "mresolverwrite"
    MACHINERESOLVERDELETE = "mresolverdelete"
    MACHINELIST = "machinelist"
    MACHINETOKENS = "manage_machine_tokens"
    MAXTOKENREALM = "max_token_per_realm"
    MAXTOKENUSER = "max_token_per_user"
    NODETAILSUCCESS = "no_detail_on_success"
    NODETAILFAIL = "no_detail_on_fail"
    OTPPIN = "otppin"
    OTPPINRANDOM = "otp_pin_random"
    OTPPINMAXLEN = 'otp_pin_maxlength'
    OTPPINMINLEN = 'otp_pin_minlength'
    OTPPINCONTENTS = 'otp_pin_contents'
    PASSNOTOKEN = "passOnNoToken"
    PASSNOUSER = "passOnNoUser"
    PASSTHRU = "passthru"
    POLICYDELETE = "policydelete"
    POLICYWRITE = "policywrite"
    RESET = "reset"
    RESOLVERDELETE = "resolverdelete"
    RESOLVERWRITE = "resolverwrite"
    RESYNC = "resync"
    SET = "set"
    SETPIN = "setpin"
    SETREALM = "setrealm"
    SERIAL = "serial"
    SYSTEMDELETE = "configdelete"
    SYSTEMWRITE = "configwrite"
    TOKENLABEL = "tokenlabel"
    TOKENREALMS = "tokentealms"
    TOKENTYPE = "tokentype"
    UNASSIGN = "unassign"
    USERLIST = "userlist"


class LOGINMODE():
    __doc__ = """This is the list of possible values for the login mode."""
    USERSTORE = "userstore"
    PRIVACYIDEA = "privacyIDEA"


class ACTIONVALUE():
    __doc__ = """This is a list of usual action values for e.g. policy
    action-values like otppin."""
    TOKENPIN = "tokenpin"
    USERSTORE = "userstore"
    NONE = "none"


class PolicyClass(object):

    """
    The Policy_Object will contain all database policy entries for easy
    filtering and mangling.
    It will be created at the beginning of the request and is supposed to stay
    alive unchanged during the request.
    """

    def __init__(self):
        """
        Create the Policy_Object from the database table

        """
        self.policies = []
        # read the policies from the database and store it in the object
        policies = Policy.query.all()
        for pol in policies:
            # read each policy
            self.policies.append(pol.get())

    def get_policies(self, name=None, scope=None, realm=None, active=None,
                     resolver=None, user=None, client=None, action=None):
        """
        Return the policies of the given filter values

        :param name:
        :param scope:
        :param realm:
        :param active:
        :param resolver:
        :param user:
        :param client:
        :param action:
        :return: list of policies
        :rtype: list of dicts
        """
        reduced_policies = self.policies

        # Do exact matches for "name", "active" and "scope", as these fields
        # can only contain one entry
        p = [("name", name), ("active", active), ("scope", scope)]
        for searchkey, searchvalue in p:
            if searchvalue is not None:
                new_policies = []
                for policy in reduced_policies:
                    if policy.get(searchkey) == searchvalue:
                        new_policies.append(policy)
                reduced_policies = new_policies

        p = [("action", action), ("user", user), ("resolver", resolver),
             ("realm", realm)]
        for searchkey, searchvalue in p:
            if searchvalue is not None:
                new_policies = []
                # first we find policies, that really match!
                # Either with the real value or with a "*"
                # values can be excluded by a leading "!" or "-"
                for policy in reduced_policies:
                    value_found = False
                    value_excluded = False
                    # iterate through the list of values:
                    for value in policy.get(searchkey):
                        if len(value) and value[0] in ["!", "-"] and \
                                        searchvalue == value[1:]:
                            value_excluded = True
                        elif value in [searchvalue, "*"]:
                            value_found = True
                    if value_found and not value_excluded:
                        new_policies.append(policy)
                # We also find the policies with no desctinct information
                # about the request value
                for policy in reduced_policies:
                    if len(policy.get(searchkey)) == 0:
                        new_policies.append(policy)
                reduced_policies = new_policies

        # Match the client IP.
        # Client IPs may be direct machts, may be located in subnets or may
        # be excluded by a leading "-" or "!" sign.
        # The client definition in the policy may ba a comma seperated list.
        # It may start with a "-" or a "!" to exclude the client
        # from a subnet.
        # Thus a client 10.0.0.2 matches a policy "10.0.0.0/8, -10.0.0.1" but
        # the client 10.0.0.1 does not match the policy "10.0.0.0/8, -10.0.0.1".
        # An empty client definition in the policy matches all clients.
        if client is not None:
            new_policies = []
            for policy in reduced_policies:
                client_found = False
                client_excluded = False
                for polclient in policy.get("client"):
                    if polclient[0] in ['-', '!']:
                        # exclude the client?
                        if IPAddress(client) in IPNetwork(polclient[1:]):
                            log.debug("the client %s is excluded by %s in "
                                      "policy %s" % (client, polclient, policy))
                            client_excluded = True
                    elif IPAddress(client) in IPNetwork(polclient):
                        client_found = True
                if client_found and not client_excluded:
                    # The client was contained in the defined subnets and was
                    #  not excluded
                    new_policies.append(policy)

            # If there is a policy without any client, we also add it to the
            # accepted list.
            for policy in reduced_policies:
                if len(policy.get("client")) == 0:
                    new_policies.append(policy)
            reduced_policies = new_policies

        return reduced_policies

    def get_action_values(self, action, scope=SCOPE.AUTHZ, realm=None,
                          resolver=None, user=None, client=None, unique=False):
        """
        Get the defined action values for a certain action like
            scope: authorization
            action: tokentype
        would return a list of the tokentypes

            scope: authorization
            action: serial
        would return a list of allowed serials

        :param unique: if set, the function will raise an exception if more
        than one value is returned
        :return: A list of the allowed tokentypes
        :rtype: list
        """
        action_values = []
        policies = self.get_policies(scope=scope,
                                     action=action, active=True,
                                     realm=realm, resolver=resolver, user=user,
                                     client=client)
        for pol in policies:
            action_dict = pol.get("action", {})
            action_value = action_dict.get(action, "")
            """
            We must distinguish actions like:
                tokentype=totp hotp motp,
            where the string represents a list divided by spaces, and
                smstext='your otp is <otp>'
            where the spaces are part of the string.
            """
            if action_value.startswith("'") and action_value.endswith("'"):
                action_values.append(action_dict.get(action)[1:-1])
            else:
                action_values.extend(action_dict.get(action, "").split())

        if unique:
            action_values = list(set(action_values))
            if len(action_values) > 1:
                raise PolicyError("There are conflicting %s"
                                  " definitions!" % action)
        return action_values

# --------------------------------------------------------------------------
#
#  NEW STUFF
#
#


@log_with(log)
def set_policy(name=None, scope=None, action=None, realm=None, resolver=None,
               user=None, time=None, client=None, active=True):
    """
    Function to set a policy.
    If the policy with this name already exists, it updates the policy.
    It expects a dict of with the following keys:
    :param name: The name of the policy
    :param scope: The scope of the policy. Something like "admin", "system",
    "authentication"
    :param action: A scope specific action or a comma seperated list of actions
    :type active: basestring
    :param realm: A realm, for which this policy is valid
    :param resolver: A resolver, for which this policy is valid
    :param user: A username or a list of usernames
    :param time: N/A    if type()
    :param client: A client IP with optionally a subnet like 172.16.0.0/16
    :param active: If the policy is active or not
    :type active: bool
    :return: The database ID od the the policy
    :rtype: int
    """
    if type(action) == dict:
        action_list = []
        for k, v in action.iteritems():
            if v is not True:
                # value key
                action_list.append("%s=%s" % (k, v))
            else:
                # simple boolean value
                action_list.append(k)
        action = ", ".join(action_list)
    if type(action) == list:
        action = ", ".join(action)
    if type(realm) == list:
        realm = ", ".join(realm)
    if type(user) == list:
        user = ", ".join(user)
    if type(resolver) == list:
        resolver = ", ".join(resolver)
    if type(client) == list:
        client = ", ".join(client)
    p = Policy(name, action=action, scope=scope, realm=realm,
               user=user, time=time, client=client, active=active,
               resolver=resolver).save()
    return p


@log_with(log)
def enable_policy(name, enable=True):
    """
    Enable or disable the policy with the given name
    :param name:
    :return: ID of the policy
    """
    if not Policy.query.filter(Policy.name == name).first():
        raise ParameterError("The policy with name '%s' does not exist" % name)

    # Update the policy
    p = set_policy(name=name, active=enable)
    return p


@log_with(log)
def delete_policy(name):
    """
    Function to delete one named policy

    :param name: the name of the policy to be deleted
    :return: the count of the deleted policies.
    :rtype: int
    """
    p = Policy.query.filter_by(name=name)
    res = p.delete()
    db.session.commit()
    return res


@log_with(log)
def export_policies(policies):
    """
    This function takes a policy list and creates an export file from it
    
    :param policies: a policy definition
    :type policies: list of policy dictionaries
    :return: the contents of the file
    :rtype: string
    """
    file_contents = ""
    if len(policies) > 0:
        for policy in policies:
            file_contents += "[%s]\n" % policy.get("name")
            for key, value in policy.iteritems():
                file_contents += "%s = %s\n" % (key, value)
            file_contents += "\n"

    return file_contents


@log_with(log)
def import_policies(file_contents):
    """
    This function imports policies from a file.
    The file has a config_object format, i.e. the text file has a header
        [<policy_name>]
        key = value
    and key value pairs.

    :param file_contents: The contents of the file
    :type file_contents: basestring
    :return: number of imported policies
    :rtype: int
    """
    policies = ConfigObj(file_contents.split('\n'), encoding="UTF-8")
    res = 0
    for policy_name in policies.keys():
        ret = set_policy(name=policy_name,
                         action=eval(policies[policy_name].get("action")),
                         scope=policies[policy_name].get("scope"),
                         realm=eval(policies[policy_name].get("realm", "[]")),
                         user=eval(policies[policy_name].get("user", "[]")),
                         resolver=eval(policies[policy_name].get("resolver",
                                                                 "[]")),
                         client=eval(policies[policy_name].get("client", "[]")),
                         time=policies[policy_name].get("time", "")
                         )
        if ret > 0:
            log.debug("import policy %s: %s" % (policy_name, ret))
            res += 1
    return res


@log_with(log)
def get_static_policy_definitions(scope=None):
    """
    These are the static hard coded policy definitions.
    They can be enhanced by token based policy definitions, that can be found
    int lib.token.get_dynamic_policy_definitions.

    :param scope: Optional the scope of the policies
    :type scope: basestring
    :return: allowed scopes with allowed actions, the type of action and a
    description.
    :rtype: dict
    """

    pol = {
        SCOPE.ADMIN: {
            ACTION.ENABLE: {'type': 'bool',
                       'desc' : _('Admin is allowed to enable tokens.')},
            ACTION.DISABLE: {'type': 'bool',
                        'desc' : _('Admin is allowed to disable tokens.')},
            ACTION.SET: {'type': 'bool',
                    'desc' : _('Admin is allowed to set token properties.')},
            ACTION.SETPIN: {'type': 'bool',
                          'desc' : _('Admin is allowed to set the OTP PIN of tokens.')},
            ACTION.RESYNC: {'type': 'bool',
                       'desc' : _('Admin is allowed to resync tokens.')},
            ACTION.RESET: {'type': 'bool',
                      'desc' : _('Admin is allowed to reset the Failcounter of a token.')},
            ACTION.ASSIGN: {'type': 'bool',
                       'desc' : _('Admin is allowed to assign a token to a user.')},
            ACTION.UNASSIGN: {'type': 'bool',
                         'desc' : _('Admin is allowed to remove the token from a user, '
                         'i.e. unassign a token.')},
            ACTION.IMPORT: {'type': 'bool',
                       'desc' : _('Admin is allowed to import token files.')},
            ACTION.DELETE: {'type': 'bool',
                       'desc' : _('Admin is allowed to remove tokens from the database.')},
            ACTION.USERLIST: {'type': 'bool',
                         'desc' : _('Admin is allowed to view the list of the users.')},
            ACTION.MACHINELIST: {'type': 'bool',
                                 'desc': _('The Admin is allowed to list '
                                            'the machines.')},
            ACTION.MACHINETOKENS: {'type': 'bool',
                                   'desc': _('The Admin is allowed to attach '
                                             'and detach tokens to machines.')},
            ACTION.AUTHITEMS: {'type': 'bool',
                               'desc': _('The Admin is allowed to fetch '
                                         'authentication items of tokens '
                                         'assigned to machines.')},
            # 'checkstatus': {'type': 'bool',
            #                 'desc' : _('Admin is allowed to check the status of a challenge'
            #                            ' resonse token.'),
            #                 "group": "tools"},
            ACTION.TOKENREALMS: {'type': 'bool',
                                 'desc' : _('Admin is allowed to manage the '
                                            'realms of a token.')},
            ACTION.GETSERIAL: {'type': 'bool',
                               'desc': _('Admin is allowed to retrieve a serial'
                                         ' for a given OTP value.'),
                               "group": "tools"},
            # 'checkserial': {'type': 'bool',
            #                 'desc': _('Admin is allowed to check if a serial '
            #                           'is unique'),
            #                 "group": "tools"},
            ACTION.COPYTOKENPIN: {'type': 'bool',
                             'desc' : _('Admin is allowed to copy the PIN of one token '
                                        'to another token.'),
                             "group": "tools"},
            ACTION.COPYTOKENUSER: {'type': 'bool',
                              'desc' : _('Admin is allowed to copy the assigned user to another'
                                         ' token, i.e. assign a user ot '
                                         'another token.'),
                              "group": "tools"},
            ACTION.LOSTTOKEN: {'type': 'bool',
                               'desc': _('Admin is allowed to trigger the '
                                          'lost token workflow.'),
                               "group": "tools"},
            # 'getotp': {
            #     'type': 'bool',
            #     'desc': _('Allow the administrator to retrieve OTP values for tokens.'),
            #     "group": "tools"},
            ACTION.SYSTEMWRITE: {'type': 'bool',
                                "desc" : _("Admin is allowed to write and modify the "
                                 "system configuration."),
                                "group": "system"},
            ACTION.SYSTEMDELETE: {'type': 'bool',
                                 "desc" : _("Admin is allowed to delete "
                                            "keys in the system configuration."),
                                 "group": "system"},
            ACTION.POLICYWRITE: {'type': 'bool',
                                "desc" : _("Admin is allowed to write and modify the "
                                 "policies."),
                                "group": "system"},
            ACTION.POLICYDELETE: {'type': 'bool',
                                 "desc" : _("Admin is allowed to delete "
                                            "policies."),
                                 "group": "system"},
            ACTION.RESOLVERWRITE: {'type': 'bool',
                                "desc" : _("Admin is allowed to write and modify the "
                                 "resolver and realm configuration."),
                                "group": "system"},
            ACTION.RESOLVERDELETE: {'type': 'bool',
                                 "desc" : _("Admin is allowed to delete "
                                            "resolvers and realms."),
                                 "group": "system"},
            ACTION.MACHINERESOLVERWRITE: {'type': 'bool',
                                          'desc': _("Admin is allowed to "
                                                    "write and modify the "
                                                    "machine resolvers."),
                                          'group': "system"},
            ACTION.MACHINERESOLVERDELETE: {'type': 'bool',
                                           'desc': _("Admin is allowed to "
                                                     "delete "
                                                     "machine resolvers."),
                                           'group': "system"},
            ACTION.AUDIT: {'type': 'bool',
                           "desc": _("Admin is allowed to view the Audit log."),
                           "group": "system"}
        },
        # 'gettoken': {
        #     'max_count_dpw': {'type': 'int',
        #                       'desc' : _('When OTP values are retrieved for a DPW token, '
        #                                  'this is the maximum number of retrievable OTP values.')},
        #     'max_count_hotp': {'type': 'int',
        #                        'desc' : _('When OTP values are retrieved for a HOTP token, '
        #                                   'this is the maximum number of retrievable OTP values.')},
        #     'max_count_totp': {'type': 'int',
        #                        'desc' : _('When OTP values are retrieved for a TOTP token, '
        #                                   'this is the maximum number of retrievable OTP values.')},
        # },
        SCOPE.USER: {
            ACTION.ASSIGN: {
                'type': 'bool',
                'desc': _("The user is allowed to assign an existing token"
                          " that is not yet assigned"
                          " using the token serial number.")},
            ACTION.DISABLE: {'type': 'bool',
                        'desc': _('The user is allowed to disable his own tokens.')},
            ACTION.ENABLE: {'type': 'bool',
                       'desc': _("The user is allowed to enable his own tokens.")},
            ACTION.DELETE: {'type': 'bool',
                       "desc": _("The user is allowed to delete his own tokens.")},
            ACTION.UNASSIGN: {'type': 'bool',
                              "desc": _("The user is allowed to unassign his "
                                        "own tokens.")},
            ACTION.RESYNC: {'type': 'bool',
                            "desc": _("The user is allowed to resyncronize his "
                                      "tokens.")},
            ACTION.RESET: {'type': 'bool',
                           'desc': _('The user is allowed to reset the '
                                     'failcounter of his tokens.')},
            ACTION.SETPIN: {'type': 'bool',
                            "desc": _("The user is allowed to set the OTP PIN "
                                      "of his tokens.")},
            ACTION.OTPPINMAXLEN: {'type': 'int',
                                  'value': range(0, 32),
                                  "desc": _("Set the maximum allowed length "
                                            "of the OTP PIN.")},
            ACTION.OTPPINMINLEN: {'type': 'int',
                                  'value': range(0, 32),
                                  "desc": _("Set the minimum required length "
                                            "of the OTP PIN.")},
            ACTION.OTPPINCONTENTS: {'type': 'str',
                                    "desc": _("Specifiy the required "
                                              "contents of the OTP PIN. "
                                              "(c)haracters, (n)umeric, "
                                              "(s)pecial, (o)thers. [+/-]!")},
            # 'setMOTPPIN': {'type': 'bool',
            #                "desc": _("The user is allowed to set the mOTP PIN of his mOTP tokens.")},
            # 'getotp': {'type': 'bool',
            #            "desc": _("The user is allowed to retrieve OTP values for his own tokens.")},
            # 'activateQR': {'type': 'bool',
            #                "desc": _("The user is allowed to enroll a QR token.")},
            # 'max_count_dpw': {'type': 'int',
            #                   "desc": _("This is the maximum number of OTP values, the user is allowed to retrieve for a DPW token.")},
            # 'max_count_hotp': {'type': 'int',
            #                    "desc": _("This is the maximum number of OTP values, the user is allowed to retrieve for a HOTP token.")},
            # 'max_count_totp': {'type': 'int',
            #                    "desc": _("This is the maximum number of OTP values, the user is allowed to retrieve for a TOTP token.")},
            ACTION.AUDIT: {
                'type': 'bool',
                'desc': _('Allow the user to view his own token history.')},
            # 'getserial': {
            #     'type': 'bool',
            #     'desc': _('Allow the user to search an unassigned token by OTP value.')},
            },
        SCOPE.ENROLL: {
            ACTION.MAXTOKENREALM: {
                'type': 'int',
                'desc': _('Limit the number of allowed tokens in a realm.')},
            ACTION.MAXTOKENUSER: {
                'type': 'int',
                'desc': _('Limit the number of tokens a user may have '
                          'assigned.')},
            ACTION.OTPPINRANDOM: {
                'type': 'int',
                'value': range(0, 32),
                "desc": _("Set a random OTP PIN with this length for a "
                          "token.")},
            ACTION.ENCRYPTPIN: {
                'type': 'bool',
                "desc": _("The OTP PIN can be hashed or encrypted. Hashing "
                          "the PIN is the default behaviour.")},
            ACTION.TOKENLABEL: {
                'type': 'str',
                'desc': _("Set label for a new enrolled Google Authenticator. "
                          "Possible tags are <u> (user), <r> ("
                          "realm), <s> (serial).")},
            ACTION.AUTOASSIGN: {
                'type': 'bool',
                'desc': _("Users can assign a token just by using the "
                          "unassigned token to authenticate.")},
            # 'ignore_autoassignment_pin': {
            #     'type': 'bool',
            #     'desc' : _("Do not set password from auto assignment as token pin.")},
            ACTION.LOSTTOKENPWLEN: {
                'type': 'int',
                'value': range(1, 32),
                'desc': _('The length of the password in case of '
                          'temporary token (lost token).')},
            ACTION.LOSTTOKENPWCONTENTS: {
                'type': 'str',
                'desc': _('The contents of the temporary password, '
                          'described by the characters C, c, n, s.')},
            ACTION.LOSTTOKENVALID: {
                'type': 'int',
                'value': range(1, 61),
                'desc': _('The length of the validity for the temporary '
                          'token (in days).')},
            },
        SCOPE.AUTH: {
            ACTION.OTPPIN: {
                'type': 'str',
                'value': [ACTIONVALUE.TOKENPIN, ACTIONVALUE.USERSTORE,
                          ACTIONVALUE.NONE],
                'desc': _('Either use the Token PIN , use the Userstore '
                          'Password or use no fixed password '
                          'component.')},
            ACTION.PASSTHRU: {
                'type': 'bool',
                'desc': _('If set, the user in this realm will be '
                          'authenticated against the UserIdResolver,'
                          ' if the user has no tokens assigned.')
                },
            ACTION.PASSNOTOKEN: {
                'type': 'bool',
                'desc': _('If the user has no token, the authentication '
                          'request for this user will always be true.')
                },
            ACTION.PASSNOUSER: {
                'type': 'bool',
                'desc': _('If the user user does not exist, '
                          'the authentication request for this '
                          'non-existing user will always be true.')
                },
            # 'qrtanurl': {
            #     'type': 'str',
            #     'desc': _('The URL for the half automatic mode that should be '
            #             'used in a QR Token')
            #     },
            # 'challenge_response': {
            #     'type': 'str',
            #     'desc': _('A list of tokentypes for which challenge response '
            #               'should be used.')
            #     }
            },
        SCOPE.AUTHZ: {
            ACTION.TOKENTYPE: {
                'type': 'str',
                'desc': _('The user will only be authenticated with this '
                          'very tokentype.')},
            ACTION.SERIAL: {
                'type': 'str',
                'desc': _('The user will only be authenticated if the serial '
                          'number of the token matches this regexp.')},
            ACTION.SETREALM: {
                'type': 'str',
                'desc': _('The Realm of the user is set to this very realm. '
                        'This is important if the user is not contained in '
                        'the default realm and can not pass his realm.')},
            ACTION.NODETAILSUCCESS: {
                'type': 'bool',
                'desc': _('In case of successful authentication additional '
                        'no detail information will be returned.')},
            ACTION.NODETAILFAIL: {
                'type': 'bool',
                'desc': _('In case of failed authentication additional '
                        'no detail information will be returned.')}
            },
        SCOPE.WEBUI: {
            ACTION.LOGINMODE: {
                'type': 'str',
                'desc': _(
                    'If set to "privacyIDEA" the users and admins need to '
                    'authenticate against privacyIDEA when they log in '
                    'to the Web UI. Defaults to "userstore"'),
                'value': [LOGINMODE.USERSTORE, LOGINMODE.PRIVACYIDEA],
            },
            ACTION.LOGOUTTIME: {
                'type': 'int',
                'desc': _("Set the time in seconds after which the user will "
                          "be logged out from the WebUI. Default: 30")
            }
        }

        # 'ocra': {
        #     'request': {
        #         'type': 'bool',
        #         'desc': _('Allow to do a ocra/request.')},
        #     'status': {
        #         'type': 'bool',
        #         'desc': _('Allow to check the transaction status.')},
        #     'activationcode': {
        #         'type': 'bool',
        #         'desc': _('Allow to do an ocra/getActivationCode.')},
        #     'calcOTP': {
        #         'type': 'bool',
        #         'desc': _('Allow to do an ocra/calculateOtp.')}
        # },
    }
    if scope:
        ret = pol.get(scope, {})
    else:
        ret = pol
    return ret
