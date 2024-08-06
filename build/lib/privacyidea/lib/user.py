# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#
#  Nov 27, 2014 Cornelius Kölbel <cornelius@privacyidea.org>
#               Migration to flask
#               Rewrite of methods
#               100% test code coverage
#  May 08, 2014 Cornelius Kölbel
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
# 2014-10-03 fix getUsername function
#            Cornelius Kölbel <cornelius@privcyidea.org>
#
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
'''
There are the library functions for user functions.
It depends on the lib.resolver and lib.realm.

There are and must be no dependencies to the token functions (lib.token)
or to webservices!
'''

import logging
import traceback

from .error import UserError
from ..api.lib.utils import (getParam,
                             optional)
from .log import log_with
from .resolver import (get_resolver_object,
                       get_resolver_type)

from .realm import (get_realms,
                    get_default_realm,
                    get_realm)
from .config import get_from_config

ENCODING = 'utf-8'

log = logging.getLogger(__name__)


@log_with(log)
class User(object):
    """
    The user has the attributes
      login, realm and resolver.
    Usually a user can be found via "login@realm".
    
    A user object with an empty login and realm should not exist,
    whereas a user object could have an empty resolver.
    """

    # In some test case the login attribute from a not
    # initialized user is requested. This is why we need
    # these dummy class attributes.
    login = ""
    realm = ""
    resolver = ""
    
    def __init__(self, login="", realm="", resolver=""):
        self.login = login or ""
        self.realm = realm or ""
        self.resolver = resolver or ""
        if not self.resolver:
            # set the resolver implicitly!
            self.get_resolvers()

        self.Resolvers_list = []

    def is_empty(self):
        # ignore if only resolver is set! as it makes no sense
        if len(self.login or "") + len(self.realm or "") == 0:
            return True
        else:
            return False

    def __eq__(self, other):
        """
        Compare two User Objects.

        :param other: The other User object, to which this very object is
        compared.
        :type other: User object
        :return: True or False
        :rtype: bool
        """
        return (self.login == other.login) and (self.resolver ==
                                                other.resolver) and (
                self.realm == other.realm)

    def __str__(self):
        ret = "<empty user>"
        if self.is_empty() is False:
            loginname = ""
            try:
                loginname = unicode(self.login)
            except UnicodeEncodeError:  # pragma: no cover
                loginname = unicode(self.login.encode(ENCODING))

            conf = ''
            if self.resolver is not None and len(self.resolver) > 0:
                conf = '.%s' % (unicode(self.resolver))
            ret = '<%s%s@%s>' % (loginname, conf, unicode(self.realm))

        return ret

    def __repr__(self):
        ret = ('User(login=%r, realm=%r, resolver=%r)' %
               (self.login, self.realm, self.resolver))
        return ret
    
    @log_with(log)
    def get_realm_resolvers(self):
        """
        This returns the list of the resolvernames in the realm.
        It does not take into account, the self.login (username)!
    
        :return: list of resolvers in self.realm
        :rtype: list
        """
        resolvers = []
        realm_config = get_realms(self.realm)
        resolvers_in_realm = realm_config.get(self.realm, {})\
                                         .get("resolver", {})
        for resolver in resolvers_in_realm:
            resolvername = resolver.get("name")
            # resolvertype = resolver.get("type")
            resolvers.append(resolvername)
        return resolvers
    
    def get_resolvers(self):
        """
        This returns the list of the resolvernames of the user.
        If no resolver attribute exists at the moment, the user is searched
        in the realm and according to this the resolver attribute is set.
        (aka getResolversOfUser)

        .. note:: If the user does not exist in the realm, then an empty
           list is returned!

        :return: list of resolvers for self.login
        :rtype: list of strings
        """
        if self.resolver:
            return [self.resolver]
        
        resolvers = []
        resolvers_in_realm = self.get_realm_resolvers()
        for resolvername in resolvers_in_realm:
            # test, if the user is contained in this resolver
            y = get_resolver_object(resolvername)
            if y is None:  # pragma: no cover
                log.error("Resolver %r not found!" % resolvername)
            else:
                uid = y.getUserId(self.login)
                if uid not in ["", None]:
                    log.info("user %r found in resolver %r" % (self.login,
                                                               resolvername))
                    log.info("userid resolved to %r " % uid)
                    resolvers.append(resolvername)
                else:
                    log.debug("user %r not found"
                              " in resolver %r" % (self.login,
                                                   resolvername))
        if len(resolvers) == 1:
            # set the resolver that was found
            self.resolver = resolvers[0]
        return resolvers
    
    def get_user_identifiers(self):
        """
        This returns the UserId  information from the resolver object and
        the resolvertype and the resolvername
        (former: getUserId)
        (former: getUserResolverId)
        :return: The userid, the resolver type and the resolver name
                 like (1000, "passwdresolver", "resolver1")
        :rtype: tuple
        """
        if not self.resolver:
            self.get_resolvers()
        if len(self.resolver) == 0:
            # The resolver list is empty
            raise UserError("The user can not be found in any resolver in "
                            "this realm!")
        rtype = get_resolver_type(self.resolver)
        y = get_resolver_object(self.resolver)
        if y is None:
            raise UserError("The resolver '%s' does not exist!" %
                            self.resolver)
        uid = y.getUserId(self.login)
        return uid, rtype, self.resolver
       
    def get_user_info(self):
        """
        return the detailed information for the user

        :return: a dict with all the userinformation
        :rtype: dict
        """
        (uid, _rtype, _resolver) = self.get_user_identifiers()
        y = get_resolver_object(self.resolver)
        userInfo = y.getUserInfo(uid)
        return userInfo
    
    @log_with(log)
    def get_user_phone(self, phone_type='phone'):
        """
        Returns the phone numer of a user
    
        :param phone_type: The type of the phone, i.e. either mobile or
                           phone (land line)
        :type phone_type: string
    
        :returns: list with phone numbers of this user object
        """
        userinfo = self.get_user_info()
        if phone_type in userinfo:
            log.debug("got user phone %r of type %r"
                      % (userinfo[phone_type], phone_type))
            return userinfo[phone_type]
        else:
            log.warning("userobject (%r) has no phone of type %r."
                        % (self, phone_type))
            return ""

    @log_with(log)
    def get_user_realms(self):
        """
        Returns a list of the realms, a user belongs to.
        Usually this will only be one realm.
        But if the user object has no realm but only a resolver,
        than all realms, containing this resolver are returned.
        This function is used for the policy module
        
        :return: realms of the user
        :rtype: list
        """
        allRealms = get_realms()
        Realms = []
        if self.realm == "" and self.resolver == "":
            defRealm = get_default_realm().lower()
            Realms.append(defRealm)
            self.realm = defRealm
        elif self.realm != "":
            Realms.append(self.realm.lower())
        else:
            # User has not realm!
            # we have got a resolver and will get all realms
            # the resolver belongs to.
            for key, val in allRealms.items():
                log.debug("evaluating realm %r: %r " % (key, val))
                for reso in val.get('resolver', []):
                    resoname = reso.get("name")
                    if resoname == self.resolver:
                        Realms.append(key.lower())
                        log.debug("added realm %r to Realms due to "
                                  "resolver %r" % (key, self.resolver))
        return Realms
    
    @log_with(log)
    def check_password(self, password):
        """
        The password of the user is checked against the user source
        
        :param password: The clear text password
        :return: the username of the authenticated user.
                 If unsuccessful, returns None
        :rtype: string/None
        """
        success = None
        try:
            log.info("User %r from realm %r tries to "
                     "authenticate" % (self.login, self.realm))
            if type(self.login) != unicode:
                self.login = self.login.decode(ENCODING)
            res = self.get_resolvers()
            # Now we know, the resolvers of this user and we can verify the
            # password
            if len(res) == 1:
                y = get_resolver_object(self.resolver)
                uid, _rtype, _rname = self.get_user_identifiers()
                if y.checkPass(uid, password):
                    success = "%s@%s" % (self.login, self.realm)
                    log.debug("Successfully authenticated user %r." % self)
                else:
                    log.info("user %r failed to authenticate." % self)

            elif len(res) == 0:
                log.error("The user %r exists in NO resolver." %
                          (self))
            else:
                log.error("The user %r exists in more than one resolver" %
                          (self))
                log.error(res)
        except UserError as e:  # pragma: no cover
            log.error("Error while trying to verify the username: %r"
                      % e.description)
        except Exception as e:  # pragma: no cover
            log.error("Error checking password within module %r" % (e))
            log.error("%s" % traceback.format_exc())
    
        return success
    
    @log_with(log)
    def get_search_fields(self):
        """
        Return the valid search fields of a user.
        The search fields are defined in the UserIdResolver class.
        
        :return: searchFields with name (key) and type (value)
        :rtype: dict
        """
        searchFields = {}
    
        for reso in self.get_resolvers():
            # try to load the UserIdResolver Class
            try:
                y = get_resolver_object(reso)
                sf = y.getSearchFields()
                searchFields[reso] = sf
    
            except Exception as e:  # pragma: no cover
                log.warning("module %r: %r" % (reso, e))
    
        return searchFields


####################################################################

@log_with(log)
def split_user(username):
    """
    Split the username of the form user@realm into the username and the realm
    splitting myemail@emailprovider.com@realm is also possible and will
    return (myemail@emailprovider, realm).
    
    We can also split realm\\user to (user, realm)
    
    :param username: the username to split
    :type username: string
    :return: username and realm
    :rtype: tuple
    """
    user = username.strip()
    realm = ""

    l = user.split('@')
    if len(l) >= 2:
        # split the last
        (user, realm) = user.rsplit('@', 1)
    else:
        l = user.split('\\')
        if len(l) >= 2:
            (realm, user) = user.rsplit('\\', 1)

    return user, realm


def get_user_from_param(param, optionalOrRequired=optional):
    """
    Find the parameters user, realm and resolver and
    create a user object from these parameters.
    
    An exception is raised, if a user in a realm is found in more
    than one resolvers.
    
    :param param: The dictionary of request parameters
    :type param: dict
    :return: User as found in the parameters
    :rtype: User object
    """
    realm = ""
    username = getParam(param, "user", optionalOrRequired)

    if username is None:
        username = ""
    else:
        splitAtSign = get_from_config("splitAtSign", "true")
        if splitAtSign.lower() == "true":
            (username, realm) = split_user(username)

    if "realm" in param:
        realm = param["realm"]

    if username != "":
        if realm is None or realm == "":
            realm = get_default_realm()

    user_object = User(login=username, realm=realm)

    if "resolver" in param:
        user_object.resolver = param["resolver"]
    else:
        res = user_object.get_resolvers()
        if len(res) > 1:
            log.error("user %r is in more than one resolver: %r" %
                      (user_object, res))
            raise Exception("The user %r is in more than one resolver:" %
                            (user_object))
    return user_object


@log_with(log)
def get_user_list(param={}, user=None):
    users = []
    resolvers = []
    searchDict = {"username": "*"}

    # we have to recreate a new searchdict without the realm key
    # as delete does not work
    for key in param:
        lval = param[key]
        if key == "realm":
            continue
        if key == "resolver":
            continue

        searchDict[key] = lval
        log.debug("Parameter key:%r=%r" % (key, lval))

    # determine which scope we want to show
    param_resolver = getParam(param, "resolver")
    param_realm = getParam(param, "realm")
    user_resolver = None
    user_realm = None
    if user is not None:
        user_resolver = user.resolver
        user_realm = user.realm
        
    # Append all possible resolvers
    if param_resolver:
        resolvers.append(param_resolver)
    if user_resolver:
        resolvers.append(user_resolver)
    for pu_realm in [param_realm, user_realm]:
        if pu_realm:
            realm_config = get_realm(pu_realm)
            for r in realm_config.get("resolver", {}):
                if r.get("name"):
                    resolvers.append(r.get("name"))

    if not (param_resolver or user_resolver or param_realm or user_realm):
        # if no realm or resolver was specified, we search the resolvers
        # in all realms
        all_realms = get_realms()
        for _name, res_list in all_realms.iteritems():
            for resolver_entry in res_list.get("resolver"):
                resolvers.append(resolver_entry.get("name"))

    for resolver_name in set(resolvers):
        try:
            log.debug("Check for resolver class: %r" % resolver_name)
            y = get_resolver_object(resolver_name)
            log.debug("with this search dictionary: %r " % searchDict)
            ulist = y.getUserList(searchDict)
            log.debug("Found this userlist: %r" % ulist)
            users.extend(ulist)

        except KeyError as exx:  # pragma: no cover
            log.error("%r" % (exx))
            log.error("%s" % traceback.format_exc())
            raise exx

        except Exception as exx:  # pragma: no cover
            log.error("%r" % (exx))
            log.error("%s" % traceback.format_exc())
            continue

    return users


@log_with(log)
def get_user_info(userid, resolvername):
    """
    return the detailed information for a user in a resolver
    
    :param userid: The id of the user in a resolver
    :type userid: string
    :param resolvername: The name of the resolver
    :return: a dict with all the userinformation
    :rtype: dict
    """
    userInfo = {}
    if len(userid) > 0:
        y = get_resolver_object(resolvername)
        userInfo = y.getUserInfo(userid)
    return userInfo


@log_with(log)
def get_username(userid, resolvername):
    """
    Determine the username for a given id and a resolvername.
    
    :param userid: The id of the user in a resolver
    :type userid: string
    :param resolvername: The name of the resolver
    :return: the username or "" if it does not exist
    :rtype: string
    """
    username = ""
    if len(userid) > 0:
        y = get_resolver_object(resolvername)
        if y:
            username = y.getUsername(userid)
    return username
   
    
