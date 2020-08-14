import inspect
import io
import json
import os
import platform
import requests
import time
from Crypto.PublicKey import RSA
import transcriptic
import warnings
import zipfile

from . import routes
from .signing import StrateosSign
from .version import __version__

try:
    import magic
except ImportError:
    warnings.warn(
        "`python-magic` is recommended. You may be missing some system-level "
        "dependencies if you have already pip-installed it.\n"
        "Please refer to https://github.com/ahupp/python-magic#installation "
        "for more installation instructions."
    )


def initialize_default_session():
    """
    Initialize a default `requests.Session()` object which can be used for
    requests into the tx web api.
    """
    session = requests.Session()
    session.headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": f"txpy/{__version__} "
        f"({platform.python_implementation()}/"
        f"{platform.python_version()}; "
        f"{platform.system()}/{platform.release()}; "
        f"{platform.machine()}; {platform.architecture()[0]})",
    }
    return session


class Connection(object):
    """
    A Connection object is the object used for communicating with Transcriptic.

    Local usage: This is most easily instantiated by using the `from_file`
    function after calling `transcriptic login` from the command line.

    .. code-block:: shell
        :caption: shell

        $ transcriptic login
        Email: me@example.com
        Password:
        Logged in as me@example.com (example-lab)

    .. code-block:: python
        :caption: python

        from transcriptic.config import Connection
        api = Connection.from_file("~/.transcriptic")

    For those using Jupyter notebooks on secure.transcriptic.com (beta), a
    Connection object is automatically instantiated as api.

    .. code-block:: python
        :caption: python

        from transcriptic import api

    The `api` object can then be used for making any api calls. It is
    recommended to use the objects in `transcriptic.objects` since that wraps
    the response in a more friendly format.

    Example Usage:

    .. code-block:: python
        :caption: python

        api.projects()
        api.runs(project_id="p123456789")

    If you have multiple organizations and would like to switch to a specific
    organization, or if you would like to auto-load certain projects, you can
    set it directly by assigning to the corresponding variable.

    Example Usage:

    .. code-block:: python
        :caption: python

        api.organization_id = "my_other_org"
        api.project_id = "p123"

    """

    def __init__(
        self,
        email=None,
        token=None,
        organization_id=None,
        api_root="https://secure.transcriptic.com",
        cookie=None,
        verbose=False,
        analytics=True,
        user_id="default",
        feature_groups=[],
        rsa_key=None,
        session=None,
    ):
        # Initialize environment args used for computing routes
        self.env_args = dict()
        self.api_root = api_root
        self.organization_id = organization_id

        # Initialize session headers
        if session is None:
            session = initialize_default_session()
        self.session = session

        # Initialize RSA props
        self._rsa_key = None
        self._rsa_key_path = None
        self._rsa_secret = None
        # Set/Load rsa_key from arguement as string or Path
        self.rsa_key = rsa_key

        # NB: These many setattr calls update self.session.headers
        # cookie authentication is mutually exclusive from token authentication
        if cookie:
            if email is not None or token is not None:
                warnings.warn(
                    "Cookie and token authentication is mutually "
                    "exclusive. Ignoring email and token"
                )
            self.session.headers["X-User-Email"] = None
            self.session.headers["X-User-Token"] = None
            self.cookie = cookie
            self.update_session_auth(use_signature=False)
        else:
            if cookie is not None:
                warnings.warn(
                    "Cookie and token authentication is mutually "
                    "exclusive. Ignoring cookie"
                )
            self.session.headers["Cookie"] = None
            self.email = email
            self.token = token
            self.update_session_auth()

        # Initialize feature groups
        self.feature_groups = feature_groups

        # Initialize CLI parameters
        self.verbose = verbose
        self.analytics = analytics
        self.user_id = user_id

        transcriptic.api = self

    @staticmethod
    def from_file(path):
        """Loads connection from file"""
        config_path = os.path.expanduser(path)
        with open(config_path) as f:
            cfg = json.load(f)

        expected_keys = set(
            ("email", "token", "organization_id", "api_root", "analytics", "user_id")
        )
        keys = set(cfg.keys())

        if not keys.issuperset(expected_keys):
            raise OSError(
                f"Key(s) not found in configuration file ({config_path}) "
                f"Missing {repr(expected_keys - keys)}"
            )
        return Connection(**cfg)

    @staticmethod
    def from_default_config():
        """
        Load the default configuration file from the home directory of the
        current user and return a Connection instance that is costructed from it.
        """
        return Connection.from_file("~/.transcriptic")

    @property
    def api_root(self):
        try:
            return self.env_args["api_root"]
        except (NameError, KeyError):
            raise ValueError("api_root is not set.")

    @api_root.setter
    def api_root(self, value):
        self.update_environment(api_root=value)

    @property
    def organization_id(self):
        try:
            return self.env_args["org_id"]
        except (NameError, KeyError):
            raise ValueError("organization_id is not set.")

    @organization_id.setter
    def organization_id(self, value):
        self.update_environment(org_id=value)

    @property
    def project_id(self):
        try:
            return self.env_args["project_id"]
        except (NameError, KeyError):
            raise ValueError("project_id is not set.")

    @project_id.setter
    def project_id(self, value):
        self.update_environment(project_id=value)

    @property
    def email(self):
        try:
            return self.session.headers["X-User-Email"]
        except (NameError, KeyError):
            raise ValueError("email is not set.")

    @email.setter
    def email(self, value):
        if self.cookie is not None:
            warnings.warn(
                "Cookie and token authentication is mutually "
                "exclusive. Clearing cookie from headers"
            )
            self.update_headers(**{"Cookie": None})
        self.update_headers(**{"X-User-Email": value})
        self.update_session_auth()

    @property
    def token(self):
        try:
            return self.session.headers["X-User-Token"]
        except (NameError, KeyError):
            raise ValueError("token is not set.")

    @token.setter
    def token(self, value):
        if self.cookie is not None:
            warnings.warn(
                "Cookie and token authentication is mutually "
                "exclusive. Clearing cookie from headers"
            )
            self.update_headers(**{"Cookie": None})
        self.update_headers(**{"X-User-Token": value})

    @property
    def cookie(self):
        try:
            return self.session.headers["Cookie"]
        except (NameError, KeyError):
            return ValueError("cookie is not set.")

    @cookie.setter
    def cookie(self, value):
        if self.email is not None or self.token is not None:
            warnings.warn(
                "Cookie and token authentication is mutually "
                "exclusive. Clearing email and token from headers"
            )
            self.update_headers(**{"X-User-Email": None, "X-User-Token": None})
        self.update_headers(**{"Cookie": value})

    @property
    def rsa_key(self):
        return self._rsa_key

    @rsa_key.setter
    def rsa_key(self, value):
        self._rsa_key = value
        self.load_rsa_secret()

    def get_container(self, container_id):
        route = self.get_route('get_container',
                               org_id=self.organization_id,
                               container_id=container_id
                               )
        return self.get(route)

    def save(self, path):
        """Saves current connection into specified file, used for CLI"""
        with open(os.path.expanduser(path), "w") as f:
            f.write(
                json.dumps(
                    {
                        "email": self.email,
                        "token": self.token,
                        "organization_id": self.organization_id,
                        "api_root": self.api_root,
                        "analytics": self.analytics,
                        "user_id": self.user_id,
                        "feature_groups": self.feature_groups,
                        # We dont want to save a string key, only a path
                        "rsa_key": self._rsa_key_path,
                    },
                    indent=2,
                )
            )

    def load_rsa_secret(self):
        key_string_or_path = self._rsa_key

        if key_string_or_path is None:
            self._rsa_key_path = None
            self._rsa_secret = None
        else:
            try:  # First try loading it as a key
                key = RSA.import_key(key_string_or_path)
                self._rsa_key_path = None
                self._rsa_secret = key.export_key()

            except ValueError:  # Then try as a Path
                key_path = os.path.abspath(os.path.expanduser(key_string_or_path))
                with open(key_path, "rb") as key_file:
                    key = RSA.import_key(key_file.read())
                self._rsa_key_path = str(key_path)
                self._rsa_secret = key.export_key()

        self.update_session_auth()

    def update_session_auth(self, use_signature=True):
        if (
            use_signature
            and self._rsa_secret
            and "X-User-Email" in self.session.headers
        ):
            self.session.auth = StrateosSign(self.email, self._rsa_secret)
        else:
            self.session.auth = None

    def update_environment(self, **kwargs):
        """
        Updates environment variables used for computing routes.
        To remove an existing variable, set value to None.
        """
        self.env_args = dict(self.env_args, **kwargs)

    def update_headers(self, **kwargs):
        """
        Updates session headers
        To remove an existing variable, set value to None.
        """
        self.session.headers = dict(self.session.headers, **kwargs)

    def url(self, path):
        """url format helper"""
        if path.startswith("/"):
            return f"{self.api_root}{path}"
        else:
            return f"{self.api_root}/{self.organization_id}/{path}"

    def preview_protocol(self, protocol):
        """Post protocol preview"""
        route = self.get_route("preview_protocol")
        protocol = _parse_protocol(protocol)
        err_default = "Unable to preview protocol"
        return self.post(
            route,
            json={"protocol": protocol},
            allow_redirects=False,
            status_response={
                "200": lambda resp: resp.json()["key"],
                "default": lambda resp: RuntimeError(err_default),
            },
        )

    def organizations(self):
        """Get list of organizations"""
        route = self.get_route("get_organizations")
        return self.get(route)

    def get_organization(self, org_id=None):
        """Get particular organization"""
        route = self.get_route("get_organization", org_id=org_id)
        err_404 = f"There was an error fetching the organization {org_id}"
        resp = self.get(
            route,
            status_response={
                "200": lambda resp: resp,
                "404": lambda resp: RuntimeError(err_404),
                "default": lambda resp: resp,
            },
        )
        return resp

    def projects(self):
        """Get list of projects in organization"""
        route = self.get_route("get_projects")
        err_default = (
            "There was an error listing the projects in your "
            "organization.  Make sure your login details are correct."
        )
        return self.get(
            route,
            status_response={
                "200": lambda resp: resp.json()["projects"],
                "default": lambda resp: RuntimeError(err_default),
            },
        )

    def project(self, project_id=None):
        """Get particular project"""
        route = self.get_route("get_project", project_id=project_id)
        err_default = f"There was an error fetching project {project_id}"
        return self.get(
            route, status_response={"default": lambda resp: RuntimeError(err_default)}
        )

    def runs(self, project_id=None):
        """Get list of runs in project"""
        route = self.get_route("get_project_runs", project_id=project_id)
        err_default = (
            f"There was an error fetching the runs in project " f"{project_id}"
        )
        return self.get(
            route,
            status_response={
                "200": lambda resp: resp.json(),
                "default": lambda resp: RuntimeError(err_default),
            },
        )

    def create_project(self, title):
        """Create project with given title"""
        route = self.get_route("create_project")
        return self.post(route, data=json.dumps({"name": title}))

    def delete_project(self, project_id=None):
        """Delete project with given project_id"""
        route = self.get_route("delete_project", project_id=project_id)
        return self.delete(route, status_response={"200": lambda resp: True})

    def archive_project(self, project_id=None):
        """Archive project with given project_id"""
        route = self.get_route("archive_project", project_id=project_id)
        return self.put(
            route,
            data=json.dumps({"project": {"archived": True}}),
            status_response={"200": lambda resp: True},
        )

    def modify_aliquot_properties(
        self, aliquot_id, set_properties={}, delete_properties=[]
    ):
        """
        Modify the properties of an alquot:

        If specified set_properties must be dict mapping {str: str}
        these properties will be set on the aliquot specified.

        If specified delete_properties must be a list of string
        properties which will be deleted on the aliquot.
        """
        route = self.get_route("modify_aliquot_properties", aliquot_id=aliquot_id)
        return self.put(
            route,
            json={
                "id": aliquot_id,
                "data": {"set": set_properties, "delete": delete_properties},
            },
        )

    def packages(self):
        """Get list of packages in organization"""
        route = self.get_route("get_packages")
        return self.get(route)

    def package(self, package_id=None):
        """Get package with given package_id"""
        route = self.get_route("get_package", package_id=package_id)
        return self.get(route)

    def create_package(self, name, description):
        """Create package with given name and description"""
        route = self.get_route("create_package")
        return self.post(
            route,
            data=json.dumps(
                {
                    "name": "%s%s" % ("com.%s." % self.organization_id, name),
                    "description": description,
                }
            ),
        )

    def delete_package(self, package_id=None):
        """Delete package with given package_id"""
        route = self.get_route("delete_package", package_id=package_id)
        return self.delete(route, status_response={"200": lambda resp: True})

    def post_release(self, data, package_id=None):
        """Create release with given data and package_id"""
        route = self.get_route("post_release", package_id=package_id)
        return self.post(route, data=data)

    def get_release_status(self, package_id=None, release_id=None, timestamp=None):
        """Get status of current release upload"""
        route = self.get_route(
            "get_release_status",
            package_id=package_id,
            release_id=release_id,
            timestamp=timestamp,
        )
        return self.get(route)

    def get_quick_launch(self, project_id=None, quick_launch_id=None):
        """Get quick launch object"""
        route = self.get_route(
            "get_quick_launch", project_id=project_id, quick_launch_id=quick_launch_id
        )
        return self.get(route)

    def create_quick_launch(self, data, project_id=None):
        """Create quick launch object"""
        route = self.get_route("create_quick_launch", project_id=project_id)
        return self.post(route, data=data)

    def launch_protocol(self, params, protocol_id=None):
        """Launch protocol-id with params"""
        route = self.get_route("launch_protocol", protocol_id=protocol_id)
        return self.post(route, data=params)

    def get_launch_request(self, protocol_id=None, launch_request_id=None):
        """Get launch request id"""
        route = self.get_route(
            "get_launch_request",
            protocol_id=protocol_id,
            launch_request_id=launch_request_id,
        )
        return self.get(route)

    def resolve_quick_launch_inputs(
        self, raw_inputs, project_id=None, quick_launch_id=None
    ):
        """Resolves `raw_inputs` to `inputs` for quick_launch"""
        route = self.get_route(
            "resolve_quick_launch_inputs",
            project_id=project_id,
            quick_launch_id=quick_launch_id,
        )
        return self.post(route, json=raw_inputs)

    def get_protocols(self):
        """Get list of available protocols"""
        route = self.get_route("get_protocols")
        return self.get(route)

    def resources(self, query):
        """Get resources"""
        route = self.get_route("query_resources", query=query)
        return self.get(route)

    def inventory(self, query, timeout=30.0, page=0):
        """Get inventory"""
        route = self.get_route("query_inventory", query=query, page=page)
        return self.get(route, timeout=timeout)

    def kits(self, query):
        """Get kits"""
        route = self.get_route("query_kits", query=query)
        return self.get(route)

    def payment_methods(self):
        route = self.get_route("get_payment_methods")
        return self.get(route)

    def monitoring_data(
        self, data_type, instruction_id, grouping=None, start_time=None, end_time=None
    ):
        """Get monitoring_data"""
        route = self.get_route(
            "monitoring_data",
            data_type=data_type,
            instruction_id=instruction_id,
            grouping=grouping,
            start_time=start_time,
            end_time=end_time,
        )
        return self.get(route)

    def raw_image_data(self, data_id=None):
        """Get raw image data"""
        route = self.get_route("view_raw_image", data_id=data_id)
        return self.get(route, status_response={"200": lambda resp: resp}, stream=True)

    def _get_object(self, obj_id, obj_type=None):
        """Helper function for loading objects"""
        # TODO: Migrate away from deref routes for other object types
        if obj_type == "dataset":
            route = self.get_route("dataset_short", data_id=obj_id)
        else:
            route = self.get_route("deref_route", obj_id=obj_id)
        err_404 = f"[404] No object found for ID {obj_id}"
        return self.get(route, status_response={"404": lambda resp: Exception(err_404)})

    def analyze_run(self, protocol, test_mode=False):
        """Analyze given protocol"""
        protocol = _parse_protocol(protocol)
        if "errors" in protocol:
            raise AnalysisException(
                (
                    "Error%s in protocol:\n%s"
                    % (
                        ("s" if len(protocol["errors"]) > 1 else ""),
                        "".join(
                            ["- " + e["message"] + "\n" for e in protocol["errors"]]
                        ),
                    )
                )
            )

        def error_string(r):
            return AnalysisException(
                "Error%s in protocol:\n%s"
                % (
                    ("s" if len(r.json()["protocol"]) > 1 else ""),
                    "".join(["- " + e["message"] + "\n" for e in r.json()["protocol"]]),
                )
            )

        return self.post(
            self.get_route("analyze_run"),
            data=json.dumps({"protocol": protocol, "test_mode": test_mode}),
            status_response={"422": lambda resp: error_string(resp)},
        )

    def submit_run(
        self,
        protocol,
        project_id=None,
        title=None,
        test_mode=False,
        payment_method_id=None,
    ):
        """Submit given protocol"""
        protocol = _parse_protocol(protocol)
        payload = {
            "title": title,
            "protocol": protocol,
            "test_mode": test_mode,
            "payment_method_id": payment_method_id,
        }
        data = {k: v for k, v in payload.items() if v is not None}
        route = self.get_route("submit_run", project_id=project_id)
        err_404 = (
            f"Error: Couldn't create run (404).\n Are you sure the "
            f"project {self.url(project_id)} exists, and that you have "
            f"access to it?"
        )

        def err_422(resp):
            f"Error creating run: {resp.text}"

        return self.post(
            route,
            data=json.dumps(data),
            status_response={
                "404": lambda resp: AnalysisException(err_404),
                "422": lambda resp: AnalysisException(err_422),
            },
        )

    def analyze_launch_request(self, launch_request_id, test_mode=False):
        return self.post(
            self.get_route("analyze_launch_request"),
            data=json.dumps(
                {"launch_request_id": launch_request_id, "test_mode": test_mode}
            ),
        )

    def submit_launch_request(
        self,
        launch_request_id,
        project_id=None,
        protocol_id=None,
        title=None,
        test_mode=False,
        payment_method_id=None,
    ):
        """Submit specified launch request"""
        payload = {
            "title": title,
            "launch_request_id": launch_request_id,
            "protocol_id": protocol_id,
            "test_mode": test_mode,
            "payment_method_id": payment_method_id,
        }
        data = {k: v for k, v in payload.items() if v is not None}
        return self.post(
            self.get_route("submit_launch_request", project_id=project_id),
            data=json.dumps(data),
            status_response={
                "404": lambda resp: AnalysisException(
                    "Error: Couldn't create run (404). \n"
                    "Are you sure the project %s "
                    "exists, and that you have access to it?" % self.url(project_id)
                ),
                "422": lambda resp: AnalysisException(
                    f"Error creating run: {resp.text}"
                ),
            },
        )

    def dataset(self, data_id, key="*"):
        """Get dataset with given data_id"""
        route = self.get_route("dataset", data_id=data_id, key=key)
        return self.get(route)

    def _get_uploads_from_key(self, key):
        """Fetches uploads for a data upload key

        Parameters
        ----------
        key : str
            data upload key

        Returns
        -------
        requests.Response
        """
        return self.get(
            route=self.get_route(method="get_uploads", key=key),
            status_response={"200": lambda resp: resp},
            stream=True,
        )

    def attachments(self, data_id):
        """Fetches all attachments for a given dataset id

        Parameters
        ----------
        data_id : str
            dataset id

        Returns
        -------
        dict(str, bytes)
            a dict of attachment names and contents

        """
        dataset_route = self.get_route("dataset_short", data_id=data_id)
        dataset_attachments = self.get(dataset_route).get("attachments")
        attachment_names = [
            os.path.basename(_.get("name", "")) for _ in dataset_attachments
        ]
        attachment_contents = [
            self._get_uploads_from_key(_.get("key")).content
            for _ in dataset_attachments
        ]
        return dict(zip(attachment_names, attachment_contents))

    def datasets(self, project_id=None, run_id=None, timeout=30.0):
        """Get datasets belonging to run"""
        route = self.get_route("datasets", project_id=project_id, run_id=run_id)
        err_404 = (
            f"[404] No run found for ID {run_id}. Please ensure you "
            f"have the right permissions."
        )
        return self.get(
            route,
            status_response={"404": lambda resp: Exception(err_404)},
            timeout=timeout,
        )

    def data_object(self, id):
        """Fetches a data object by id

        Parameters
        ----------
        id: str
            data_object id

        Returns
        -------
        dict
            attributes dict
        """
        route = self.get_route("data_object", id=id)
        attributes = self.get(route).get("data").get("attributes")
        attributes["id"] = id

        return attributes

    def data_objects(self, dataset_id):
        """Fetches all data objects given a dataset id

        Parameters
        ----------
        dataset_id: str
            dataset id

        Returns
        -------
        arr[dict]
            array of attributes dict
        """
        route_base = self.get_route("data_objects", dataset_id=dataset_id)
        page = 0
        limit = 50
        has_more = True

        results = []

        while has_more:
            route = f"{route_base}&page[limit]={limit}&page[offset]=" f"{page * limit}"
            response = self.get(route)
            entities = response.get("data")

            for entity in entities:
                attributes = entity["attributes"]
                attributes["id"] = entity["id"]
                results.append(attributes)

            page += 1

            if len(entities) != limit:
                has_more = False

        return results

    def upload_dataset_from_filepath(
        self, file_path, title, run_id, analysis_tool, analysis_tool_version
    ):
        """
        Helper for uploading a file as a dataset to the specified run.

        Uses `upload_dataset`.

        .. code-block:: python

            api.upload_dataset_from_filepath(
                "my_file.txt",
                title="my cool dataset",
                run_id="r123",
                analysis_tool="cool script",
                analysis_tool_version="v1.0.0"
            )

        Parameters
        ----------
        file: str
            Path to file to be uploaded
        title: str
            Name of dataset
        run_id: str
            Run-id
        analysis_tool: str, optional
            Name of tool used for analysis
        analysis_tool_version: str, optional
            Version of tool used

        Returns
        -------
        response: dict
            JSON-formatted response
        """
        try:
            file_path = os.path.expanduser(file_path)
            file_handle = open(file_path, "rb")
            name = os.path.basename(file_handle.name)
        except (AttributeError, FileNotFoundError):
            raise ValueError("'file' has to be a valid filepath")

        try:
            content_type = magic.from_file(file_path, mime=True)
        except NameError:
            # Handle issues with magic import by not decoding content_type
            content_type = None
        return self.upload_dataset(
            file_handle,
            name,
            title,
            run_id,
            analysis_tool,
            analysis_tool_version,
            content_type,
        )

    def upload_dataset(
        self,
        file_handle,
        name,
        title,
        run_id,
        analysis_tool,
        analysis_tool_version,
        content_type=None,
    ):
        """
        Uploads a file_handle as a dataset to the specified run.

        .. code-block:: python

            # Uploading a data_frame via file_handle, using Py3
            import io

            temp_buffer = io.StringIO()
            my_df.to_csv(temp_buffer)

            api.upload_dataset(
                temp_buffer,
                name="my_df",
                title="my cool dataset",
                run_id="r123",
                analysis_tool="cool script",
                analysis_tool_version="v1.0.0"
            )

        Parameters
        ----------
        file_handle: file_handle
            File handle to be uploaded
        name: str
            Dataset filename
        title: str
            Name of dataset
        run_id: str
            Run-id
        analysis_tool: str, optional
            Name of tool used for analysis
        analysis_tool_version: str, optional
            Version of tool used
        content_type: str
            Type of content uploaded

        Returns
        -------
        response: dict
            JSON-formatted response
        """
        upload_id = self.upload_to_uri(file_handle, content_type, title, name)
        upload_datasets_route = self.get_route("upload_datasets")
        upload_resp = self.post(
            upload_datasets_route,
            json={
                "upload_id": upload_id,
                "file_name": name,
                "title": title,
                "run_id": run_id,
                "analysis_tool": analysis_tool,
                "analysis_tool_version": analysis_tool_version,
            },
            status_response={
                "404": lambda resp: "[404] Please double-check your parameters"
                " and ensure they are valid."
            },
        )

        return upload_resp

    def upload_to_uri(self, file_handle, content_type, title, name):
        """
        Helper for uploading files via the `upload` route

        Parameters
        ----------
        file_handle: file_handle
            File handle to be uploaded
        content_type: str
            Type of content uploaded
        title: str
            Title of content to be uploaded
        name: str
            Name of file to be uploaded

        Returns
        -------
        key: str
            s3 key
        """
        # NOTE(meawoppl) title argument is unused?

        # TODO:
        # Currently, we are passing `0` for file_size as it doesn't really
        # matter for non multipart uploads, though it would be better to
        # supply the correct value.
        data = {
            "attributes": {
                "file_name": name,
                "file_size": 0,
                "last_modified": int(time.time()),
                "is_multipart": False,
            }
        }

        uri_route = self.get_route("upload")
        uri_resp = self.post(uri_route, data=json.dumps({"data": data}))

        try:
            upload_id = uri_resp["data"]["id"]
            upload_uri = uri_resp["data"]["attributes"]["upload_url"]
        except KeyError:
            raise RuntimeError("Unexpected payload returned for upload_dataset")

        if isinstance(file_handle, io.StringIO):
            try:
                # io.StringIO instances must be converted to bytes
                file_handle = io.BytesIO(bytes(file_handle.getvalue(), "utf-8"))
            except AttributeError:
                raise ValueError("Unable to convert read buffer to bytes")

        headers = {
            "Content-Disposition": f"attachment; filename={name}",
            "Content-Type": content_type,
        }
        headers = {k: v for k, v in headers.items() if v}
        self.put(
            upload_uri,
            data=file_handle,
            headers=headers,
            status_response={"200": lambda resp: resp},
        )
        return upload_id

    def get_zip(self, data_id, file_path=None):
        """
        Get zip file with given data_id. Downloads to memory and returns a
        Python ZipFile by default.
        When dealing with larger files where it may not be desired to load the
        entire file into memory, specifying `file_path` will enable the file to
        be downloaded locally.

        Example Usage:

        .. code-block:: python

            small_zip_id = 'd12345'
            small_zip = api.get_zip(small_zip_id)

            my_big_zip_id = 'd99999'
            api.get_zip(my_big_zip_id, file_path='big_file.zip')

        Parameters
        ----------
        data_id: data_id
            Data id of file to download
        file_path: Optional[str]
            Path to file which to save the response to. If specified, will not
            return ZipFile explicitly.

        Returns
        ----------
        zip: zipfile.ZipFile
            A Python ZipFile is returned unless `file_path` is specified

        """
        route = self.get_route("get_data_zip", data_id=data_id)
        req = self.get(route, status_response={"200": lambda resp: resp}, stream=True)

        if file_path:
            with open(file_path, "wb") as f:
                # Buffer download of data into memory with smaller chunk sizes
                chunk_sz = 1024  # 1kb chunks
                for chunk in req.iter_content(chunk_sz):
                    if chunk:
                        f.write(chunk)
            print(f"Zip file downloaded locally to {file_path}.")
        else:
            return zipfile.ZipFile(io.BytesIO(req.content))

    def get_route(self, method, **kwargs):
        """
        Helper function to automatically match and supply required arguments
        """
        route_method = getattr(routes, method)
        route_method_args, _, _, route_defaults = inspect.getargspec(route_method)
        if route_defaults:
            route_method_args = route_method_args[: -len(route_defaults)]
        # Update loaded argument dict with new arguments which are not None
        new_args = {k: v for k, v in list(kwargs.items()) if v is not None}
        arg_dict = dict(self.env_args, **new_args)
        input_args = []
        for arg in route_method_args:
            if arg_dict[arg]:
                input_args.append(arg_dict[arg])
            else:
                raise Exception(
                    f"For route: {method}, argument {arg} needs " f"to be provided."
                )
        return route_method(  # pylint: disable=no-value-for-parameter
            *tuple(input_args)
        )

    def get(self, route, **kwargs):
        return self._call("get", route, **kwargs)

    def put(self, route, **kwargs):
        return self._call("put", route, **kwargs)

    def post(self, route, **kwargs):
        return self._call("post", route, **kwargs)

    def delete(self, route, **kwargs):
        return self._call("delete", route, **kwargs)

    def _req_call(self, method, route, **kwargs):
        return getattr(self.session, method)(route, **kwargs)

    def _call(self, method, route, status_response={}, **kwargs):
        """Base function for handling all requests"""
        if self.verbose:
            print(f"{method.upper()}: {route}")

        return self._handle_response(
            self._req_call(method, route, **kwargs), **status_response
        )

    def _handle_response(self, response, **kwargs):
        unauthorized_resp = (
            "You are not authorized to execute this command. "
            "For more information on access "
            "permissions see the package documentation."
        )
        internal_error_resp = (
            "An internal server error has occurred. "
            "Please contact support for assistance."
        )
        default_status_response = {
            "200": lambda resp: resp.json(),
            "201": lambda resp: resp.json(),
            "401": lambda resp: PermissionError(
                "[%d] %s" % (resp.status_code, unauthorized_resp)
            ),
            "403": lambda resp: PermissionError(
                "[%d] %s" % (resp.status_code, unauthorized_resp)
            ),
            "500": lambda resp: Exception(
                "[%d] %s" % (resp.status_code, internal_error_resp)
            ),
            "default": lambda resp: Exception(
                "[%d] %s" % (resp.status_code, resp.text)
            ),
        }
        status_response = dict(default_status_response, **kwargs)

        return_val = status_response.get(
            str(response.status_code), status_response["default"]
        )

        if isinstance(return_val(response), Exception):
            raise return_val(response)
        else:
            return return_val(response)

    # NOTE(meawoppl) This is only called externally
    def _post_analytics(self, client_id=None, event_action=None, event_category="cli"):
        route = "https://www.google-analytics.com/collect"
        if not client_id:
            client_id = self.user_id
        packet = (
            f"v=1&tid=UA-28937242-7&cid={client_id}&t=event&"
            f"ea={event_action}&ec={event_category}"
        )
        requests.post(route, packet)


class AnalysisException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


def _parse_protocol(protocol):
    if isinstance(protocol, dict):
        return protocol
    try:
        from autoprotocol import Protocol
    except ImportError:
        raise RuntimeError(
            "Please install `autoprotocol-python` in order "
            "to work with Protocol objects"
        )
    if isinstance(protocol, Protocol):
        return protocol.as_dict()
