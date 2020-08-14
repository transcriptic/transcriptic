from copy import deepcopy
from io import StringIO
from operator import itemgetter
from requests.exceptions import ReadTimeout
import json
import requests
import warnings

try:
    import pandas as pd
except ImportError:
    raise ImportError(
        "Please run `pip install transcriptic[jupyter] if you "
        "would like to use Transcriptic objects."
    )


def _check_api(obj_type):
    from transcriptic import api

    if not api:
        raise RuntimeError(
            f"You have to be logged in to be able to create {obj_type} objects"
        )
    return api


class _BaseObject(object):
    """Base object which other objects inherit from"""

    # TODO: Inherit more stuff from here. Need to ensure web has unified fields for jupyter
    def __init__(self, obj_type, obj_id, attributes, connection=None):
        # If attributes and connection are explicitly provided, just return and not do any smart parsing
        if attributes and connection:
            self.connection = connection
            self.attributes = attributes
        else:
            if not connection:
                self.connection = _check_api(obj_type)
            else:
                self.connection = connection
            (self.id, self.name) = self.load_object(obj_type, obj_id)
            if not attributes:
                self.attributes = self.connection._get_object(self.id, obj_type)
            else:
                self.attributes = attributes

    def load_object(self, obj_type, obj_id):
        """Find and match object by name"""
        # TODO: Remove the try/except statement and properly handle cases where objects are not found
        # TODO: Fix `datasets` route since that only returns non-analysis objects
        try:
            objects = getattr(self.connection, obj_type + "s")()
        except:
            return (obj_id, str(obj_id))
        matched_objects = []
        for obj in objects:
            # Special case here since we use both 'name' and 'title' for object names
            if "name" in obj:
                if obj_id == obj["name"] or obj_id == obj["id"]:
                    matched_objects.append((obj["id"], obj["name"]))
            if "title" in obj:
                if obj_id == obj["title"] or obj_id == obj["id"]:
                    matched_objects.append((obj["id"], obj["title"]))
        if len(matched_objects) == 0:
            raise TypeError(f"{obj_id} is not found in your {obj_type}s.")
        elif len(matched_objects) == 1:
            return matched_objects[0]
        else:
            print(
                f"More than 1 match found. Defaulting to the first match: {matched_objects[0]}"
            )
            return matched_objects[0]


class Project(_BaseObject):
    """
    A Project object contains helper methods for managing your runs. You can view the runs associated with this project
    as well as submit runs to the project.

    Example Usage:

    .. code-block:: python

        myProject = Project("My Project")
        projectRuns = myProject.runs()
        myRunId = projectRuns.query("title == 'myRun'").id.item()
        myRun = Run(myRunId)

    Attributes
    ----------
    id : str
        Project id
    name: str
        Project name
    attributes: dict
        Master attributes dictionary
    connection: transcriptic.config.Connection
        Transcriptic Connection object associated with this specific object

    """

    def __init__(self, project_id, attributes=None, connection=None):
        """
        Initialize a Project by providing a project name/id. The attributes and connection parameters are generally
        not specified unless one wants to manually initialize the object.

        Parameters
        ----------
        project_id: str
            Project name or id in string form
        attributes: Optional[dict]
            Attributes of the project
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless explicitly provided
        """
        super(Project, self).__init__("project", project_id, attributes, connection)
        self._runs = pd.DataFrame()

    def runs(self, use_cache=True):
        """
        Get the list of runs belonging to the project

        Parameters
        ----------
        use_cache: Boolean
            Determines whether the cached list of runs is returned

        Returns
        -------
        DataFrame
            Returns a DataFrame of runs, with the id and title as columns
        """
        if self._runs.empty and use_cache:
            temp = self.connection.env_args
            self.connection.update_environment(project_id=self.id)
            project_runs = self.connection.runs()
            self._runs = pd.DataFrame([[pr["id"], pr["title"]] for pr in project_runs])
            self._runs.columns = ["id", "Name"]
            self.connection.env_args = temp
        return self._runs

    def submit(self, protocol, title, test_mode=False):
        """
        Submit a run to this project

        Parameters
        ----------
        protocol: dict
            Autoprotocol Protocol in dictionary form, can be generated using Protocol.as_dict()
        title: Optional[str]
            Title of run. Run-id will automatically be used as name if field is not provided
        test_mode: Optional[boolean]
            Determines if run will be submitted will be treated as a test run or a run that is meant for execution

        Returns
        -------
        Run
            Returns a run object if run is successfully submitted
        """
        response = self.connection.submit_run(
            protocol, project_id=self.id, title=title, test_mode=test_mode
        )
        return Run(response["id"], response)


class Run(_BaseObject):
    """
    A Run object contains helper methods for accessing Run-related information such as Instructions, Datasets
    and monitoring data

    Example Usage:

        .. code-block:: python

            myRun = Run('r12345')
            myRun.data
            myRun.instructions
            myRun.containers
            myRun.Instructions[0]

    Attributes
    ----------
    id : str
        Run id
    name: str
        Run name
    data: DataFrame
        DataFrame summary of all datasets which belong to this run
    instructions: DataFrame
        DataFrame summary of all Instruction objects which belong to this run
    containers: DataFrame
        DataFrame summary of all Container objects which belong to this run
    project_id : str
        Project id which run belongs to
    attributes: dict
        Master attributes dictionary
    connection: transcriptic.config.Connection
        Transcriptic Connection object associated with this specific object

    """

    def __init__(self, run_id, attributes=None, connection=None, timeout=30.0):
        """
        Initialize a Run by providing a run name/id. The attributes and connection parameters are generally
        not specified unless one wants to manually initialize the object.

        Parameters
        ----------
        run_id: str
            Run name or id in string form
        attributes: Optional[dict]
            Attributes of the run
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless explicitly provided
        timeout: Optional[float]
            Timeout in seconds (defaults to 30.0). This will be used when making API calls to fetch data associated with the run.
        """
        super(Run, self).__init__("run", run_id, attributes, connection)
        self.project_id = self.attributes["project"]["id"]
        self.timeout = timeout
        self._data_ids = pd.DataFrame()
        self._instructions = pd.DataFrame()
        self._containers = pd.DataFrame()
        self._data = pd.DataFrame()

    @property
    def data_ids(self):
        """
        Find and generate a list of datarefs and data_ids associated with this run.

        Returns
        -------
        DataFrame
            Returns a DataFrame of data ids, with datarefs and data_ids as columns

        """
        if self._data_ids.empty:
            datasets = []
            for dataset in self.attributes["datasets"]:
                inst_id = dataset["instruction_id"]
                if inst_id:
                    titles = [
                        inst.attributes["operation"]["dataref"]
                        for inst in self.instructions["Instructions"]
                        if inst.attributes["id"] == inst_id
                    ]
                    if len(titles) == 0:
                        title = "unknown"
                    elif len(titles) == 1:
                        title = titles[0]
                    else:
                        # This should never happen since instruction_ids are unique
                        raise ValueError("No unique instruction id found")
                else:
                    title = dataset["title"]
                datasets.append(
                    {
                        "Name": title,
                        "DataType": dataset["data_type"],
                        "Id": dataset["id"],
                    }
                )
            if len(datasets) > 0:
                data_ids = pd.DataFrame(datasets)
                self._data_ids = data_ids[["Name", "DataType", "Id"]]
        return self._data_ids

    @property
    def instructions(self):
        if self._instructions.empty:
            instruction_list = [
                Instruction(
                    dict(x, **{"project_id": self.project_id, "run_id": self.id}),
                    connection=self.connection,
                )
                for x in self.attributes["instructions"]
            ]
            self._instructions = pd.DataFrame(instruction_list)
            self._instructions.columns = ["Instructions"]
            self._instructions.insert(
                0, "Name", [inst.name for inst in self._instructions.Instructions]
            )
            self._instructions.insert(
                1, "Id", [inst.id for inst in self._instructions.Instructions]
            )
            self._instructions.insert(
                2,
                "Started",
                [inst.started_at for inst in self._instructions.Instructions],
            )
            self._instructions.insert(
                3,
                "Completed",
                [inst.completed_at for inst in self._instructions.Instructions],
            )
        return self._instructions

    @property
    def Instructions(self):
        """
        Helper for allowing direct access of `Instruction` objects

        Returns
        -------
        Series
            Returns a Series of `Instruction` objects

        """
        return self.instructions.Instructions

    @property
    def containers(self):
        if self._containers.empty:
            container_list = []
            for ref in Run(self.id).attributes["refs"]:
                container_list.append(Container(ref["container"]["id"]))
            self._containers = pd.DataFrame(container_list)
            self._containers.columns = ["Containers"]
            self._containers.insert(
                0, "Name", [container.name for container in self._containers.Containers]
            )
            self._containers.insert(
                1,
                "ContainerId",
                [container.id for container in self._containers.Containers],
            )
            self._containers.insert(
                2,
                "Type",
                [
                    container.container_type.shortname
                    for container in self._containers.Containers
                ],
            )
            self._containers.insert(
                3,
                "Status",
                [
                    container.attributes["status"]
                    for container in self._containers.Containers
                ],
            )
            self._containers.insert(
                4,
                "Storage Condition",
                [container.storage for container in self._containers.Containers],
            )
        return self._containers

    @property
    def Containers(self):
        """
        Helper for allowing direct access of `Container` objects

        Returns
        -------
        Series
            Returns a Series of `Container` objects
        """
        return self.containers.Containers

    @property
    def data(self):
        """
        Find and generate a list of Dataset objects which are associated with this run

        Returns
        -------
        DataFrame
            Returns a DataFrame of datasets, with Name, Dataset and DataType as columns

        """
        if self._data.empty:
            num_datasets = len(self.data_ids)
            if num_datasets == 0:
                print("No datasets were found.")
            else:
                print("Attempting to fetch %d datasets..." % num_datasets)
                try:
                    data_list = []
                    for name, data_type, data_id in self.data_ids.values:
                        dataset = Dataset(data_id)
                        data_list.append(
                            {
                                "Name": name,
                                "DataType": data_type,
                                "Operation": dataset.operation,
                                "AnalysisTool": dataset.analysis_tool,
                                "Datasets": dataset,
                            }
                        )
                    data_frame = pd.DataFrame(data_list)

                    # Rearrange columns
                    self._data = data_frame[
                        ["Name", "DataType", "Operation", "AnalysisTool", "Datasets"]
                    ]
                except ReadTimeout:
                    print(
                        "Operation timed out after %d seconds. Returning data_ids instead of Datasets.\nTo try again, increase value of self.timeout and resubmit request."
                        % self.timeout
                    )
                    return self.data_ids
        return self._data

    @property
    def Datasets(self):
        """
        Helper for allowing direct access of `Dataset` objects

        Returns
        -------
        Series
            Returns a Series of `Dataset` objects
        """
        try:
            return self.data.Datasets
        except Exception:
            print("Unable to load Datasets successfully. Returning empty series.")
            return pd.Series()

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
        style="height:450px" seamless></iframe>""" % self.connection.get_route(
            "view_run", project_id=self.project_id, run_id=self.id
        )


class Dataset(_BaseObject):
    """
    A Dataset object contains helper methods for accessing data related information

    Attributes
    ----------
    id : str
        Dataset id
    name: str
        Dataset name
    data : DataFrame
        DataFrame of well-indexed data values. Note that associated metadata is found in attributes dictionary
    data_objects : list(DataObject)
        List of DataObject type
    attachments : dict(str, bytes)
        names and data of all attachments for the dataset
    container: Container
        Container object that was used for this dataset
    operation: str
        Operation used for generating the dataset
    data_type: str
        Data type of this dataset
    attributes: dict
        Master attributes dictionary
    connection: transcriptic.config.Connection
        Transcriptic Connection object associated with this specific object

    """

    def __init__(self, data_id, attributes=None, connection=None):
        """
        Initialize a Dataset by providing a data name/id. The attributes and connection parameters are generally
        not specified unless one wants to manually initialize the object.

        Parameters
        ----------
        data_id: str
            Dataset name or id in string form
        attributes: Optional[dict]
            Attributes of the dataset
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless explicitly provided
        """
        super(Dataset, self).__init__("dataset", data_id, attributes, connection)
        # TODO: Get BaseObject to handle dataset name
        self.name = self.attributes["title"]
        self.id = data_id

        # TODO: Consider more formally distinguishing between dataset types
        try:
            self.operation = self.attributes["instruction"]["operation"]["op"]
        except KeyError:
            self.operation = None
        try:
            self.container = Container(
                self.attributes["container"]["id"],
                attributes=self.attributes["container"],
                connection=connection,
            )
        except KeyError as e:
            if "instruction" in self.attributes:
                warnings.warn(f"Missing key {e} when initializing dataset")
            self.container = None

        self.analysis_tool = self.attributes["analysis_tool"]
        self.analysis_tool_version = self.attributes["analysis_tool_version"]
        self.data_type = self.attributes["data_type"]
        self._raw_data = None
        self._data = pd.DataFrame()
        self._attachments = None
        self._data_objects = None

    @property
    def attachments(self):
        if not self._attachments:
            self._attachments = self.connection.attachments(data_id=self.id)
        return self._attachments

    @property
    def raw_data(self):
        if not self._raw_data:
            # Get all raw data
            self._raw_data = self.connection.dataset(data_id=self.id, key="*")
        return self._raw_data

    @property
    def data(self, key="*"):
        if self._data.empty:
            # Get all data initially (think about lazy loading in the future)
            try:
                self._data = pd.DataFrame(self.raw_data)
            except:
                raise RuntimeError(
                    "Failed to cast data as DataFrame. Try using raw_data property instead."
                )
            self._data.columns = [x.upper() for x in self._data.columns]
        if key == "*":
            return self._data
        else:
            return self._data[key]

    def data_objects(self):
        if not self._data_objects:
            self._data_objects = DataObject.init_from_dataset_id(self.id)
        return self._data_objects

    def cross_ref_aliquots(self):
        # Use the container.aliquots DataFrame as the base
        aliquot_data = deepcopy(self.container.aliquots)
        data_column = []
        indices_without_data = []
        # Print a warning if new column will overwrite existing column
        if "Aliquot Data" in aliquot_data.columns.values.tolist():
            warnings.warn(
                "Column 'Aliquot Data' will be overwritten with data pulled from Dataset."
            )
        # Look up data for every well index
        for index in aliquot_data.index:
            # Get humanized index
            humanized_index = self.container.container_type.humanize(int(index))
            if humanized_index in self.data:
                # Use humanized index to get data for that well
                data_point = self.data.loc[0, humanized_index]
            else:
                # If no data for that well, use None instead
                data_point = None
                indices_without_data.append(humanized_index)
            # Append data point to list
            data_column.append(data_point)
        # Print a list of well indices that do not have corresponding data keys
        if len(indices_without_data) > 0:
            warnings.warn(
                "The following indices were not found as data keys: %s"
                % ", ".join(indices_without_data)
            )
        # Add these data as a column to the DataFrame
        aliquot_data["Aliquot Data"] = data_column

        return aliquot_data

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
            style="height:400px; width:600px" seamless></iframe>""" % self.connection.get_route(
            "view_data", data_id=self.id
        )


class DataObject(object):
    """
    A DataObject holds a reference to the raw data, stored in S3, along with format and validation information

    Attributes
    ----------
    id : str
        DataObject id
    dataset_id : str
        Dataset id
    data : bytes
        Bytes fetched from the url
    name: str
        Dataset name
    content_type: str
        content type
    format: str
        format
    size: int
        size in bytes
    status: Enum("valid", "invalid", "unverified")
        valid vs invalid
    url: str
        download url which expires every 1hr.  Call `refresh` to renew
    validation_errors: list(str)
        validation errors
    container: Container
        Container object that was used for this data object
    attributes: dict
        Master attributes dictionary
    """

    def __init__(self, data_object_id=None):
        attributes = {}

        # Fetch dataobject from server if id supplied
        if data_object_id is not None:
            attributes = DataObject.fetch_attributes(data_object_id)

        self.__init_attrs(attributes)

        # cached values
        self._container = None
        self._data = None
        self._json = None

    def __init_attrs(self, attributes):
        self.attributes = attributes

        self.id = attributes.get("id")
        self.dataset_id = attributes.get("dataset_id")
        self.content_type = attributes.get("content_type")
        self.format = attributes.get("format")
        self.name = attributes.get("name")
        self.size = attributes.get("size")
        self.status = attributes.get("status")
        self.url = attributes.get("url")
        self.validation_errors = attributes.get("validation_errors")

    @staticmethod
    def fetch_attributes(data_object_id):
        connection = _check_api("data_objects")
        return connection.data_object(data_object_id)

    @staticmethod
    def init_from_attributes(attributes):
        data_object = DataObject()
        data_object.__init_attrs(attributes)

        return data_object

    @staticmethod
    def init_from_id(data_object_id):
        return DataObject(data_object_id)

    @staticmethod
    def init_from_dataset_id(data_object_id):
        connection = _check_api("data_objects")

        # array of attributes
        attributes_arr = connection.data_objects(data_object_id)

        return [DataObject.init_from_attributes(a) for a in attributes_arr]

    @property
    def container(self):
        container_id = self.attributes["container_id"]

        if container_id is None:
            return None

        if not self._container:
            self._container = Container(container_id)

        return self._container

    @property
    def data(self):
        if self._data:
            return self._data

        self._data = requests.get(self.url).content

        return self._data

    @property
    def data_str(self):
        return self.data.decode("utf-8")

    @property
    def json(self):
        if self._json:
            return self._json

        self._json = json.loads(self.data)

        return self._json

    def dataframe(self):
        """Creates a simple Pandas Dataframe"""
        if self.format == "csv" or self.content_type == "text/csv":
            return pd.read_csv(StringIO(self.data_str))
        else:
            return pd.DataFrame(self.json)

    def save_data(self, filepath, chunk_size=1024):
        """Save DataObject data to a file.  Useful for large files"""
        with open(filepath, "wb") as f:
            if self._data:
                f.write(self._data)
                return

            r = requests.get(self.url, stream=True)

            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

    def refresh(self):
        """Refresh DataObject as the url will expire after 1 hour"""
        clone = DataObject.init_from_id(self.id)
        self.__init_attrs(clone.attributes)


class Instruction(object):
    """
    An Instruction object contains information related to the current instruction such as the start,
    completed time as well as warps associated with the instruction.
    Note that Instruction objects are usually created as part of a run and not created explicity.

    Additionally, if diagnostic information is available, one can click on the `Show Diagnostics Data`
    button to view relevant diagnostic information.

    Example Usage:

        .. code-block:: python

            myRun = Run('r12345')
            myRun.instructions

            # Access instruction object
            myRun.Instructions[1]
            myRun.Instructions[1].warps


    Attributes
    ----------
    id : str
        Instruction id
    name: str
        Instruction name
    warps : DataFrame
        DataFrame of warps in the instruction
    started_at : str
        Time where instruction begun
    completed_at : str
        Time where instruction ended
    device_id: str
        Id of device which instruction was executed on
    attributes: dict
        Master attributes dictionary
    connection: transcriptic.config.Connection
        Transcriptic Connection object associated with this specific object
    """

    def __init__(self, attributes, connection=None):
        """
        Parameters
        ----------
        attributes : dict
            Instruction attributes
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless explicitly provided
        """
        self.connection = connection
        self.attributes = attributes
        self.id = attributes["id"]
        self.name = attributes["operation"]["op"]
        self.started_at = attributes["started_at"]
        self.completed_at = attributes["completed_at"]
        if len(attributes["warps"]) > 0:
            device_id_set = set(
                [warp["device_id"] for warp in self.attributes["warps"]]
            )
            self.device_id = device_id_set.pop()
            if len(device_id_set) > 1:
                warnings.warn(
                    "There is more than one device involved in this instruction. Please contact "
                    "Transcriptic for assistance."
                )

        else:
            self.device_id = None
        self._warps = pd.DataFrame()
        self._warp_events = pd.DataFrame()

    @property
    def warps(self):
        if self._warps.empty:
            warp_list = self.attributes["warps"]
            if len(warp_list) != 0:
                self._warps = pd.DataFrame(x["command"] for x in warp_list)
                self._warps.columns = [x.title() for x in self._warps.columns.tolist()]
                # Rearrange columns to start with `Name`
                if "Name" in self._warps.columns:
                    col_names = ["Name"] + [
                        col for col in self._warps.columns if col != "Name"
                    ]
                    self._warps = self._warps[col_names]
                self._warps.insert(1, "WarpId", [x["id"] for x in warp_list])
                self._warps.insert(
                    2, "Completed", [x["reported_completed_at"] for x in warp_list]
                )
                self._warps.insert(
                    3, "Started", [x["reported_started_at"] for x in warp_list]
                )
            else:
                warnings.warn(
                    "There are no warps associated with this instruction. Please contact "
                    "Transcriptic for assistance."
                )
        return self._warps

    @property
    def warp_events(self):
        """
        Warp events include discrete monitoring events such as liquid sensing
        events for a particular instruction.
        """
        # Note: We may consider adding special classes for specific warp
        # events, with more specific annotations/fields.
        if self._warp_events.empty:
            self._warp_events = self.monitoring(data_type="events")
        return self._warp_events

    def monitoring(self, data_type="pressure", grouping=None):
        """
        View monitoring data of a given instruction

        Parameters
        ----------
        data_type: Optional[str]
            Monitoring data type, defaults to 'pressure'
        grouping: Optional[str]
            Determines whether the values will be grouped, defaults to None. E.g. "5:ms"

        Returns
        -------
        DataFrame
            Returns a pandas dataframe of the monitoring data if present.
            Returns an empty dataframe if no data can be found due to errors.
        """
        response = self.connection.monitoring_data(
            instruction_id=self.id, data_type=data_type, grouping=grouping
        )
        # Handle errors by returning empty dataframe
        if "error" in response:
            warnings.warn(response["error"])
            return pd.DataFrame()
        res = pd.DataFrame(response["results"])
        # re-order so that "name" column is always leading
        if "name" in res.columns:
            rearr_cols = ["name"] + res.columns[res.columns != "name"].tolist()
            return res[rearr_cols]
        return res

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
            style="width:450px" seamless></iframe>""" % self.connection.get_route(
            "view_instruction",
            run_id=self.attributes["run_id"],
            project_id=self.attributes["project_id"],
            instruction_id=self.id,
        )


class Container(_BaseObject):
    """
    A Container object represents a container from the Transcriptic LIMS and
    contains relevant information on the container type as well as the
    aliquots present in the container.

    Example Usage:
        .. code-block:: python

          my_container = container("ct186apgz6a374")
          my_container.well_map
          my_container.aliquots

          my_container.container_type.col_count
          my_container.container_type.robotize("B1")
          my_container.container_type.humanize(12)

    Attributes
    ----------
    name: str
        Name of container
    well_map: dict
        Well mapping with well indices for keys and well names as values
    aliquots: DataFrame
        DataFrame of aliquots present in the container. DataFrame index
        now corresponds to the Well Index.
    container_type: autoprotocol.container_type.ContainerType
        Autoprotocol ContainerType object with many useful container type
        information and functions.
    cover: str
        Cover type of container
    storage: str
        Storage condition of container

        Example Usage:

        .. code-block:: python

          my_container = container("ct186apgz6a374")

          my_container.well_map

          my_container.container_type.col_count
          my_container.container_type.robotize("B1")
          my_container.container_type.humanize(12)


    """

    def __init__(self, container_id, attributes=None, connection=None):
        """
        Initialize a Container by providing a container name/id. The attributes and connection parameters are generally
        not specified unless one wants to manually initialize the object.

        Parameters
        ----------
        container_id: str
            Container name or id in string form
        attributes: Optional[dict]
            Attributes of the container
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless explicitly provided
        """
        super(Container, self).__init__(
            "container", container_id, attributes, connection
        )
        # TODO: Unify container "label" with name, add Containers route
        self.id = container_id
        self.cover = self.attributes["cover"]
        self.name = self.attributes["label"]
        self.storage = self.attributes["storage_condition"]
        self.well_map = {
            aliquot["well_idx"]: aliquot["name"]
            for aliquot in self.attributes["aliquots"]
        }
        self.container_type = self._parse_container_type()
        self._aliquots = pd.DataFrame()

    def _parse_container_type(self):
        """Helper function for parsing container string into container object"""

        container_type = self.attributes["container_type"]

        # Return the corresponding AP-Py container object for now. In the future, consider merging
        # the current and future dictionary when instantiating container_type
        try:
            from autoprotocol.container_type import _CONTAINER_TYPES

            return _CONTAINER_TYPES[container_type["shortname"]]
        except ImportError:
            warnings.warn(
                "Please install `autoprotocol-python` in order to get container types"
            )
            return None
        except KeyError:
            warnings.warn("ContainerType given is not supported yet in AP-Py")
            return None

    @property
    def aliquots(self):
        """
        Return a DataFrame of aliquots in the container, along with aliquot
        name, volume, and properties. Row index for the DataFrame corresponds
        to the well index of the aliquot.

        """
        if self._aliquots.empty:
            aliquot_list = self.attributes["aliquots"]
            try:
                from autoprotocol import Unit

                self._aliquots = pd.DataFrame(
                    sorted(
                        [
                            dict(
                                {
                                    "Well Index": x["well_idx"],
                                    "Name": x["name"],
                                    "Id": x["id"],
                                    "Volume": Unit(float(x["volume_ul"]), "microliter"),
                                },
                                **x["properties"],
                            )
                            for x in aliquot_list
                        ],
                        key=itemgetter("Well Index"),
                    )
                )
            except ImportError:
                warnings.warn(
                    "Volume is not cast into Unit-type. Please install `autoprotocol-python` in order to have automatic Unit casting"
                )
                self._aliquots = pd.DataFrame(
                    sorted(
                        [
                            dict(
                                {
                                    "Well Index": x["well_idx"],
                                    "Name": x["name"],
                                    "Id": x["id"],
                                    "Volume": float(x["volume_ul"]),
                                },
                                **x["properties"],
                            )
                            for x in aliquot_list
                        ],
                        key=itemgetter("Well Index"),
                    )
                )
            indices = self._aliquots.pop("Well Index")
            self._aliquots.set_index(indices, inplace=True)
        return self._aliquots

    def __repr__(self):
        """
        Return a string representation of a Container using the specified name.
        (ex. Container('my_plate'))

        """
        return "Container(%s)" % (str(self.name))
