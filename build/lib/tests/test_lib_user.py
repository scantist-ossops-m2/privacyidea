"""
This test file tests the lib.user

The lib.user.py only depends on the database model
"""
PWFILE = "tests/testdata/passwd"
PWFILE2 = "tests/testdata/passwords"

from .base import MyTestCase
from privacyidea.lib.resolver import (save_resolver)
from privacyidea.lib.realm import (set_realm)
from privacyidea.lib.user import (User,
                                  get_username,
                                  get_user_info,
                                  get_user_list,
                                  split_user,
                                  get_user_from_param)


class UserTestCase(MyTestCase):
    """
    Test the user on the database level
    """
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"
    resolvername3 = "reso3"
    realm1 = "realm1"
    realm2 = "realm2"
    
    def test_00_create_user(self):
        rid = save_resolver({"resolver": self.resolvername1,
                               "type": "passwdresolver",
                               "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)
               
        (added, failed) = set_realm(self.realm1,
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)
        
        user = User(login="root",
                    realm=self.realm1,
                    resolver=self.resolvername1)
        
        user_str = "%s" % user
        self.assertTrue(user_str == "<root.resolver1@realm1>", user_str)
        
        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())
        
        user_repr = "%r" % user
        expected = ("User(login='root', realm='realm1', resolver='resolver1')")
        self.assertTrue(user_repr == expected, user_repr)
        
    def test_01_resolvers_of_user(self):
        user = User(login="root",
                    realm=self.realm1)
        resolvers = user.get_realm_resolvers()
        self.assertTrue(self.resolvername1 in resolvers, resolvers)
        self.assertFalse(self.resolvername2 in resolvers, resolvers)
        
        resolvers = user.get_resolvers()
        self.assertTrue(self.resolvername1 in resolvers, resolvers)
        self.assertFalse(self.resolvername2 in resolvers, resolvers)
        
        user2 = User(login="root",
                     realm=self.realm1,
                     resolver=self.resolvername1)
        resolvers = user2.get_resolvers()
        self.assertTrue(self.resolvername1 in resolvers, resolvers)
        self.assertFalse(self.resolvername2 in resolvers, resolvers)
        
    def test_02_get_user_identifiers(self):
        user = User(login="root",
                    realm=self.realm1)
        (uid, rtype, resolvername) = user.get_user_identifiers()
        self.assertTrue(uid == "0", uid)
        self.assertTrue(rtype == "passwdresolver", rtype)
        self.assertTrue(resolvername == self.resolvername1, resolvername)
        
    def test_03_get_username(self):
        username = get_username("0", self.resolvername1)
        self.assertTrue(username == "root", username)
        
    def test_04_get_user_info(self):
        userinfo = get_user_info("0", self.resolvername1)
        self.assertTrue(userinfo.get("description") == "root", userinfo)
        
    def test_05_get_user_list(self):
        # all users
        userlist = get_user_list()
        self.assertTrue(len(userlist) > 10, userlist)
        
        # users from one realm
        userlist = get_user_list({"realm": self.realm1,
                                  "username": "root",
                                  "resolver": self.resolvername2})
        self.assertTrue(len(userlist) == 1, userlist)
        
        # get the list with user
        userlist = get_user_list(user=User(login="root",
                                           resolver=self.resolvername1,
                                           realm=self.realm1))
        self.assertTrue(len(userlist) > 10, userlist)
        
    def test_06_get_user_phone(self):
        phone = User(login="cornelius", realm=self.realm1).get_user_phone()
        self.assertTrue(phone == "+49 561 3166797", phone)
        
        phone = User(login="cornelius",
                     realm=self.realm1).get_user_phone("landline")
        self.assertTrue(phone == "", phone)
        
    def test_07_get_user_realms(self):
        user = User(login="cornelius", realm=self.realm1)
        realms = user.get_user_realms()
        self.assertTrue(len(realms) == 1, realms)
        self.assertTrue(self.realm1 in realms, realms)
        
        # test for default realm
        user = User(login="root")
        realms = user.get_user_realms()
        self.assertTrue(len(realms) == 1, realms)
        
        # test for user with only a resolver
        user = User(login="root", resolver=self.resolvername1)
        realms = user.get_user_realms()
        self.assertTrue(len(realms) == 1, realms)
        self.assertTrue(self.realm1 in realms, realms)
        
    def test_08_split_user(self):
        user = split_user("user@realm")
        self.assertTrue(user == ("user", "realm"), user)
        
        user = split_user("user")
        self.assertTrue(user == ("user", ""), user)
        
        user = split_user("user@email@realm")
        self.assertTrue(user == ("user@email", "realm"), user)
        
        user = split_user("realm\\user")
        self.assertTrue(user == ("user", "realm"), user)
        
    def test_09_get_user_from_param(self):
        user = get_user_from_param({"user": "cornelius"})
        self.assertTrue(user.realm == self.realm1, user)
        self.assertTrue(user.resolver == self.resolvername1, user)
        
        user = get_user_from_param({"realm": self.realm1})
        self.assertTrue(user.realm == self.realm1, user)
        self.assertTrue(user.login == "", user)
        self.assertTrue(user.resolver == "", user.resolver)
        
        user = get_user_from_param({"user": "cornelius",
                                    "resolver": self.resolvername1})
        self.assertTrue(user.realm == self.realm1, user)
        
        # create a realm, where cornelius is in two resolvers!
        rid = save_resolver({"resolver": self.resolvername3,
                               "type": "passwdresolver",
                               "fileName": PWFILE2})
        self.assertTrue(rid > 0, rid)
               
        (added, failed) = set_realm(self.realm2,
                                    [self.resolvername1,
                                     self.resolvername3])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 2)
        
        # get user cornelius, who is in two resolvers!
        # this problem raises an exception
        param = {"user": "cornelius",
                 "realm": self.realm2}
        self.assertRaises(Exception, get_user_from_param, param)
        
    def test_10_check_user_password(self):
        (added, failed) = set_realm("passwordrealm",
                                    [self.resolvername3])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)
        
        self.assertTrue(User(login="cornelius",
                             realm="passwordrealm").check_password("test"))
        self.assertFalse(User(login="cornelius",
                              realm="passwordrealm").check_password("wrong"))
        self.assertFalse(User(login="unknownuser",
                              realm="passwordrealm").check_password("wrong"))
        
        # test cornelius@realm2, since he is located in more than one
        # resolver.
        # TODO: We need to decide, what to do in this case.
        self.assertRaises(User(login="cornelius",
                               realm="realm2").check_password("test"))
        
    def test_11_get_search_fields(self):
        user = User(login="cornelius", realm=self.realm1)
        sF = user.get_search_fields()
        self.assertTrue(self.resolvername1 in sF, sF)
        resolver_sF = sF.get(self.resolvername1)
        self.assertTrue("username" in resolver_sF, resolver_sF)
        self.assertTrue("userid" in resolver_sF, resolver_sF)
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
