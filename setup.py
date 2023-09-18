# SPDX-FileCopyrightText: (C) 2023 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
# SPDX-License-Identifier: CC0-1.0

from setuptools import setup

# The pyproject.toml format does not (yet) provide a way to install stand-alone
# scripts so we (mis)use the setup.py
setup(
    scripts=[
        "pi-manage",
        "tools/creategoogleauthenticator-file",
        "tools/getgooglecodes",
        "tools/privacyidea-authorizedkeys",
        "tools/privacyidea-convert-base32.py",
        "tools/privacyidea-convert-token",
        "tools/privacyidea-convert-xml-to-csv",
        "tools/privacyidea-create-ad-users",
        "tools/privacyidea-create-certificate",
        "tools/privacyidea-create-pwidresolver-user",
        "tools/privacyidea-create-sqlidresolver-user",
        "tools/privacyidea-create-userdb",
        "tools/privacyidea-cron",
        "tools/privacyidea-diag",
        "tools/privacyidea-expired-users",
        "tools/privacyidea-export-linotp-counter.py",
        "tools/privacyidea-export-privacyidea-counter.py",
        "tools/privacyidea-fetchssh",
        "tools/privacyidea-fix-access-rights",
        "tools/privacyidea-get-serial",
        "tools/privacyidea-get-unused-tokens",
        "tools/privacyidea-migrate-linotp.py",
        "tools/privacyidea-pip-update",
        "tools/privacyidea-queue-huey",
        "tools/privacyidea-schema-upgrade",
        "tools/privacyidea-standalone",
        "tools/privacyidea-sync-owncloud.py",
        "tools/privacyidea-token-janitor",
        "tools/privacyidea-update-counter.py",
        "tools/privacyidea-update-linotp-counter.py",
        "tools/privacyidea-user-action",
        "tools/privacyidea-usercache-cleanup",
        "tools/reset-privacyidea",
        "tools/ssha.py",
    ]
)
