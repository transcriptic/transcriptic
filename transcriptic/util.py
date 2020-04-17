import click
import itertools
import re
import sys

from collections import defaultdict

def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)


def flatmap(func, items):
    return itertools.chain.from_iterable(map(func, items))


def ascii_encode(non_compatible_string):
    """Primarily used for ensuring terminal display compatibility"""
    if non_compatible_string:
        return non_compatible_string.encode('ascii', errors='ignore').decode("ascii")
    else:
        return ""


def pull(nested_dict):
    if "type" in nested_dict and "inputs" not in nested_dict:
        return nested_dict
    else:
        inputs = {}
        if "type" in nested_dict and "inputs" in nested_dict:
            for param, input in list(nested_dict["inputs"].items()):
                inputs[str(param)] = pull(input)
            return inputs
        else:
            return nested_dict


def regex_manifest(protocol, input):
    """Special input types, gets updated as more input types are added"""
    if "type" in input and input["type"] == "choice":
        if "options" in input:
            pattern = '\[(.*?)\]'
            match = re.search(pattern, str(input["options"]))
            if not match:
                click.echo("Error in %s: input type \"choice\" options must "
                           "be in the form of: \n[\n  {\n  \"value\": "
                           "<choice value>, \n  \"label\": <choice label>\n  "
                           "},\n  ...\n]" % protocol['name'])
                raise RuntimeError
        else:
            click.echo("Must have options for 'choice' input type." +
                       " Error in: " + protocol["name"])
            raise RuntimeError


def iter_json(manifest):
    all_types = {}
    try:
        protocol = manifest['protocols']
    except TypeError:
        raise RuntimeError("Error: Your manifest.json file doesn't contain "
                           "valid JSON and cannot be formatted.")
    for protocol in manifest["protocols"]:
        types = {}
        for param, input in list(protocol["inputs"].items()):
            types[param] = pull(input)
            if isinstance(input, dict):
                if input["type"] == "group" or input["type"] == "group+":
                    for i, j in list(input.items()):
                        if isinstance(j, dict):
                            for k, l in list(j.items()):
                                regex_manifest(protocol, l)
                else:
                    regex_manifest(protocol, input)
        all_types[protocol["name"]] = types
    return all_types


def robotize(well_ref, well_count, col_count):
    """Function referenced from autoprotocol.container_type.robotize()"""
    if isinstance(well_ref, list):
        return [robotize(well, well_count, col_count) for well in well_ref]
    if not isinstance(well_ref, (str, int)):
        raise TypeError("ContainerType.robotize(): Well reference given "
                        "is not of type 'str' or 'int'.")

    well_ref = str(well_ref)
    m = re.match("([a-z])(\d+)$", well_ref, re.I)
    if m:
        row = ord(m.group(1).upper()) - ord('A')
        col = int(m.group(2)) - 1
        well_num = row * col_count + col
        # Check bounds
        if row > (well_count // col_count):
            raise ValueError("Row given exceeds "
                             "container dimensions.")
        if col > col_count or col < 0:
            raise ValueError("Col given exceeds "
                             "container dimensions.")
        if well_num > well_count:
            raise ValueError("Well given "
                             "exceeds container dimensions.")
        return well_num
    else:
        m = re.match("\d+$", well_ref)
        if m:
            well_num = int(m.group(0))
            # Check bounds
            if well_num > well_count or well_num < 0:
                raise ValueError("Well number "
                                 "given exceeds container dimensions.")
            return well_num
        else:
            raise ValueError("Well must be in "
                             "'A1' format or be an integer.")


def humanize(well_ref, well_count, col_count):
    """Function referenced from autoprotocol.container_type.humanize()"""
    if isinstance(well_ref, list):
        return [humanize(well, well_count, col_count) for well in well_ref]
    if isinstance(well_ref, str):
        try:
            well_ref = int(well_ref)
        except:
            raise ValueError("Well reference (%s) given has to be parseable into int." % well_ref)
    if not isinstance(well_ref, int):
        raise TypeError("Well reference (%s) given "
                        "is not of type 'int'." % well_ref)
    idx = robotize(well_ref, well_count, col_count)
    row, col = (idx // col_count, idx % col_count)
    # Check bounds
    if well_ref > well_count or well_ref < 0:
        raise ValueError("Well reference "
                         "given exceeds container dimensions.")
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[row] + str(col + 1)


def by_well(datasets, well):
    return [datasets[reading].props['data'][well][0] for
            reading in list(datasets.keys())]


def makedirs(name, mode=None, exist_ok=False):
    """Forward ports `exist_ok` flag for Py2 makedirs. Retains mode defaults"""
    from os import makedirs
    mode = mode if mode is not None else 0o777
    makedirs(name, mode, exist_ok)

class PreviewParameters:
    """
    A PreviewParameters object modifies web browser quick launch parameters and
    modifies them for application protocol testing and debugging.

    Attributes
    ------
    api : object
        the Connection object to provide session for using api endpoints

    quick_launch_params: dict
        web browser generated inputs for quick launch

    selected_samples: defaultdict
        all aliquots selected through the web quick launch manifest

    modified_params: dict
        the modified quick launch launch parameters, converts quick launch
        aliquot objects into strings for debugging

    refs: dict
        all unique refs seen in the quick launch parameters

    preview: dict
        the combination of refs and modified_params for scientific
        application debugging
    """
    def __init__(self, api, quick_launch_params):
        """
        Initialize TestParameter by providing a web generated params dict.

        Parameters
        ----------
        quick_launch_params: dict
            web browser generated inputs for quick launch
        """
        self.api = api
        self.container_cache = {}
        self.selected_samples = {}
        self.quick_launch_params = quick_launch_params
        self.preview = self.build_preview()

    def build_preview(self):
        """Builds preview parameters"""
        self.modified_params = self.modify_preview_parameters()
        self.refs = self.generate_refs()
        preview = defaultdict(lambda: defaultdict(dict))
        preview['preview']["parameters"].update(self.modified_params)
        preview['preview'].update(self.refs)
        return preview

    def modify_preview_parameters(self):
        """
        This method will traverse the quick launch 'raw_inputs' and modify
        container ids and aliquot dicts into a preview parameter container
        string for autoprotocol generation debugging.
        """
        return self.traverse(
            obj=self.quick_launch_params, callback=self.create_preview_string
        )

    def generate_refs(self):
        """
        This method takes the aggregated containers and aliquots to produce
        the refs aliquot values
        """
        ref_dict = defaultdict(lambda: defaultdict(dict))
        for cid, index_arr in self.selected_samples.items():
            container = self.container_cache.get(cid)
            cont_name = PreviewParameters.format_container_name(container)
            ref_dict['refs'][cont_name] = {
                'label': cont_name,
                'type': container.get('container_type').get('id'),
                'store': container.get('storage_condition'),
                'cover': container.get('cover', None),
                'properties': container.get('properties')
            }
            if None not in index_arr:
                ref_dict['refs'][cont_name]['aliquots'] = self.\
                    get_selected_aliquots(container, index_arr)
        return ref_dict

    def traverse(self, obj, callback=None):
        """
        Will traverse quick launch object and send value to a callback
        action method.
        """
        if isinstance(obj, dict):
            # If object has 'containerId' and 'wellIndex', then it is an aliquot
            if 'containerId' and 'wellIndex' in obj.keys():
                return self.create_string_from_aliquot(value=obj)
            else:
                value = {k: self.traverse(v, callback) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.traverse(elem, callback) for elem in obj]
        else:
            value = obj

        if callback is None:
            return value
        else:
            return callback(value)

    def add_to_cache(self, container_id):
        """Adds requested container to cache for later use"""
        if container_id in self.container_cache:
            container = self.container_cache[container_id]
        else:
            container = self.api.get_container(container_id)
            self.container_cache[container_id] = container
        return container

    def create_string_from_aliquot(self, value):
        """Creates preview aliquot representation"""
        well_idx = value.get("wellIndex")
        container_id = value.get("containerId")
        container = self.add_to_cache(container_id)
        cont_name = PreviewParameters.format_container_name(container)
        self.add_to_selected(container_id, well_idx)
        return '{}/{}'.format(cont_name, well_idx)

    def create_preview_string(self, value):
        """Creates preview parameters string representation"""
        if isinstance(value, str):
            if value[:2] == 'ct':
                container_id = value
                container = self.add_to_cache(container_id)
                cont_name = PreviewParameters.format_container_name(container)
                self.add_to_selected(container_id)
                return cont_name
            else:
                return value
        else:
            return value

    def add_to_selected(self, container_id, well_idx=None):
        """Saves which containers were selected."""
        if container_id in self.selected_samples:
            self.selected_samples[container_id].append(well_idx)
        else:
            self.selected_samples[container_id] = [well_idx]

    def get_selected_aliquots(self, container, index_arr):
        """Grabs the properties from the selected aliquots"""
        ref_aliquots = dict()
        container_aliquots = {
            ali.get('well_idx'): ali for ali in container.get('aliquots')
        }
        for i in index_arr:
            ali = container_aliquots.get(i, container)
            ref_aliquots[i] = {
                'name': ali.get('name'),
                'volume': '{}:microliter'.format(ali.get('volume_ul', 10)),
                'properties': ali.get('properties')
            }
        return ref_aliquots

    @classmethod
    def format_container_name(cls, container):
        return container.get('label').replace(' ', '_')