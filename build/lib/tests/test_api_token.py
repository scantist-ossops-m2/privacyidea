from .base import MyTestCase
import json
from privacyidea.lib.error import (TokenAdminError, ParameterError)
from privacyidea.lib.token import get_tokens, init_token
from privacyidea.lib.user import User
from urllib import urlencode

PWFILE = "tests/testdata/passwords"
IMPORTFILE = "tests/testdata/import.oath"
IMPORTFILE2 = "tests/testdata/empty.oath"
YUBICOFILE = "tests/testdata/yubico-oath.csv"
OTPKEY = "3132333435363738393031323334353637383930"
OTPKEY2 = "010fe88d31948c0c2e3258a4b0f7b11956a258ef"
OTPVALUES2 = ["551536", "703671", "316522", "413789"]


class APITokenTestCase(MyTestCase):

    def _create_temp_token(self, serial):
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"serial": serial,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

    def test_000_setup_realms(self):
        self.setUp_user_realms()

    def test_00_init_token(self):
        # hmac is now hotp.
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "hmac"},
                                           headers={'Authorization': self.at}):
            self.assertRaises(TokenAdminError, self.app.full_dispatch_request)

        # missing parameter otpkey
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "hotp"},
                                           headers={'Authorization': self.at}):
            self.assertRaises(ParameterError, self.app.full_dispatch_request)

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "hotp",
                                                 "otpkey": self.otpkey},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertTrue("value" in detail.get("googleurl"), detail)
            self.assertTrue("OATH" in detail.get("serial"), detail)

    def test_01_list_tokens(self):
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            tokenlist = result.get("value").get("tokens")
            count = result.get("value").get("count")
            next = result.get("value").get("next")
            prev = result.get("value").get("prev")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(len(tokenlist) == 1, tokenlist)
            self.assertTrue(count == 1, count)
            self.assertTrue(next is None, next)
            self.assertTrue(prev is None, prev)
            token0 = tokenlist[0]
            self.assertTrue(token0.get("username") == "", token0)
            self.assertTrue(token0.get("count") == 0, token0)
            self.assertTrue(token0.get("tokentype") == "hotp", token0)
            self.assertTrue(token0.get("tokentype") == "hotp", token0)
            self.assertTrue(token0.get("count_window") == 10, token0)
            self.assertTrue(token0.get("realms") == [], token0)
            self.assertTrue(token0.get("user_realm") == "", token0)

        # get assigned tokens
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({
                                               "assigned": True}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            tokenlist = result.get("value").get("tokens")
            # NO token assigned, yet
            self.assertTrue(len(tokenlist) == 0, "%s" % tokenlist)

        # get unassigned tokens
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({
                                               "assigned": False}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            tokenlist = result.get("value").get("tokens")
            self.assertTrue(len(tokenlist) == 1, len(tokenlist))

    def test_02_list_tokens_csv(self):
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({"outform":
                                                                       "csv"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue("info" in res.data, res.data)
            self.assertTrue("username" in res.data, res.data)
            self.assertTrue("user_realm" in res.data, res.data)

    def test_03_list_tokens_in_one_realm(self):
        for serial in ["S1", "S2", "S3", "S4"]:
             with self.app.test_request_context('/token/init',
                                                method='POST',
                                                data={"type": "hotp",
                                                      "otpkey": self.otpkey,
                                                      "serial": serial},
                                                headers={'Authorization':
                                                             self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)

        # tokens with realm
        for serial in ["R1", "R2"]:
            with self.app.test_request_context('/token/init', method='POST',
                                               data={"type": "hotp",
                                                     "otpkey": self.otpkey,
                                                     "serial": serial,
                                                     "realm": self.realm1},
                                               headers={'Authorization':
                                                            self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)

        # list tokens of realm1
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({
                                               "tokenrealm": self.realm1}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            tokenlist = result.get("value").get("tokens")
            count = result.get("value").get("count")
            next = result.get("value").get("next")
            prev = result.get("value").get("prev")
            self.assertTrue(len(tokenlist) == 2, res.data)
            self.assertTrue(count == 2, count)

    def test_04_assign_unassign_token(self):
        with self.app.test_request_context('/token/assign',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "serial": "S1",
                                                 "pin": "test"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") is True, result)

        # Assign the same token to another user will fail
        with self.app.test_request_context('/token/assign',
                                           method='POST',
                                           data={"user": "shadow",
                                                 "realm": self.realm1,
                                                 "serial": "S1"},
                                           headers={'Authorization': self.at}):
            self.assertRaises(TokenAdminError, self.app.full_dispatch_request)

        # Now unassign the token
        with self.app.test_request_context('/token/unassign',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") is True, result)

        # Assign the same token to another user will success
        with self.app.test_request_context('/token/assign',
                                           method='POST',
                                           data={"user": "shadow",
                                                 "realm": self.realm1,
                                                 "serial": "S1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") is True, result)

        # Unassign without any arguments will raise a ParameterError
        with self.app.test_request_context('/token/unassign',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            self.assertRaises(ParameterError, self.app.full_dispatch_request)

    def test_05_delete_token(self):
        self._create_temp_token("DToken")

        with self.app.test_request_context('/token/DToken',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

        # Try to remove token, that does not exist returns a value=0
        with self.app.test_request_context('/token/DToken',
                                           method='DELETE',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = json.loads(res.data).get("result")
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(result.get("value") == 0, result)

    def test_06_disable_enable_token(self):
        self._create_temp_token("EToken")

        # try to disable a token with no parameters
        with self.app.test_request_context('/token/disable',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            self.assertRaises(ParameterError, self.app.full_dispatch_request)

        # disable token
        with self.app.test_request_context('/token/disable/EToken',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

        # disable a disabled token will not count, so the value will be 0
        with self.app.test_request_context('/token/disable',
                                           method='POST',
                                           data={"serial": "EToken"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 0, result)

        # enable the token again
        with self.app.test_request_context('/token/enable/EToken',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

        # try to enable an already enabled token returns value=0
        with self.app.test_request_context('/token/enable',
                                           method='POST',
                                           data={"serial": "EToken"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 0, result)

    def test_07_reset_failcounter(self):
        serial = "RToken"
        self._create_temp_token(serial)

        # Set the failcounter to 12
        tokenobject_list = get_tokens(serial=serial)
        tokenobject_list[0].token.failcount = 12
        tokenobject_list[0].save()

        # reset the failcounter
        with self.app.test_request_context('/token/reset/RToken',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

        # test the failcount
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({"serial":
                                                                       serial}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(value.get("count") == 1, value)
            self.assertTrue(token.get("failcount") == 0, token)

        # reset failcount again, will again return value=1
        with self.app.test_request_context('/token/reset',
                                           method='POST',
                                           data={"serial": serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)


    def test_07_resync(self):

        with self.app.test_request_context('/token/init', method="POST",
                                           data={"serial": "Resync01",
                                                 "otpkey": self.otpkey},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

            """
                                             Truncated
               Count    Hexadecimal    Decimal        HOTP
               0        4c93cf18       1284755224     755224
               1        41397eea       1094287082     287082
               2         82fef30        137359152     359152
               3        66ef7655       1726969429     969429
               4        61c5938a       1640338314     338314
               5        33c083d4        868254676     254676
               6        7256c032       1918287922     287922
               7         4e5b397         82162583     162583
               8        2823443f        673399871     399871
               9        2679dc69        645520489     520489
            """

        # Resync does not work with NON-consecutive values
        with self.app.test_request_context('/token/resync/Resync01',
                                            method="POST",
                                            data={"otp1": 287082,
                                                  "otp2": 969429},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") is False, result)

        # Successful resync with consecutive values
        with self.app.test_request_context('/token/resync',
                                            method="POST",
                                            data={"serial": "Resync01",
                                                  "otp1": 359152,
                                                  "otp2": 969429},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") is True, result)

        # Get the OTP token an inspect the counter
        with self.app.test_request_context('/token/',
                                            method="GET",
                                            query_string=urlencode({"serial": "Resync01"}),
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(token.get("count") == 4, result)

    def test_08_setpin(self):
        self._create_temp_token("PToken")
        # Set one PIN of the token
        with self.app.test_request_context('/token/setpin',
                                            method="POST",
                                            data={"serial": "PToken",
                                                  "userpin": "test"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

        # Set both PINs of the token
        with self.app.test_request_context('/token/setpin/PToken',
                                            method="POST",
                                            data={"userpin": "test",
                                                  "sopin": "topsecret"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 2, result)

    def test_09_set_token_attributes(self):
        self._create_temp_token("SET001")
        # Set some things
        with self.app.test_request_context('/token/setpin',
                                            method="POST",
                                            data={"serial": "SET001",
                                                  "otppin": "test"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)


        # Set all other values
        with self.app.test_request_context('/token/set/SET001',
                                            method="POST",
                                            data={"count_auth_max": 17,
                                                  "count_auth_success_max": 8,
                                                  "hashlib": "sha2",
                                                  "count_window": 11,
                                                  "sync_window": 999,
                                                  "max_failcount": 15,
                                                  "description": "Some Token"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 7, result)

        # check the values
        with self.app.test_request_context('/token/',
                                           method="GET",
                                           query_string=urlencode(
                                                   {"serial": "SET001"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(value.get("count") == 1, result)

            self.assertTrue(token.get("count_window") == 11, token)
            self.assertTrue(token.get("sync_window") == 999, token)
            self.assertTrue(token.get("maxfail") == 15, token)
            self.assertTrue(token.get("description") == "Some Token", token)
            tokeninfo = token.get("info")
            self.assertTrue(tokeninfo.get("hashlib") == "sha2", tokeninfo)
            self.assertTrue(tokeninfo.get("count_auth_max") == "17",
                            tokeninfo)
            self.assertTrue(tokeninfo.get("count_auth_success_max") == "8",
                            tokeninfo)

    def test_10_set_token_realms(self):
        self._create_temp_token("REALM001")

        with self.app.test_request_context('/token/realm/REALM001',
                                            method="POST",
                                            data={"realms": "realm1, realm2"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        with self.app.test_request_context('/token/',
                                            method="GET",
                                            query_string=urlencode({"serial": "REALM001"}),
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(token.get("realms") == ["realm1"], token)

    def test_11_load_tokens(self):
        # Load OATH CSV
        with self.app.test_request_context('/token/load/import.oath',
                                            method="POST",
                                            data={"type": "oathcsv",
                                                  "file": (IMPORTFILE,
                                                           "import.oath")},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value == 3, result)

        # Load yubico.csv
        with self.app.test_request_context('/token/load/yubico.csv',
                                            method="POST",
                                            data={"type": "yubikeycsv",
                                                  "file": (YUBICOFILE,
                                                           "yubico.csv")},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value == 3, result)


        # Try to load empty file
        with self.app.test_request_context('/token/load/empty.oath',
                                            method="POST",
                                            data={"type": "oathcsv",
                                                  "file": (IMPORTFILE2,
                                                           "empty.oath")},
                                            headers={'Authorization': self.at}):
            self.assertRaises(ParameterError, self.app.full_dispatch_request)

        # Try to load unknown file type
        with self.app.test_request_context('/token/load/import.oath',
                                            method="POST",
                                            data={"type": "unknown",
                                                  "file": (IMPORTFILE,
                                                           "import.oath")},
                                            headers={'Authorization': self.at}):
            self.assertRaises(TokenAdminError, self.app.full_dispatch_request)

    def test_12_copy_token(self):
        self._create_temp_token("FROM001")
        self._create_temp_token("TO001")
        with self.app.test_request_context('/token/assign',
                                            method="POST",
                                            data={"serial": "FROM001",
                                                  "user": "cornelius",
                                                  "realm": self.realm1},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        with self.app.test_request_context('/token/setpin',
                                            method="POST",
                                            data={"serial": "FROM001",
                                                  "otppin": "test"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value == 1, result)

        # copy the PIN
        with self.app.test_request_context('/token/copypin',
                                            method="POST",
                                            data={"from": "FROM001",
                                                  "to": "TO001"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        # copy the user
        with self.app.test_request_context('/token/copyuser',
                                            method="POST",
                                            data={"from": "FROM001",
                                                  "to": "TO001"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        # check in the database
        tokenobject_list = get_tokens(serial="TO001")
        token = tokenobject_list[0]
        # check the user
        self.assertTrue(token.token.user_id == "1000", token.token)
        # check if the TO001 has a pin
        self.assertTrue(len(token.token.pin_hash) == 64,
                        len(token.token.pin_hash))

    def test_13_lost_token(self):
        self._create_temp_token("LOST001")

        # call lost token for a token, that is not assigned.
        # THis will create an exception
        with self.app.test_request_context('/token/lost/LOST001',
                                            method="POST",
                                            headers={'Authorization': self.at}):
            self.assertRaises(TokenAdminError, self.app.full_dispatch_request)

        # assign the token
        with self.app.test_request_context('/token/assign',
                                            method="POST",
                                            data={"serial": "LOST001",
                                                  "user": "cornelius",
                                                  "realm": self.realm1},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        with self.app.test_request_context('/token/lost/LOST001',
                                            method="POST",
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue("end_date" in value, value)
            self.assertTrue(value.get("serial") == "lostLOST001", value)

        # check if the user cornelius now owns the token lostLOST001
        tokenobject_list = get_tokens(user=User("cornelius",
                                                realm=self.realm1),
                                      serial="lostLOST001")
        self.assertTrue(len(tokenobject_list) == 1, tokenobject_list)

    def test_14_get_serial_by_otp(self):
        self._create_temp_token("T1")
        self._create_temp_token("T2")
        self._create_temp_token("T3")
        init_token({"serial": "GETSERIAL",
                    "otpkey": OTPKEY})


        # multiple tokens are matching!
        with self.app.test_request_context('/token/getserial/162583',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            self.assertRaises(TokenAdminError, self.app.full_dispatch_request)

        init_token({"serial": "GETSERIAL2",
                    "otpkey": OTPKEY2})

        with self.app.test_request_context('/token/getserial/316522',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertEqual(value.get("serial"), "GETSERIAL2")

        # If one OTP values was found, it can not be used again
        with self.app.test_request_context('/token/getserial/316522',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertEqual(value.get("serial"), None)


        # Will not find an assigned token
        with self.app.test_request_context('/token/getserial/413789'
                                           '?assigned=1',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertNotEqual(value.get("serial"), "GETSERIAL2")

        # Will find a substr
        with self.app.test_request_context('/token/getserial/413789'
                                           '?unassigned=1&string=SERIAL',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertEqual(value.get("serial"), "GETSERIAL2")
