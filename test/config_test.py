import json
import unittest
import tempfile
import re

import requests
from email.utils import formatdate

import transcriptic.config

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


class ConnectionInitTests(unittest.TestCase):
    def test_inits_valid(self):
        with tempfile.NamedTemporaryFile() as config_file:
            with open(config_file.name, "w") as f:
                json.dump(
                    {
                        "email": "somebody@transcriptic.com",
                        "token": "foobarinvalid",
                        "organization_id": "transcriptic",
                        "api_root": "http://foo:5555",
                        "analytics": True,
                        "user_id": "ufoo2",
                        "feature_groups": [
                            "can_submit_autoprotocol",
                            "can_upload_packages",
                        ],
                    },
                    f,
                )

            transcriptic.config.Connection.from_file(config_file.name)

    def test_inits_invalid(self):
        with tempfile.NamedTemporaryFile() as config_file:
            with open(config_file.name, "w") as f:
                json.dump(
                    {
                        "email": "somebody@transcriptic.com",
                        # "token": "foobarinvalid",  (missing token)
                        "organization_id": "transcriptic",
                        "api_root": "http://foo:5555",
                        "analytics": True,
                        "user_id": "ufoo2",
                        "feature_groups": [
                            "can_submit_autoprotocol",
                            "can_upload_packages",
                        ],
                    },
                    f,
                )

            # TODO(meawoppl) - assertRaisesRegexp deprecated in py3
            # Move it to assertRaisesRegex()
            with self.assertRaisesRegexp(OSError, "token"):
                transcriptic.config.Connection.from_file(config_file.name)

    def get_mocked_connection(self):
        # NOTE(meawoppl) - This could be the start of a testing pattern
        # for this module.
        class FakeReturn:
            status_code = 200

            def json(self):
                return {}

        session = transcriptic.config.initialize_default_session()
        session.put = Mock(return_value=FakeReturn())
        connection = transcriptic.config.Connection(
            email="foo@transcriptic.com",
            token="bar",
            organization_id="txid",
            api_root="https://fake.transcriptic.com",
            session=session,
        )
        return session, connection

    def test_aliquot_modify(self):
        session, connection = self.get_mocked_connection()

        aliquot_id = "23534245"
        props = {"prop1": "val1"}
        connection.modify_aliquot_properties(aliquot_id, props)
        session.put.assert_called_with(
            "https://fake.transcriptic.com/api/aliquots/23534245/modify_properties",
            json={"id": aliquot_id, "data": {"delete": [], "set": props}},
        )

    def test_signing(self):
        # Set up a connection with a key from a file
        with tempfile.NamedTemporaryFile() as config_file, tempfile.NamedTemporaryFile() as key_file:
            with open(key_file.name, "w") as kf:
                kf.write(
                    "-----BEGIN RSA PRIVATE KEY-----\nMIICXAIBAAKBgQDIK/IzSkBEuwKjYQo/ri4iKTTkr+FDtJetI7dYoz0//U5z7Vbu\nZQWncDNc38wMKidf2bWA+MTSWcYVUTlivp0y98MTLPsR6oJ9RwLggA2lFlCIjmdV\nUow/MmhWg0vX/SkThxS/F5I41GTrNIU3ZVZwGbmQ8hbyKCBYtbEHJWqATwIDAQAB\nAoGAHtYmSaB2ph/pGCIq4gSDNuACNfiiSzvW4eVOqWj8Vo8/NrypV7BYXqL6RqRz\nWqxjxHBVdbjdGUqbKU2J+ZxDuwCREsxQipjq+hM9aPpgjNJg4dz6yuc5mnUdOr9M\nR+zFjnnOJx98HGjuzLDXdBNYVSZFcDWj70Fjln/z5AjBYQECQQDijaHEcvDJOUmL\nDNyAYbjK811kFGpmglQBiZ257L47IP6jgqN544siHGnI7rykt+1upGfB2q8uQSIb\njNJKKsa3AkEA4jB9PXE8EooJ/eax2UsuwXt9LAgRabFurAJtadpAeeFBIIMSwBXU\n7APMfB3cQOnBlodnyrQ56mIOWPcSdN+7KQJAHr+4aBBtq/IRkETjnK0mxqz3TQEU\nW+tueXLzLGv8ecwFo620gHOoy61tki8M/ZJVMIIx7va+dhmzBmg7loNtywJAZUdy\n/K0USfTXToIaxoJcmDQUM0AVk+7n8EtR9KDOWASdpdIq9imQYnG9ASJZuhMxJJbS\nybfzatinNfzDneOEKQJBAMLOhHHbskUuuU9oDUl8sbrsreglQuoq1hvlB1uVskpi\nqMEIXSBwxAlxwmiAQLgS4hZY+cmQ3v5hCberMaZRPZ8=\n-----END RSA PRIVATE KEY-----\n"
                )
            with open(config_file.name, "w") as f:
                json.dump(
                    {
                        "email": "somebody@transcriptic.com",
                        "token": "foobarinvalid",
                        "organization_id": "transcriptic",
                        "api_root": "http://foo:5555",
                        "analytics": True,
                        "user_id": "ufoo2",
                        "feature_groups": [
                            "can_submit_autoprotocol",
                            "can_upload_packages",
                        ],
                        "rsa_key": key_file.name,
                    },
                    f,
                )

            connection = transcriptic.config.Connection.from_file(config_file.name)

        # Test that GET signature matches the above key (given a hardcoded date header)
        get_request = requests.Request(
            "GET",
            "http://foo:5555/get",
            headers={
                "Date": formatdate(timeval=1588628873, localtime=False, usegmt=True)
            },
        )
        prepared_get = connection.session.prepare_request(get_request)

        get_sig = prepared_get.headers["authorization"]
        self.assertEqual(
            re.search(r'keyId="(.+?)"', get_sig).group(1), "somebody@transcriptic.com"
        )
        self.assertEqual(
            re.search(r'algorithm="(.+?)"', get_sig).group(1), "rsa-sha256"
        )
        self.assertEqual(
            re.search(r'signature="(.+?)"', get_sig).group(1),
            "GfcAtyV0+CKDkxjsREXYAm6RP0WdIYaN5RamlNfIYZ7e847KAydQf2ylYIcsj9CS5BIOiBi5JBoC6n51NSbxU+kQcSv2nzSsq3rBpTFFMHUhTPdrfeHsH4IBvgMWZZHmHvyE7UXVqhLssVzMIm/oGTnprPMWiTcsKjEhe+DsQT4=",
        )
        self.assertEqual(
            set(re.search(r'headers="(.+?)"', get_sig).group(1).split(" ")),
            {"(request-target)", "date", "host"},
        )

        # Test that POST signature matches the above key (given a hardcoded body & date header)
        post_request = requests.Request(
            "POST",
            "http://foo:5555/get",
            data="Some body content",
            headers={
                "Date": formatdate(timeval=1588638873, localtime=False, usegmt=True)
            },
        )
        prepared_post = connection.session.prepare_request(post_request)

        post_sig = prepared_post.headers["authorization"]
        self.assertEqual(
            re.search(r'keyId="(.+?)"', post_sig).group(1), "somebody@transcriptic.com"
        )
        self.assertEqual(
            re.search(r'algorithm="(.+?)"', post_sig).group(1), "rsa-sha256"
        )
        self.assertEqual(
            re.search(r'signature="(.+?)"', post_sig).group(1),
            "TnixnCg4eT7nQhYQP1PNZHv5MVhHnWKf6MQb+cyS2tfw6++yuSaZS/4kz9nuvAbjZ1CsLWBKBDDIQWZqQXEjGUH/mXQ3KYDXhREyl0aDv2NgxKBcAsSooDa9nfA9zI7OeFa2dYzF81oOB4L4PDkbV3Bojw4mQYJf0eLW6FL1yTI=",
        )
        self.assertEqual(
            set(re.search(r'headers="(.+?)"', post_sig).group(1).split(" ")),
            {"(request-target)", "date", "host", "content-length", "digest"},
        )
