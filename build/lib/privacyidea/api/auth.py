# -*- coding: utf-8 -*-
#
# 2015-04-03 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#            Add logout time to response
# 2014-12-15 Cornelius Kölbel, info@privacyidea.org
#            Initial creation
#
# (c) Cornelius Kölbel
# Info: http://www.privacyidea.org
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
__doc__ = """This REST API is used to authenticate the users.

Authentication of users and admins is tested in tests/test_api_roles.py

You need to authenticate for all administrative tasks. If you are not
authenticated, the API returns a 401 response.

To authenticate you need to send a POST request to /auth containing username
and password.
"""
from flask import (Blueprint,
                   request,
                   url_for,
                   current_app,
                   jsonify,
                   abort,
                   g)
from lib.utils import (send_result, remove_session_from_param)
from ..lib.crypto import geturandom
from ..lib.error import AuthError
from ..lib.auth import verify_db_admin
import jwt
import json
from functools import wraps
from datetime import (datetime,
                      timedelta)
from privacyidea.lib.audit import getAudit
from privacyidea.lib.auth import check_webui_user, ROLE
from privacyidea.lib.user import User
from privacyidea.lib.user import split_user
from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.realm import get_default_realm
from privacyidea.api.lib.postpolicy import postpolicy, get_logout_time


jwtauth = Blueprint('jwtauth', __name__)


@jwtauth.before_request
def before_request():
    """
    This is executed before the request
    """
    g.policy_object = PolicyClass()
    g.audit_object = getAudit(current_app.config)
    g.audit_object.log({"success": False,
                        "client": request.remote_addr,
                        "client_user_agent": request.user_agent.browser,
                        "privacyidea_server": request.host,
                        "action": "%s %s" % (request.method, request.url_rule),
                        "action_detail": "",
                        "info": ""})
    request.all_data = remove_session_from_param(request.values, request.data)


@jwtauth.route('', methods=['POST'])
@postpolicy(get_logout_time)
def get_auth_token():
    """
    This call verifies the credentials of the user and issues an
    authentication token, that is used for the later API calls. The
    authentication token has a validity, that is usually 1 hour.

    :jsonparam username: The username of the user who wants to authenticate to
        the API.
    :type username: basestring
    :jsonparam password: The password/credentials of the user who wants to
        authenticate to the API.

    :return: A json response with an authentication token, that needs to be
        used in any further request.

    :status 200: in case of success
    :status 401: if authentication fails

    **Example Authentication Request**:

    .. sourcecode:: http

       POST /auth HTTP/1.1
       Host: example.com
       Accept: application/json

       username=admin
       password=topsecret

    **Example Authentication Response**:

    .. sourcecode:: http

       HTTP/1.0 200 OK
       Content-Length: 354
       Content-Type: application/json

       {
            "id": 1,
            "jsonrpc": "2.0",
            "result": {
                "status": true,
                "value": {
                    "token": "eyJhbGciOiJIUz....jdpn9kIjuGRnGejmbFbM"
                }
            },
            "version": "privacyIDEA unknown"
       }

    **Response for failed authentication**:

    .. sourcecode:: http

       HTTP/1.1 401 UNAUTHORIZED
       Content-Type: application/json
       Content-Length: 203

       {
          "id": 1,
          "jsonrpc": "2.0",
          "result": {
            "error": {
              "code": -401,
              "message": "missing Authorization header"
            },
            "status": false
          },
          "version": "privacyIDEA unknown",
          "config": {
            "logout_time": 30
          }
       }

    """
    validity = timedelta(hours=1)
    username = request.all_data.get("username")
    password = request.all_data.get("password")
    realm = ""
    secret = current_app.secret_key
    # This is the default role for the logged in user.
    # The role privileges may be risen to "admin"
    role = ROLE.USER
    # The way the user authenticated. This could be
    # "password" = The admin user DB or the user store
    # "pi" = The admin or the user is authenticated against privacyIDEA
    authtype = "password"
    if username is None:
        raise AuthError("Authentication failure",
                        "missing Username",
                        status=401)
    # Verify the password
    admin_auth = False
    user_auth = False
    if verify_db_admin(username, password):
        role = ROLE.ADMIN
        admin_auth = True

    if not admin_auth:
        # The user could not be identified against the admin database,
        # so we do the rest of the check
        username, realm = split_user(username)
        realm = realm or get_default_realm()
        user_obj = User(username, realm)
        options = {"g": g,
                   "clientip": request.remote_addr}
        superuser_realms = current_app.config.get("SUPERUSER_REALM", [])
        user_auth, role = check_webui_user(user_obj,
                                           password,
                                           options=options,
                                           superuser_realms=superuser_realms)

    if not admin_auth and not user_auth:
        raise AuthError("Authentication failure",
                        "Wrong credentials", status=401)

    # Add the role to the JWT, so that we can verify it internally
    # Add the authtype to the JWT, so that we could use it for access
    # definitions
    token = jwt.encode({"username": username,
                        "realm": realm,
                        "nonce": geturandom(hex=True),
                        "role": role,
                        "authtype": authtype,
                        "exp": datetime.utcnow() + validity,
                        "rights": "TODO"},
                       secret)
    g.audit_object.log({"success": True,
                        "administrator": username,
                        "jwt_token": token})
    # Add the role to the response, so that the WebUI can make decisions
    # based on this (only show selfservice, not the admin part)
    return send_result({"token": token,
                        "role": role,
                        "username": username,
                        "realm": realm,
                        "rights": "TODO"})


def admin_required(f):
    """
    This is a decorator for routes, that require to be authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        check_auth_token(required_role=["admin"])
        return f(*args, **kwargs)
    return decorated_function


def user_required(f):
    """
    This is a decorator for routes, that require to be authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        check_auth_token(required_role=["user", "admin"])
        return f(*args, **kwargs)
    return decorated_function


def check_auth_token(required_role=None):
    """
    This checks the authentication token
    
    You need to pass an authentication header:
    
        Authorization: <token>
        
    You can do this using httpie like this:
    
        http -j POST http://localhost:5000/system/getConfig Authorization:ewrt
    """
    auth_token = request.headers.get('Authorization', None)
    if auth_token is None:
        raise AuthError("Authentication failure",
                        "missing Authorization header",
                        status=401)
    try:
        r = jwt.decode(auth_token, current_app.secret_key)
    except jwt.DecodeError as err:
        raise AuthError("Authentication failure",
                        "error during decoding your token: %s" % err,
                        status=401)
    except jwt.ExpiredSignature as err:
        raise AuthError("Authentication failure",
                        "Your token has expired: %s" % err,
                        status=401)
    if required_role and r.get("role") not in required_role:
        # If we require a certain role like "admin", but the users role does
        # not match
        raise AuthError("Authentication failure",
                        "You do not have the necessary role (%s) to access "
                        "this resouce!" % (required_role),
                        status=401)
    g.logged_in_user = {"username": r.get("username"),
                        "realm": r.get("realm"),
                        "role": r.get("role")}

