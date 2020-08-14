from __future__ import print_function
import json
import os
import requests


def protocol_response(method, protocol_path=None, response_path=None, **kwargs):
    """
    Helper function for getting protocol response and dumping json to response path
    Caveat Emptor: Does not do any additional checks on the response object, just dumps to json if possible
    """
    from transcriptic import api

    if not api:
        from transcriptic.config import Connection

        api = Connection.from_file("~/.transcriptic")
    protocol = json.loads(open(protocol_path).read())

    response = requests.post(
        api.get_route(method),
        headers=api.session.headers,
        data=json.dumps({"protocol": protocol}),
    )
    with open(response_path, "w") as out_file:
        json.dump(response.json(), out_file, indent=2)


if __name__ == "__main__":
    # Using optparse, to support Python 2
    from optparse import OptionParser

    usage = "usage: %prog [options] method -i 'myProtocol.json'"
    parser = OptionParser(usage=usage)
    parser.add_option(
        "-i",
        "--input",
        action="store",
        type="str",
        dest="protocol_path",
        help="Path to protocol.json (required)",
        default=None,
    )
    parser.add_option(
        "-o",
        "--output",
        action="store",
        type="str",
        dest="response_path",
        help="output path for response json. If not specified, goes to protocol_response.json",
        default=None,
    )
    (options, args) = parser.parse_args()

    if len(args) != 1:
        raise RuntimeError("Please provide a method argument. Example: analyze_run")

    if not options.protocol_path:
        raise RuntimeError("The input path to the protocol is required")
    if not os.path.isfile(options.protocol_path):
        raise RuntimeError(f"{options.protocol_path} is an invalid protocol path")

    if not options.response_path:
        options.response_path = (
            options.protocol_path.split(".json")[0] + "_response.json"
        )
    try:
        protocol_response(args[0], options.protocol_path, options.response_path)
        print(f"File succesfully generated: {options.response_path}")
    except Exception as e:
        print(f"Ran into {e} when generating file.")
