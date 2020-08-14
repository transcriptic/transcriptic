Contributing
============

Structure
---------

The Transcriptic Python Library (TxPy) is separated into two main
portions: the command line interface (CLI) and the Jupyter notebook
interface.

Both the CLI and the notebook interface uses the base ``Connection``
object for making relevant application programming interface (API) calls
to Transcriptic. The ``Connection`` object itself uses the ``routes``
module to figure out the relevant routes and passes that onto the
``api`` module for making these calls.

The base functionality of the CLI is handled by the ``cli`` module which
is the front-facing interface for users. The ``english`` module provides
autoprotocol parsing functionalities, and the ``util`` module provides
additional generic helper functions.

The base functionality of the notebook interface is exposed through the
``objects`` module. Additional analysis of these objects is provided
through the ``analysis`` module. In general, html representations should
be provided as much as possible.

For analysis purposes, we prefer using Pandas DataFrames and NumPy
arrays for representing and slicing data. For plotting, matplotlib and
plotly is preferred.

Version Compatibility
---------------------

TxPy is written with Python 3.6+ compatibility in mind. Python 2 is no
longer officialy supported.

General Setup
-------------

Use of virtual environment to isolate the development environment is
highly recommended. There are several tools available such as
`conda <https://docs.conda.io/projects/conda/en/latest/user-guide/install/>`__
and `pyenv <https://github.com/pyenv/pyenv#installation>`__.

After activating your desired virtualenv, install the dependencies using
the snippet below

::

   pip install -e '.[test, docs]'
   pre-commit install

Styling and Documentation
-------------------------

All code written should follow the `PEP8
standard <https://www.python.org/dev/peps/pep-0008/>`__

For documentation purposes, we follow `NumPy style doc
strings <https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt>`__

We use `pre-commit <https://pre-commit.com>`__ as our linting and
auto-formatting framework. Lint is checked with
`pylint <https://www.pylint.org>`__ and auto-formatting is done with
`black <https://black.readthedocs.io/en/stable/>`__. This is
automatically executed as part of the ``git commit`` and ``git push``
workflows. You may also execute it manually using the snippet below.

::

   pre-commit run

Testing
-------

For testing purposes, we write tests in the ``test`` folder in the
`pytest <http://pytest.org/latest/getting-started.html>`__ format. We
also use `tox <https://tox.readthedocs.org/en/latest/>`__ for automating
tests.

The ``tox`` command is run by Jenkins and is currently configured to run
the main module tests, generate a coverage report and build
documentation.

Generally, please ensure that all tests pass when you execute ``tox`` in
the root folder.

::

   cd $TXPY_ROOT_DIR
   tox

If you’re using `pyenv <https://github.com/pyenv/pyenv>`__ to manage
python versions, ensure you have all the tested environments in your
``.python-version`` file. i.e.\ ``pyenv local 3.5.6 3.6.8 3.7.3``

Running Specific Tests
~~~~~~~~~~~~~~~~~~~~~~

Specific tests are controlled by the ``tox.ini`` configuration file.

To run just the main module tests, execute ``python setup.py test`` in
the root folder. This is specified by the main ``[testenv]`` flag in
``tox.ini``.

To build the docs locally, execute
``sphinx-build -W -b html -d tmp/doctrees . -d tmp/html`` in the
``docs`` directory. This is specified by the ``[testenv:docs]`` flag in
``tox.ini``.

Pull Requests
-------------

To contribute, please submit a pull-request to the `Github
repository <http://github.com/strateos/transcriptic>`__.

Before submitting the request, please ensure that all tests pass by
running ``tox`` in the main directory.
