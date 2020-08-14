import json

import pytest
from Crypto.PublicKey import RSA
from click.testing import CliRunner
from transcriptic.cli import cli


@pytest.fixture(scope="session")
def temp_tx_dotfile(tmpdir_factory):
    path = tmpdir_factory.mktemp("config").join(".transcriptic")
    config = {
        "email": "somebody@transcriptic.com",
        "token": "foobarinvalid",
        "organization_id": "transcriptic",
        "api_root": "http://foo:5555",
        "analytics": True,
        "user_id": "ufoo2",
        "feature_groups": ["can_submit_autoprotocol", "can_upload_packages"],
    }
    with open(str(path), "w") as f:
        json.dump(config, f)
    return path


@pytest.fixture()
def temp_ssh_key(tmpdir_factory):
    dir_path = tmpdir_factory.mktemp("ssh")
    private_key_path = str(dir_path.join("private.pem"))
    public_key_path = str(dir_path.join("public.pem"))
    private_key = RSA.generate(2048)
    with open(private_key_path, "wb") as private_key_file:
        private_key_file.write(private_key.exportKey("PEM"))
    pubkey = private_key.publickey()
    with open(public_key_path, "wb") as public_key_file:
        public_key_file.write(pubkey.exportKey("OpenSSH"))
    yield private_key_path, public_key_path


@pytest.fixture
def cli_test_runner(temp_tx_dotfile):
    runner = CliRunner(env={"TRANSCRIPTIC_CONFIG": str(temp_tx_dotfile)})
    yield runner


def test_kebab_case(cli_test_runner):
    result = cli_test_runner.invoke(cli, ["--help"])
    command_str = result.output.split("Commands:\n")[1]
    commands = [x.strip() for x in command_str.split("\n") if x != ""]
    is_kebab = lambda x: x.islower() and ("_" not in x)
    assert all([is_kebab(cmd) for cmd in commands])


def test_login_nonexistent_key_path(cli_test_runner):
    result = cli_test_runner.invoke(
        cli,
        ["login", "--rsa-key", "/temp/path/invalid_key.pem"],
        input="\n".join(["email@foo.com", "barpw"]),
    )
    assert "Invalid value for '--rsa-key'" in result.output


def test_login_random_file_for_key(cli_test_runner, tmpdir_factory):
    path = tmpdir_factory.mktemp("foo").join("random-file")
    with open(str(path), "w") as fh:
        fh.write("this is not an rsa key")
    result = cli_test_runner.invoke(
        cli,
        ["login", "--rsa-key", str(path)],
        input="\n".join(["email@foo.com", "barpw"]),
    )
    assert (
        "Error loading RSA key: Could not parse the specified RSA Key, "
        "ensure it is a PRIVATE key in PEM format" in result.output
    )


def test_login_public_key(cli_test_runner, temp_ssh_key):
    (private_key_path, public_key_path) = temp_ssh_key
    result = cli_test_runner.invoke(
        cli,
        ["login", "--rsa-key", public_key_path],
        input="\n".join(["email@foo.com", "barpw"]),
    )
    assert "Error connecting to host: This is not a private key" in result.output
