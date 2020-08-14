import json
import ast
import re
from collections import OrderedDict


PLURAL_UNITS = [
    "microliter",
    "nanoliter",
    "milliliter",
    "second",
    "minute",
    "hour",
    "g",
    "nanometer",
]

TEMP_DICT = {
    "cold_20": "-20 degrees celsius",
    "cold_80": "-80 degrees celsius",
    "warm_37": "37 degrees celsius",
    "cold_4": "4 degrees celsius",
    "warm_30": "30 degrees celsius",
    "ambient": "room temperature",
}


class AutoprotocolParser(object):
    def __init__(self, protocol_obj, api=None, parsed_output=None):
        self.api = api
        self.resource = dict()
        self.parse(protocol_obj)

    def parse(self, obj):
        self.object_list = []
        self.instructions = obj["instructions"]

        parsed_output = []
        for i in self.instructions:
            try:
                output = getattr(self, i["op"])(i)
                parsed_output.extend(output) if isinstance(
                    output, list
                ) else parsed_output.append(output)
            except AttributeError:
                parsed_output.append("[Unknown instruction]")

        self.parsed_output = parsed_output
        for i, p in enumerate(parsed_output):
            print("%d. %s" % (i + 1, p))

    def job_tree(self):
        """
        A Job Tree visualizes the instructions of a protocol in a hierarchical
        structure based on container dependency to help human readers with manual
        execution. Its construction utilizes the algorithm below, as well as the
        Node object class (to store relational information) at the bottom of this
        script.

        Example Usage:
            .. code-block:: python

                p = Protocol()

                bacterial_sample = p.ref("bacteria", None, "micro-1.5", discard=True)
                test_plate = p.ref("test_plate", None, "96-flat", storage="cold_4")

                p.dispense_full_plate(test_plate, "lb-broth-noAB", "50:microliter")
                w = 0
                amt = 1
                while amt < 20:
                    p.transfer(bacterial_sample.well(
                        0), test_plate.well(w), "%d:microliter" % amt)
                    amt += 2
                    w += 1

                pjsonString = json.dumps(p.as_dict(), indent=2)
                pjson = json.loads(pjsonString)
                parser_instance = english.AutoprotocolParser(pjson)
                parser_instance.job_tree()

                Output:
                1
                +---2
                3
                +---4
                5
                +---6
                7
                +---8
                9
                +---10
                11
                +---12


        Variables
        ---------
        steps: list
            deep list of objects per instruction/step;
            is primary information job tree is built from
        nodes: list
            list of node objects
        proto_forest: list
            list of lists grouped by connected nodes
        forest: list
            list of nested dictionaries, depicting parent-children relations
        forest_list: list
            list of nested lists, depticting parent-children relations
        """

        # 1. Enforce depth of 1 for steps
        def depth_one(steps):
            depth_one = []
            for step in steps:
                if type(step) is list:
                    if type(step[0]) is list:
                        depth_one.append(step[0])
                    else:
                        depth_one.append(step)
                else:
                    depth_one.append([step])
            return depth_one

        # 2. Convert steps to list of node objects (0,1,2,3...)
        def assign_nodes(steps):
            nodes = [i for i in range(len(steps))]
            objects = list(set([elem for sublist in steps for elem in sublist]))

            # checks for multiple src and dst objects -- added when looking for
            # mutiples
            split_objects = []
            for obj in objects:
                if len(obj) > 1:
                    new_objs = obj.split(", ")
                    split_objects.extend(new_objs)
                else:
                    split_objects.append(obj)
            objects = split_objects
            del split_objects

            # populate with leafless trees (Node objects, no edges)
            for node in nodes:
                nodes[node] = Node(str(node))

            # search for leafy trees
            for obj in objects:

                # accounts for multiple drc/dst objects
                leaves = []
                for i, sublist in enumerate(steps):
                    for string in sublist:
                        if string.count(",") > 0:
                            if obj in string:
                                leaves.append(i)
                        else:
                            if obj in sublist:
                                leaves.append(i)
                leaves = sorted(list(set(leaves)))

                if len(leaves) > 1:
                    viable_edges = []

                    # compute cross-product
                    for leaf1 in leaves:
                        for leaf2 in leaves:
                            if (
                                str(leaf1) != str(leaf2)
                                and sorted((leaf1, leaf2)) not in viable_edges
                            ):
                                viable_edges.append(sorted((leaf1, leaf2)))

                    # form edge networks
                    for edge in viable_edges:
                        n1, n2 = nodes[edge[0]], nodes[edge[1]]
                        n1.add_edge(n2)
                        n2.add_edge(n1)
                        nodes[int(n1.name)], nodes[int(n2.name)] = n1, n2
            return nodes

        # 3. Determine number of trees and regroup by connected nodes
        def connected_nodes(nodes):
            proto_trees = []
            nodes = set(nodes)

            while nodes:
                n = nodes.pop()
                group = {n}
                queue = [n]
                while queue:
                    n = queue.pop(0)
                    neighbors = n.edges
                    neighbors.difference_update(group)
                    nodes.difference_update(neighbors)
                    group.update(neighbors)
                    queue.extend(neighbors)
                proto_trees.append(group)
            return proto_trees

        # 4. Convert nodes to nested dictionary of parent-children relations
        # i.e. adding depth -- also deals with tree-node sorting and path
        # optimization
        def build_tree_dict(trees, steps):
            # node sorting in trees
            sorted_trees = []
            for tree in trees:
                sorted_trees.append(sorted(tree, key=lambda x: int(x.name)))

            # retrieve values of the nodes (the protocol's containers)
            # for each tree ... may want to use dictionary eventually
            all_values = []
            for tree in sorted_trees:
                values = [steps[int(node.name)] for node in tree]
                all_values.append(values)

            # create relational tuples:
            all_digs = []
            singles = []
            dst_potentials = []
            for tree_idx in range(len(sorted_trees)):
                edge_flag = False
                tree_digs = []
                for node_idx in range(len(sorted_trees[tree_idx])):

                    # digs: directed graph vectors
                    digs = []
                    dst_nodes = []
                    node_values = all_values[tree_idx][node_idx]
                    src_node = str(sorted_trees[tree_idx][node_idx].name)

                    # ACTION ON MULTIPLE OBJECTS (E.G. TRANSFER FROM SRC -> DST
                    # WELLS)
                    # Outcome space: {1-1, 1-many, many-1, many-many}
                    if len(node_values) == 2:
                        # single destination (x-1)
                        if node_values[1].count(",") == 0:
                            dst_nodes = [
                                i
                                for i, sublist in enumerate(steps)
                                if node_values[1] == sublist[0]
                            ]
                        # multiple destinations (x-many)
                        elif node_values[1].count(",") > 0:
                            dst_nodes = []
                            for dst in node_values[1].replace(", ", ""):
                                for i, sublist in enumerate(steps):
                                    if i not in dst_nodes and dst == sublist[0]:
                                        dst_nodes.append(i)

                    # ACTION ON A SINGLE OBJECT
                    elif len(node_values) == 1:
                        dst_nodes = [
                            i
                            for i, sublist in enumerate(steps)
                            if node_values[0] == sublist[0]
                        ]

                    # Constructing tuples in (child, parent) format
                    for dst_node in dst_nodes:
                        dig = (int(dst_node), int(src_node))
                        digs.append(dig)

                    # else: an edge-case for dictionaries constructed with no edges
                    # initiates tree separation via flag
                    if digs != []:
                        edge_flag = False
                        tree_digs.append(digs)
                    else:
                        edge_flag = True
                        digs = [(int(src_node), int(src_node))]
                        tree_digs.append(digs)

                # digraph cycle detection: avoids cycles by overlooking set
                # repeats
                true_tree_digs = []
                for digs in tree_digs:
                    for dig in digs:
                        if tuple(sorted(dig, reverse=True)) not in true_tree_digs:
                            true_tree_digs.append(tuple(sorted(dig, reverse=True)))

                # edge-case for dictionaries constructed with no edges
                if true_tree_digs != [] and edge_flag == False:
                    all_digs.append(true_tree_digs)
                elif edge_flag == True:
                    all_digs.extend(tree_digs)

            # Enforces forest ordering
            all_digs = sorted(all_digs, key=lambda x: x[0])

            # job tree traversal to find all paths:
            forest = []
            for digs_set in all_digs:

                # pass 1: initialize nodes dictionary
                nodes = OrderedDict()
                for tup in digs_set:
                    id, parent_id = tup
                    # ensure all nodes accounted for
                    nodes[id] = OrderedDict({"id": id})
                    nodes[parent_id] = OrderedDict({"id": parent_id})

                # pass 2: create trees and parent-child relations
                for tup in digs_set:
                    id, parent_id = tup
                    node = nodes[id]
                    # links node to its parent
                    if id != parent_id:
                        # add new_node as child to parent
                        parent = nodes[parent_id]
                        if not "children" in parent:
                            # ensure parent has a 'children' field
                            parent["children"] = []
                        children = parent["children"]
                        children.append(node)

                desired_tree_idx = sorted(list(nodes.keys()))[0]
                forest.append(nodes[desired_tree_idx])
            return forest

        # 5. Convert dictionary-stored nodes to unflattened, nested list of
        # parent-children relations
        def dict_to_list(forest):
            forest_list = []
            for tree in forest:
                tString = str(json.dumps(tree))
                tString = (
                    tString.replace('"id": ', "")
                    .replace('"children": ', "")
                    .replace("[{", "[")
                    .replace("}]", "]")
                    .replace("{", "[")
                    .replace("}", "]")
                )

                # find largest repeated branch (if applicable)
                # maybe think about using prefix trees or SIMD extensions for better
                # efficiency
                x, y, length, match = 0, 0, 0, ""
                for y in range(len(tString)):
                    for x in range(len(tString)):
                        substring = tString[y:x]
                        if (
                            len(list(re.finditer(re.escape(substring), tString))) > 1
                            and len(substring) > length
                        ):
                            match = substring
                            length = len(substring)

                # checking for legitimate branch repeat
                if "[" in match and "]" in match:
                    hits = []
                    index = 0
                    if len(tString) > 3:
                        while index < len(tString):
                            index = tString.find(str(match), index)
                            if index == -1:
                                break
                            hits.append(index)
                            index += len(match)

                    # find all locations of repeated branch and remove
                    if len(hits) > 1:
                        for start_loc in hits[1:]:
                            tString = tString[:start_loc] + tString[start_loc:].replace(
                                match, "]", 1
                            )

                # increment all numbers in string to match the protocol
                newString = ""
                numString = ""
                for el in tString:
                    if el.isdigit():  # build number
                        numString += el
                    else:
                        if (
                            numString != ""
                        ):  # convert it to int and reinstantaite numString
                            numString = str(int(numString) + 1)
                        newString += numString
                        newString += el
                        numString = ""
                tString = newString
                del newString

                forest_list.append(ast.literal_eval(tString))
            return forest_list

        # 6. Print job tree(s)
        def print_tree(lst, level=0):
            print("    " * (level - 1) + "+---" * (level > 0) + str(lst[0]))
            for l in lst[1:]:
                if type(l) is list:
                    print_tree(l, level + 1)
                else:
                    print("    " * level + "+---" + l)

        # 1
        steps = depth_one(self.object_list)
        # 2
        nodes = assign_nodes(steps)
        # 3
        proto_forest = connected_nodes(nodes)
        # 4
        forest = build_tree_dict(proto_forest, steps)
        # 5
        self.forest_list = dict_to_list(forest)
        # 6
        print("\n" + "A suggested Job Tree based on container dependency: \n")
        for tree_list in self.forest_list:
            print_tree(tree_list)

    def absorbance(self, opts):
        self.object_list.append([opts["object"]])
        return (
            f"Measure absorbance at {self.unit(opts['wavelength'])} for "
            f"{self.well_list(opts['wells'])} of plate {opts['object']}"
        )

    def acoustic_transfer(self, opts):
        transfers = []
        for t in opts["groups"][0]["transfer"]:
            transfers.append(
                f"Acoustic transfer {self.unit(t['volume'])} "
                f"from {t['from']} to {t['to']}"
            )
            self.object_list.append([t["from"], t["to"]])
        return transfers

    def autopick(self, opts):
        picks = []
        for i, g in enumerate(opts["groups"]):
            picks.extend(
                [
                    "Pick %s colonies from %s %s: %s to %s, %s"
                    % (
                        len(g["to"]),
                        len(g["from"]),
                        ("well" if len(g["from"]) is 1 else "wells"),
                        self.well_list(g["from"]),
                        self.well_list(g["to"]),
                        (
                            f"data saved at '{opts['dataref']}'"
                            if i is 0
                            else "analyzed with previous"
                        ),
                    )
                ]
            )
            self.object_list.append([g["from"], g["to"]])
        return picks

    def cover(self, opts):
        self.object_list.append([opts["object"]])
        return f"Cover {opts['object']} with a {opts['lid']} lid"

    def dispense(self, opts):
        self.object_list.append([opts["object"]])
        unique_vol = []
        for col in opts["columns"]:
            vol = self.unit(col["volume"])
            if vol not in unique_vol:
                unique_vol.append(vol)
        if "reagent" in opts:
            reagent = opts["reagent"]
        elif "resource_id" in opts:
            resource_id = opts["resource_id"]
            if resource_id in self.resource:
                reagent = self.resource[resource_id]
            elif self.api:
                resource = self.api.resources(resource_id)
                if resource["results"]:
                    reagent = resource["results"][0]["name"].lower()
                    self.resource[resource_id] = reagent
                else:
                    reagent = f"resource with resource ID {resource_id}"
            else:
                reagent = f"resource with resource ID {resource_id}"
        else:
            reagent = "unknown"

        if len(opts["columns"]) == 12 and len(unique_vol) == 1:
            return (
                f"Dispense {unique_vol[0]} of {reagent} to the full plate "
                f"of {opts['object']}"
            )
        else:
            return "Dispense corresponding amounts of %s to %d column(s) of %s" % (
                reagent,
                len(opts["columns"]),
                opts["object"],
            )

    def flash_freeze(self, opts):
        self.object_list.append([opts["object"]])
        return f"Flash freeze {opts['object']} for {self.unit(opts['duration'])}"

    def fluorescence(self, opts):
        self.object_list.append([opts["object"]])
        return (
            f"Read fluorescence of {self.well_list(opts['wells'])} of "
            f"plate {opts['object']} at excitation wavelength "
            f"{self.unit(opts['excitation'])} and emission wavelength "
            f"{self.unit(opts['emission'])}"
        )

    def gel_separate(self, opts):
        self.object_list.append([opts["matrix"]])
        return (
            f"Perform gel electrophoresis using a "
            f"{opts['matrix'].split(',')[1][:-1]} agarose gel for "
            f"{self.unit(opts['duration'])}"
        )

    def gel_purify(self, opts):
        self.object_list.append([opts["matrix"]])
        unique_bl = []
        for ext in opts["extract"]:
            bl = ext["band_size_range"]
            if bl not in unique_bl:
                unique_bl.append(bl)
        for i in range(len(unique_bl)):
            unique_bl[i] = (
                str(unique_bl[i]["min_bp"]) + "-" + str(unique_bl[i]["max_bp"])
            )

        if len(unique_bl) <= 3:
            return (
                f"Perform gel purification on the "
                f"{opts['matrix'].split(',')[1][:-1]} agarose gel with "
                f"band range(s) {', '.join(unique_bl)}"
            )
        else:
            return (
                f"Perform gel purification on the "
                f"{opts['matrix'].split(',')[1][:-1]} agarose gel with "
                f"{len(unique_bl)} band ranges"
            )

    def incubate(self, opts):
        self.object_list.append([opts["object"]])
        shaking = " (shaking)" if opts["shaking"] else ""
        return (
            f"Incubate {opts['object']} at "
            f"{TEMP_DICT[opts['where']]} for "
            f"{self.unit(opts['duration'])}{shaking}"
        )

    def image_plate(self, opts):
        self.object_list.append([opts["object"]])
        return f"Take an image of {opts['object']}"

    def luminescence(self, opts):
        self.object_list.append([opts["object"]])
        return (
            f"Read luminescence of {self.well_list(opts['wells'])} of "
            f"plate {opts['object']}"
        )

    def oligosynthesize(self, opts):
        self.object_list.append([o["destination"] for o in opts["oligos"]])
        return [
            f"Oligosynthesize sequence '{o['sequence']}' into " f"'{o['destination']}'"
            for o in opts["oligos"]
        ]

    def provision(self, opts):
        self.object_list.append([self.platename(t["well"]) for t in opts["to"]])
        resource_id = opts["resource_id"]
        if resource_id in self.resource:
            reagent = self.resource[resource_id]
        elif self.api:
            resource = self.api.resources(resource_id)
            if resource["results"]:
                reagent = resource["results"][0]["name"].lower()
                self.resource[resource_id] = reagent
            else:
                reagent = f"resource with resource ID {resource_id}"
        else:
            reagent = f"resource with resource ID {resource_id}"
        provisions = []
        for t in opts["to"]:
            provisions.append(
                f"Provision {self.unit(t['volume'])} of "
                f"{reagent} to well {self.well(t['well'])} of "
                f"container {self.platename(t['well'])}"
            )
        return provisions

    def sanger_sequence(self, opts):
        self.object_list.append([opts["object"]])
        seq = (
            f"Sanger sequence {self.well_list(opts['wells'])} of plate "
            f"{opts['object']}"
        )
        if opts["type"] == "standard":
            return seq
        elif opts["type"] == "rca":
            return seq + " with %s" % self.platename(opts["primer"])

    def illumina_sequence(self, opts):
        unique_wells = self.get_unique_wells(opts["lanes"])
        unique_plates = self.get_unique_plates(unique_wells)
        self.object_list.append(unique_plates)

        if len(unique_plates) == 1 and len(unique_wells) <= 3:
            seq = "Illumina sequence wells %s" % (", ".join(unique_wells))
        elif len(unique_plates) > 1 and len(unique_plates) <= 3:
            seq = "Illumina sequence the corresponding wells of plates %s" % ", ".join(
                unique_plates[0]
            )
        else:
            seq = "Illumina sequence the corresponding wells of %s plates" % len(
                unique_wells
            )

        return seq + f" with library size {opts['library_size']}"

    def flow_analyze(self, opts):
        wells = []
        for sample in opts["samples"]:
            if sample["well"] not in wells:
                wells.append(sample["well"])
        self.object_list.append([self.platename(w) for w in wells])

        return (
            "Perform flow cytometry on %s with the respective FSC and SSC channel parameters"
            % ", ".join(wells)
        )

    def seal(self, opts):
        self.object_list.append([opts["object"]])
        return f"Seal {opts['object']} ({opts['type']})"

    def spin(self, opts):
        self.object_list.append([opts["object"]])
        return (
            f"Spin {opts['object']} for {self.unit(opts['duration'])} at "
            f"{self.unit(opts['acceleration'])}"
        )

    def spread(self, opts):
        self.object_list.append([self.well(opts["from"]), self.well(opts["to"])])
        return [
            f"Spread {opts['volume']} of bacteria from well "
            f"{self.well(opts['from'])} of {self.platename(opts['from'])} "
            f"to well {self.well(opts['to'])} of agar plate "
            f"{self.platename(opts['to'])}"
        ]

    def stamp(self, opts):
        stamps = []
        for g in opts["groups"]:
            for pip in g:
                if pip == "transfer":
                    stamps.extend(
                        [
                            "Stamp %s from source origin %s "
                            "to destination origin %s %s (%s)"
                            % (
                                self.unit(p["volume"]),
                                p["from"],
                                p["to"],
                                (
                                    "with the same set of tips as previous"
                                    if (len(g[pip]) > 1 and i > 0)
                                    else ""
                                ),
                                (
                                    "%s rows x %s columns"
                                    % (g["shape"]["rows"], g["shape"]["columns"])
                                ),
                            )
                            for i, p in enumerate(g[pip])
                        ]
                    )
                    from_objs = str(
                        [self.platename(p["from"]) for i, p in enumerate(g[pip])]
                    )
                    to_objs = str(
                        [self.platename(p["to"]) for i, p in enumerate(g[pip])]
                    )
                    self.object_list.append([from_objs, to_objs])
        return stamps

    def thermocycle(self, opts):
        self.object_list.append([opts["object"]])
        return f"Thermocycle {opts['object']}"

    def pipette(self, opts):
        pipettes = []
        for g in opts["groups"]:
            for pip in g:
                if pip == "mix":
                    for m in g[pip]:
                        pipettes.append(
                            "Mix well %s of plate %s %d times "
                            "with a volume of %s"
                            % (
                                self.well(m["well"]),
                                self.platename(m["well"]),
                                m["repetitions"],
                                self.unit(m["volume"]),
                            )
                        )
                        self.object_list.append(self.platename(m["well"]))
                elif pip == "transfer":
                    pipettes.extend(
                        [
                            f"Transfer {self.unit(p['volume'])} from {p['from']} to {p['to']} {'with the same tip as previous' if len(g[pip]) > 1 and i > 0 else ''}"
                            for i, p in enumerate(g[pip])
                        ]
                    )

                    from_objs = str(
                        [self.platename(p["from"]) for i, p in enumerate(g[pip])]
                    )
                    to_objs = str(
                        [self.platename(p["to"]) for i, p in enumerate(g[pip])]
                    )
                    self.object_list.append([from_objs, to_objs])
                elif pip == "distribute":
                    pipettes.append(
                        f"Distribute from {g[pip]['from']} into "
                        f"{self.well_list([d['well'] for d in g[pip]['to']], 20)}"
                    )
                    self.object_list.append([g[pip]["from"], g[pip]["to"][0]["well"]])
                elif pip == "consolidate":
                    pipettes.append(
                        f"Consolidate "
                        f"{self.well_list([c['well'] for c in g[pip]['from']], 20)} "
                        f"into {g[pip]['to']}"
                    )
                    self.object_list.append([g[pip]["from"][0]["well"], g[pip]["to"]])
        return pipettes

    def magnetic_transfer(self, opts):
        specific_op = list(opts["groups"][0][0].keys())[0]
        specs_dict = opts["groups"][0][0][specific_op]
        self.object_list.append([specs_dict["object"]])
        seq = f"Magnetically {specific_op} {specs_dict['object']}"

        if specific_op == "dry":
            return seq + " for %s" % self.unit(specs_dict["duration"])
        elif specific_op == "incubate":
            return (
                seq + f" for {self.unit(specs_dict['duration'])} with a "
                f"tip position of {specs_dict['tip_position']}"
            )
        elif specific_op == "collect":
            return (
                seq + f" beads for {specs_dict['cycles']} cycles with a "
                f"pause duration of {self.unit(specs_dict['pause_duration'])}"
            )
        elif specific_op == "release" or "mix":
            return (
                seq + f" beads for {self.unit(specs_dict['duration'])} at "
                f"an amplitude of {specs_dict['amplitude']}"
            )

    def measure_volume(self, opts):
        unique_plates = self.get_unique_plates(opts["object"])
        self.object_list.append(unique_plates)

        if len(unique_plates) <= 3:
            return f"Measure volume of {len(opts['object'])} wells from {', '.join(unique_plates)}"
        else:
            return f"Measure volume of {len(opts['object'])} wells from the {len(unique_plates)} plates"

    def measure_mass(self, opts):
        unique_plates = self.get_unique_plates(opts["object"])
        self.object_list.append(unique_plates)
        return "Measure mass of %s" % ", ".join(opts["object"])

    def measure_concentration(self, opts):
        unique_plates = self.get_unique_plates(opts["object"])
        self.object_list.append(unique_plates)
        return (
            f"Measure concentration of {self.unit(opts['volume'])} "
            f"{opts['measurement']} source aliquots of {self.platename(opts['object'][0])}"
        )

    def uncover(self, opts):
        self.object_list.append([opts["object"]])
        return f"Uncover {opts['object']}"

    def unseal(self, opts):
        self.object_list.append([opts["object"]])
        return f"Unseal {opts['object']}"

    @staticmethod
    def platename(ref):
        return ref.split("/")[0]

    @staticmethod
    def well(ref):
        return ref.split("/")[1]

    @staticmethod
    def get_unique_wells(list_of_wells):
        unique_wells = []
        for well in list_of_wells:
            w = well["object"]
            if w not in unique_wells:
                unique_wells.append(w)
        return unique_wells

    @staticmethod
    def get_unique_plates(list_of_wells):
        unique_plates = []
        for well in list_of_wells:
            loc = well.find("/")
            if loc == -1:
                plate = well
            else:
                plate = well[:loc]

            if plate not in unique_plates:
                unique_plates.append(plate)
        return unique_plates

    @staticmethod
    def well_list(wells, max_len=10):
        well_list = "wells " + (", ").join(str(x) for x in wells)
        if len(wells) > max_len:
            well_list = str(len(wells)) + " wells"
        return well_list

    @staticmethod
    def unit(u):
        value = u.split(":")[0]
        unit = u.split(":")[1]
        return (
            f"{value} "
            f"{unit + 's' if float(value) > 1 and unit in PLURAL_UNITS else unit}"
        )


class Node(object):
    """
    A Node represents a Job Tree element that fulfils a broader child-parent
    relational structure. It contains relevant information on its relationships
    in the form of edges. The job_tree algorithm above then constructs the
    actual hierachy of the aforementioned relational structure.

    Example Usage:
        .. code-block:: python

        a = Node("a")
        b = Node("b")
        c = Node("c")
        d = Node("d")
        e = Node("e")
        f = Node("f")      structure:
        a.add_edge(b)          a
        a.add_edge(c)         / \
        b.add_edge(d)        b   c
        c.add_edge(e)       /   / \
        c.add_edge(f)      d   e   f

    Attributes
    ----------
    name: str
        Name the Node object
    edges: set
        Set of edges that each node owns
    """

    def __init__(self, name):
        self.__name = name
        self.__links = set()

    @property
    def name(self):
        return self.__name

    @property
    def edges(self):
        return set(self.__links)

    def add_edge(self, other):
        self.__links.add(other)
        other.__links.add(self)
