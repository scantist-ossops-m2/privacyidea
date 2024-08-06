"""
This test file tests the lib.tokens.sshkeytoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.sshkeytoken import SSHkeyTokenClass
from privacyidea.models import Token


class SSHTokenTestCase(MyTestCase):

    otppin = "topsecret"
    serial1 = "ser1"
    sshkey = "ssh-rsa " \
             "AAAAB3NzaC1yc2EAAAADAQABAAACAQDJy0rLoxqc8SsY8DVAFijMsQyCv" \
             "hBu4K40hdZOacXK4O6OgnacnSKN56MP6pzz2+4svzvDzwvkFsvf34pbsgD" \
             "F67PPSCsimmjEQjf0UfamBKh0cl181CbPYsph3UTBOCgHh3FFDXBduPK4DQz" \
             "EVQpmqe80h+lsvQ81qPYagbRW6fpd0uWn9H7a/qiLQZsiKLL07HGB+NwWue4os" \
             "0r9s4qxeG76K6QM7nZKyC0KRAz7CjAf+0X7YzCOu2pzyxVdj/T+KArFcMmq8V" \
             "dz24mhcFFXTzU3wveas1A9rwamYWB+Spuohh/OrK3wDsrryStKQv7yofgnPMs" \
             "TdaL7XxyQVPCmh2jVl5ro9BPIjTXsre9EUxZYFVr3EIECRDNWy3xEnUHk7Rzs" \
             "734Rp6XxGSzcSLSju8/MBzUVe35iXfXDRcqTcoA0700pIb1ANYrPUO8Up05v4" \
             "EjIyBeU61b4ilJ3PNcEVld6FHwP3Z7F068ef4DXEC/d7pibrp4Up61WYQIXV/" \
             "utDt3NDg/Zf3iqoYcJNM/zIZx2j1kQQwqtnbGqxJMrL6LtClmeWteR4420uZx" \
             "afLE9AtAL4nnMPuubC87L0wJ88un9teza/N02KJMHy01Yz3iJKt3Ou9eV6kqO" \
             "ei3kvLs5dXmriTHp6g9whtnN6/Liv9SzZPJTs8YfThi34Wccrw== " \
             "NetKnights GmbH"

    def test_01_create_token(self):
        db_token = Token(self.serial1, tokentype="sshkey")
        db_token.save()
        token = SSHkeyTokenClass(db_token)

        # An invalid key, raises an exception
        self.assertRaises(Exception, token.update, {"sshkey": "InvalidKey"})

        # Set valid key
        token.update({"sshkey": self.sshkey})
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "sshkey",
                        token.token.tokentype)
        self.assertTrue(token.type == "sshkey", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "SSHK", class_prefix)
        self.assertTrue(token.get_class_type() == "sshkey", token)

    def test_03_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = SSHkeyTokenClass(db_token)

        info = token.get_class_info()
        self.assertTrue(info.get("title") == "SSHkey Token",
                        "%s" % info.get("title"))

        info = token.get_class_info("title")
        self.assertTrue(info == "SSHkey Token", info)

    def test_04_get_sshkey(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = SSHkeyTokenClass(db_token)
        sshkey = token.get_sshkey()
        self.assertTrue(sshkey == self.sshkey, sshkey)
