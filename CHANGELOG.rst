Changelog
=========

Updated
~~~~~~~

-  Remove util.robotize/humanize and change callers to use autoprotocol directly

v8.0.0
------

Added
~~~~~

-  .readthedocs.yml configuration for docs building, corresponding badge
-  pre-commit framework and linting
-  auto-deploy functionality
-  Fish completions
-  Autoprotocol dependency for ``analysis`` package

Updated
~~~~~~~

-  Transitioned all .md files to .rst files
-  Doc dependencies, Sphinx to 2.4, releases to 1.6.3, sphinx-rtd-theme to 0.4.3
-  Test dependencies, pytest to 5.4, pylint to 2.5.2, tox to 3.15
-  Travis build reorganized to distinct jobs
-  Support for Python 3.8
-  Made adding autocomplete functionality more explicit
-  Base CLI test framework
-  Standardize on kebab-case for cli commands
-  Plotly dependency to 1.13
-  Matplotlib dependency to 3.0.3
-  Spectrophotometry plots now render offline
-  Dataset object html representation increased

Fixed
~~~~~

-  Kinetics.Spectrophotometry.plot() function now works again
-  Spectrophotometry.Absorbance/Fluorescence/Luminescence plot() works
   again

Removed
~~~~~~~

-  References to Phabricator
-  Support for Python 3.5

v7.1.0
------


Added
~~~~~

-  Add optional Run title to Launch command


Fixed
~~~~~

-  Removal of ``can_submit_autoprotocol`` feature group in the default
   ``.transcriptic``

v7.0.0
------


Added
~~~~~

-  zsh auto-completion support


Updated
~~~~~~~

-  Support only Python >=3.5, drop Python 2 support
-  Pin dependencies
-  Email references to point towards strateos

v6.0.0
------


Added
~~~~~

-  Added ``Connection.from_default_config()`` method and tests
-  Added ``Connection.modify_aliquot_properties()`` for aliquot property
   managment


Updated
~~~~~~~

-  Lint and docs, test cleanup
-  Starter work on testing ``Connection`` methods.
-  Updated dependencies to only support python 2.7 and python >=3.5

v5.6.0
------


Updated
~~~~~~~

-  run tox tests against python 3.5 instead of 3.4


Added
~~~~~

-  lint and build docs with tox
-  DataObject class which should help ease the transition from Datasets
   to DataObjects with regards to fetching data.


Fixed
~~~~~

-  doc and lint errors

v5.5.1
------


Fixed
~~~~~

-  Docstring building

v5.5.0
------


Added
~~~~~

-  ``attachments`` attribute on ``Dataset``


Fixed
~~~~~

-  Analyzed Dataset content-disposition

v5.4.1
------


Updated
~~~~~~~

-  Separated out the CLI logic into programatically callable functions.

v5.4.0
------


Added
~~~~~

-  Ability to filter by package id when using transcriptic launch

v5.3.10
-------


Updated
~~~~~~~

-  Made ``transcriptic analyze`` command visible to all

v5.3.9
------


Updated
~~~~~~~

-  Analyze handles missing pricing information.

v5.3.8
------


Updated
~~~~~~~

-  Jinja2 dependency made less strict

v5.3.7
------


Fixed
~~~~~

-  Fixed dataset and release uploading.

v5.3.6
------


Fixed
~~~~~

-  Fixed encoding bug with Python 3

v5.3.5
------


Fixed
~~~~~

-  Fixed backwards compatibility bug with using ``makedirs`` with Python
   2

v5.3.4
------


Updated
~~~~~~~

-  Added ``transcriptic generate_protocol <NAME>`` that generates a
   scaffold of a python protocol.

v5.3.3
------


Updated
~~~~~~~

-  ``transcriptic summarize`` now has an optional ``--html`` argument.
   When specified it will return a url to view the autoprotocol.

v5.3.2
------


Updated
~~~~~~~

-  ``transcriptic select_org`` now has an optional ``organization``
   argument. When specified, i.e. ``transcriptic select_org my_org``,
   it’ll skip the prompt and set the organization value to ``my_org``
   directly.

v5.3.1
------


Updated
~~~~~~~

-  ``transcriptic login`` now properly respects the ``--api-root``
   option and persists the result into the dotfile

v5.3.0
------


Updated
~~~~~~~

-  ``transcriptic launch --save_input`` now outputs the same type of
   JSON ### Added
-  ``test`` flag to ``transcriptic launch``, enabling the submission of
   test runs via the launch command

v5.2.0
------


Added
~~~~~

-  ``warp_events``, a new property of the ``Instruction`` object is
   added. This provides information on discrete monitoring events ###
   Updated
-  Instruction object now has an ``Id`` field ### Fixed
-  Fixed issue with broken direct imports of Jupyter objects
   (e.g. ``from transcriptic import Run``)

v5.1.0
------


Updated
~~~~~~~

-  Shifted non-core cli dependencies (i.e. those used in analysis) to
   the ``extras_require`` field
-  Shifted relative imports in base ``__init__`` file to make this
   possible
-  Shifted ``objects`` to a separate Jupyter module, but preserved
   existing relative imports path for backwards compatibility
-  Documentation updated to reflect the changes

v5.0.4
------


Fixed
~~~~~

-  Error with ``transcriptic launch --local`` when a file is provided

v5.0.3
------


Fixed
~~~~~

-  FileNotFound incompatibility error for Python2 (when ~/.transcriptic
   file isn’t specified)

v5.0.2
------


Fixed
~~~~~

-  Made cookie updates actually update headers

v5.0.1
------


Fixed
~~~~~

-  in ``Connection.upload_dataset()``, only convert io.StringIO instance
   to bytes, not StringIO.StringIO instance
-  Issue with ``upload-release``

v5.0.0
------


Added
~~~~~

-  Added concept of HiddenOption and email and token as input parameters
   ### Updated
-  Use ``Sessions`` object for maintaining persistent api connection
-  Reworked env_args and headers setting and getting to be clearer and
   more consistent
-  CLI now automatically fits flags in the order of: –flag, environment
   variable, .transcriptic
-  More formal support for cookie-based authentication ### Fixed
-  Improvements to the way non-unique projects are handled
-  Improved error handling for Py2 ### Removed
-  ``use_environ`` flag is now deprecated in ``Connection``. Please
   specify environment parameters directly
-  ``organization`` is now deprecated from ``Connection``. Please use
   ``organization_id`` instead

v4.3.0
------


Updated
~~~~~~~

-  Reworked the structure of ``run.data`` to be more verbose

v4.2.1
------


Added
~~~~~

-  ``transcriptic upload_dataset`` to CLI

v4.2.0
------


Added
~~~~~

-  ``upload_dataset`` to api object and surrounding infrastructure ###
   Updated
-  Dataset object is now initialized via a more stable route ### Fixed
-  Reworked ``run.data`` route based on changes to web response

v4.1.2
------


Fixed
~~~~~

-  Quick bugfix to ``run.data`` route due to breaking web change

v4.1.1
------


Fixed
~~~~~

-  Minor bug with default behavior with ``select_org`` prompt in
   ``select_org`` and ``login``

v4.1.0
------


Added
~~~~~

-  ``transcriptic payments`` to view payment methods and their
   corresponding ids
-  ``--payment`` flag to ``launch`` and ``submit`` to allow
   specification of payment methods ### Updated
-  ``transcriptic launch`` now presents and the price and asks for a
   confirmation before proceeding. ``--accept_quote`` flag is added
   which will override the confirmation

v4.0.1
------


Fixed
~~~~~

-  Remote behavior of ``transcriptic protocols``
-  Missing ``container`` key in Dataset initialization now returns a
   warning instead of an error

v4.0.0
------


Added
~~~~~

-  Conditional display of views based on enabled feature_flags ###
   Updated
-  Default behavior of ``protocols`` and ``launch`` to remote instead

v3.12.0
-------


Added
~~~~~

-  New –json flag for runs, projects and protocols for fetching JSON ###
   Fixed
-  Fixed bug in PlateRead that caused data overwrites if multiple
   instances of the same group_label were present

v3.11.0
-------


Updated
~~~~~~~

-  Handling of 403 routes
-  Documentation to reflect permissions changes
-  Minor rework of launch_request

v3.10.3
-------


Fixed
~~~~~

-  Bug with launch_request

v3.10.2
-------


Fixed
~~~~~

-  AP2EN_test failures still requiring protocol
-  object.py requirement for ``autoprotocol.container_types``

v3.10.1
-------


Fixed
~~~~~

-  Minor bugfix for ``_parse_protocol``

v3.10.0
-------


Updated
~~~~~~~

-  Removed setup.py requirement for ``autoprotocol-python``

v3.9.2
------


Fixed
~~~~~

-  Bugfix to resolve error caused by attempting to print unicode
   characters on the CLI.

v3.9.1
------


Fixed
~~~~~

-  Bugfix to remove ``data_keys`` from Absorbance function, which is no
   longer returned from webapp

v3.9.0
------


Added
~~~~~

-  Add raw_data property to the ``Dataset`` object
-  Add ability to cross reference aliquots with their data using the
   ``Dataset`` object

v3.8.0
------


Added
~~~~~

-  Ability to add ``--dye_test`` flag to ``transcriptic preview`` to
   convert a run into a water/dye test

v3.7.1
------


Fixed
~~~~~

-  Fixed minor bug in launching local protocols with
   ``transcriptic launch``

v3.7.0
------


Added
~~~~~

-  Ability to browse your inventory using the ``transcriptic inventory``
   command E.g. ``transcriptic inventory water``
-  Ability to launch protocols remotely using the ``--remote`` flag.
   E.g. ``transcriptic launch Pipetting --remote``
-  Ability to view available remote protocols for launching using
   ``transcriptic protocols --remote``
-  Ability for ``transcriptic summarize`` to retrieve resource strings
   with the ``--lookup`` flag


Fixed
~~~~~

-  resources route has been updated to match web return
-  Ap2En for dispense and provision
-  resources route now accepts resource IDs

v3.6.0
------


Added
~~~~~

-  Object helpers to allow more natural property access. E.g.
   ``myRun.instructions.Instructions`` = ``myRun.Instructions``


Updated
~~~~~~~

-  Misc formatting changes for HTML representation


Fixed
~~~~~

-  Underyling ``handle_response`` code to be more robust

v3.5.1
------


Added
~~~~~

-  Row index of the Container.aliquots DataFrame object now corresponds
   to the well index


Fixed
~~~~~

-  Stored volume in the Container.aliquots DataFrame as a Unit object
   instead of unicode

v3.5.0
------


Added
~~~~~

-  timeout property for Run objects
-  data_ids property for Run objects


Updated
~~~~~~~

-  data property for Run objects gives more informative errors when
   failing due to timeout
-  ``.monitoring`` method is now shifted to the Instruction object from
   the Run object
-  Optional parameters can now be handled by ``get_route`` ### Fixed
-  Existing route for monitoring data

v3.4.3
------


Fixed
~~~~~

-  Made local commands robust to lack of internet access

v3.4.2
------


Fixed
~~~~~

-  Broaden exception clause for general Python compatibility

v3.4.1
------


Added
~~~~~

-  Usage analytics support to CLI ### Updated
-  Minor documentation fixes

v3.4.0
------


Added
~~~~~

-  ``transcriptic select_org`` in CLI now allows you to switch
   organizations without re-authenticating
-  ``User-agent`` information to headers
-  ``Run.containers`` to return a list of containers used within the run

v3.3.1
------


Fixed
~~~~~

-  Updated ``transcriptic runs`` route to reflect reality

v3.3.0
------


Added
~~~~~

-  Ability for ``api.get_zip`` to handle larger zip-files by downloading
   to a local file
-  ``cover`` and ``storage`` attributes to Container object
-  Ability to construct and visualize a given protocol’s job tree using
   a flag on the CLI ### Updated
-  Updated english’s summarize to handle all currently-implemented
   instructions

v3.2.5
------


Fixed
~~~~~

-  Fixed initialization of Container object

v3.2.4
------


Added
~~~~~

-  Helper function ``flatmap`` into util ### Fixed
-  Fixed resources route in CLI. ``transcriptic resources 'query'`` now
   works

v3.2.3
------


Updated
~~~~~~~

-  Simplified ``Container._parse_container_type`` to use matching AP-Py
   container-type object whenever possible

v3.2.2
------


Added
~~~~~

-  additional documentation for ``Connection`` object ### Updated
-  update relevant documentation.rst files

v3.2.1
------


Updated
~~~~~~~

-  Updated “url” reference in run attributes to use “id” instead,
   in-line with a web update ### Fixed
-  Update docs/requirements.txt to be PEP440 compatible

v3.2.0
------


Updated
~~~~~~~

-  Reworked ``Instruction`` object
-  Reworked ``Run.instructions`` to return a Dataframe of
   ``Instruction`` objects
-  ``Aliquot`` object has been reworked into Container object as an
   ``aliquots`` property


Removed
~~~~~~~

-  ``Resource`` object has been removed from the library as its
   currently unused


Fixed
~~~~~

-  Change check for ImagePlate to be more generic
-  Setup now requires plotly 1.9.6 (for plotly offline/ipython
   compatibility reasons)

v3.1.0
------


Added
~~~~~

-  Tab completion for CLI (enabled by sourcing
   ``transcriptic_complete.sh``)
-  New API route for getting zipfiles: ``api.get_zip``
-  Made -h option synonymous with –help

v3.0.2
------


Updated
~~~~~~~

-  Setup now requires plotly 1.9.6 or greater

v3.0.1
------


Fixed
~~~~~

-  Better handling of Datasets with no ``well_map`` property in
   kinetics.spectrophotometry

v3.0.0
------


Added
~~~~~

-  New documentation for the new testing framework and how to write
   tests
-  Added Dockerfile for running Transcriptic containers. Compatible with
   CI tools (e.g. Jenkins) as well
-  New documentation added and hosted on
   http://transcriptic.readthedocs.io/en/latest/


Updated
~~~~~~~

-  Migrated the test framework from vanilla unittest2 to py.test
-  Rewrote documentation structure and added misc. documentation related
   changes
-  ``api`` module has been removed and merged into ``config`` module.
   The Connection object now handles all api calls.
-  All references to ``ctx`` has been renamed to ``api``


Fixed
~~~~~

-  Fixed bug in spectrophotometry handling attributes
-  Fixed compatibility issue with running ``transcriptic preview`` on
   python3

v2.3.1
------


Updated
~~~~~~~

-  Transcriptic CLI subcommands: compile, init, preview, summarize no
   longer require login


Fixed
~~~~~

-  ``transcriptic runs`` command now works in CLI

v2.3.0
------


Added
~~~~~

-  ``__version__`` variable for checking version. Enable version
   checking in CLI using ``transcriptic --version``
-  New Analysis module: Kinetics; ``Kinetics`` base object and
   ``Kinetics.Spectrophotometry`` for analyzing kinetics-based data such
   as growth curves
-  Expose additional properties of Dataset object: ``operation``,
   ``container``, ``data_type``

v2.2.1
------


Updated
~~~~~~~

-  Objects module has been heavily reworked and documentation added.
   This is especially true for Project, Run and Dataset objects


Fixed
~~~~~

-  Fixed package related CLI issues

v2.2.0
------


Added
~~~~~

-  ``api`` module for handling all calls including responses and
   exceptions
-  ``Connection`` object now mirrors most of the CLI functionality
-  basic test infrastructure and examples for testing API module


Updated
~~~~~~~

-  all separate requests, context or connection object calls are now
   consolidated and re-routed to go through the api and routes module


Removed
~~~~~~~

-  all direct api calls (get, put, push, pull) are removed from
   Connection. Users are encouraged to use the corresponding calls from
   the ``api`` module instead

v2.1.2
------


Fixed
~~~~~

-  Change in datasets route


Updated
~~~~~~~

-  Removed additional shadowed variable names

v2.1.1
------


Added
~~~~~

-  ``imaging`` module with ``ImagePlate`` as the first class for
   representing plate images. Focus is placed on IPython rendering
-  PIL dependency for image manipulation

v2.1.0
------


Updated
~~~~~~~

-  Major refactor of code to be in-line with PEP8
-  Removed unnecessary modules and renamed shadowed variables

v2.0.11
-------


Updated
~~~~~~~

-  Updated behavior of ``transcriptic login`` to be clearer and to
   return appropriate error messages


Fixed
~~~~~

-  print statement for launch

v2.0.10
-------


Added
~~~~~

-  pypi tags for setup.py such as ``classifiers`` and ``license``


Fixed
~~~~~

-  Updated Container object to automatically populate safe_min_volume_ul


Removed
~~~~~~~

-  Unused dependency: scikit-learn

v2.0.9
------


Added
~~~~~

-  Updated manifest json parsing to deserialize into an OrderedDict,
   preserving key order, which enables quick launch inputs to be ordered

v2.0.8
------


Added
~~~~~

-  ``launch`` command now supports –save_input option to save the
   protocol input as a local file


Fixed
~~~~~

-  ``launch`` command now properly supported either a project name or
   project id for the ``project`` option
-  typo AutoProtocol -> Autoprotocol

v2.0.7
------


Added
~~~~~

-  ``launch`` command to configure and run protocols without needing to
   package and upload them first

v2.0.6
------


Fixed
~~~~~

-  RMSE calculation in spectrophotometry.py now reports correct RMSE
-  transcriptic submit now correctly parses new autopick group
-  containter attributes are correctly requested from transcriptic via
   spectrophotometry.py

v2.0.5
------


Added
~~~~~

-  List runs in a specific project using the
   ``transcriptic runs <project_name_or_id`` command

v2.0.4
------


Added
~~~~~

-  Enabled ``analyze`` and ``submit`` to work for Protocol objects
-  Additional functionality to Container object: Use your favorite
   autoprotocol ContainerType functions
-  Additional properties of Container object exposed: Use wellMap to
   return a mapping of the well indices to aliquot names


Fixed
~~~~~

-  Set plot to default to use mpl=true (not all users have plotly
   credentials)

v2.0.3
------


Added
~~~~~

-  cost breakdown in ``analyze``
-  Python 3 compatibility
-  use ``transcriptic preview --view`` to return a URL that displays the
   instruction cards produced by the run you want to preview (this URL
   expires after two hours)
-  use the ‘transcriptic resources ’ CLI command to search the catalog
   for a resource’s vendor and ``id``
-  ``plotly`` and ``future`` are now required


Fixed
~~~~~

-  dataset helpers and embedding


Removed
~~~~~~~

-  ipython module

v2.0.2
------


Updated
~~~~~~~

-  Refactored analysis.spectrophotometry into ``Fluorescence``,
   ``Absorbance`` and ``Luminescence`` classes that inherit from
   ``PlateRead``


Added
~~~~~

-  More documentation and related configuration
-  Python 3 support
-  Added cost breakdown to analyze CLI


Fixed
~~~~~

-  bug with initializing runs with Project object

v2.0.1
------


Added
~~~~~

-  project url and description to setup.py
-  ``Aliquot``, ``Resource`` and ``Container`` object types
-  documentation setup and configuration


Updated
~~~~~~~

-  moved ``submit`` from ``cli`` to ``__init__``


Fixed
~~~~~

-  critical bug in ``submit``
-  bug in ``analyze``
-  bug in ``create_project``

v2.0.0
------


Updated
~~~~~~~

-  migrated content from
   `transcriptic/runner <https://github.com/transcriptic/runner>`__ to
   here, converted that code to a Python Client Library,
-  CLI functionality has not changed other than renaming some commands:

   -  ``release`` –> ``build-release``
   -  ``upload`` –> ``upload-release``
   -  ``new-project`` –> ``create-project``
   -  ``new-package`` –> ``create-package``
   -  ``run`` –> ``compile``
