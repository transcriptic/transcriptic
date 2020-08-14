from .config import Connection
from .version import __version__

api = None

"""
Transcriptic
============

The Transcriptic library is separated into three components:
1) Core. The core modules provide a barebones client for making calls to
the Transcriptic webapp to create and obtain data. This can be done via the
`api` object or via the command-line using the CLI.
2) Jupyter. This module provides a Jupyter-centric means for interacting with
objects returned from the Transcriptic webapp such as Run, Project and Dataset.
3) Analysis. This module provides some basic analysis wrappers around datasets
returned from the webapp using standard Python scientific libraries.

The __init__ file contains a bunch of entry functions to facilitate easy access
to the Jupyter library.
"""

""" Allow direct import of Jupyter objects such as `Run` directly if the
required imports are present
"""
try:
    from .jupyter import Run, Project, Container, Dataset
    from .commands import ProtocolPreview
except ImportError as e:
    pass


def run(run_id):
    """
    Creates a Run object for the specified run-id

    Parameters
    ----------
    run_id: str
        Id of Run, e.g. r123456789
    Returns
    ------
    Run object: Run
        Transcriptic representation of a Run object
    """
    from .jupyter import Run

    return Run(run_id)


def project(project_id):
    """
    Creates a Project object for the specified project-id

    Parameters
    ----------
    project_id: str
        Id of Project, e.g. p123456789
    Returns
    ------
    Project object: Project
        Transcriptic representation of a Project object
    """
    from .jupyter import Project

    return Project(project_id)


def container(container_id):
    """
    Creates a Container object for the specified container-id

    Parameters
    ----------
    container_id: str
        Id of Container, e.g. ct123456789
    Returns
    ------
    Container object: Container
        Transcriptic representation of a Container object
    """
    from .jupyter import Container

    return Container(container_id)


def preview(protocol):
    """
    Creates a protocol preview object for the specified protocol

    Parameters
    ----------
    protocol: dictionary
        protocol JSON in dictionary format
    Returns
    ------
    Protocol object: ProtocolPreview
        Transcriptic representation of a Protocol object
    """
    from .commands import ProtocolPreview

    return ProtocolPreview(protocol, api=api)


def analyze(protocol, test_mode=False):
    """
    Analyze a given protocol

    Parameters
    ----------
    protocol: dict
        Autoprotocol JSON in dictionary format
    test_mode: boolean
        whether protocol should be analyzed under test mode
    Returns
    ------
    Analysis result: dict
        Raw result of the analysis
    """
    return api.analyze_run(protocol, test_mode)


def submit(protocol, project_id, title=None, test_mode=False):
    """
    Submit a given protocol

    Parameters
    ----------
    protocol: dict
        Autoprotocol JSON in dictionary format
    project_id: str
        Project to submit Autoprotocol to
    title: str
        Name of Run
    test_mode: boolean
        whether protocol should be submitted as a test run
    Returns
    ------
    Submission result: dict
        Raw result of the submission
    """
    return api.submit_run(
        protocol, project_id=project_id, title=title, test_mode=test_mode
    )


def dataset(data_id, key="*"):
    """
    Get dataset for a given data_id

    Parameters
    ----------
    data_id
        Id of desired dataset, e.g. d123456789
    key
        Key of desired sub-fields of dataset

    Returns
    ------
    Data: dict
        Data in JSON form
    """
    return api.dataset(data_id=data_id, key=key)


def connect(transcriptic_path="~/.transcriptic"):
    """
    Instantiates a Connection based on the specified path, and overwrites the
    existing `api` object with this Connection

    Parameters
    ----------
    transcriptic_path:
     Path to transcriptic dot-file
    """
    # TODO: Mirror login code from CLI
    try:
        api = Connection.from_file(transcriptic_path)
    except (OSError, IOError):
        print(
            "Unable to find .transcriptic file, please ensure the right path"
            " is provided"
        )
