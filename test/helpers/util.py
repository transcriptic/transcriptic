import json


def load_protocol(name=None, test_dir=None, path=None):
    if not test_dir:
        test_dir = "test/autoprotocol/"
    if not path:
        return json.loads(open(test_dir + name + ".json").read())
    else:
        return json.loads(open(path).read())
