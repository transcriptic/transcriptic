#!/usr/bin/env python3

import click
import json
import locale
import os
import time
import zipfile
import requests

from collections import OrderedDict
from contextlib import contextmanager
from jinja2 import Environment, PackageLoader
from os.path import isfile, expanduser, abspath
from transcriptic.english import AutoprotocolParser
from transcriptic.config import Connection
from transcriptic.signing import StrateosSign
from transcriptic.util import iter_json, flatmap, ascii_encode, makedirs
from transcriptic import routes

import sys


def submit(api, file, project, title=None, test=None, pm=None):
    """Submit your run to the project specified."""
    if pm is not None and not is_valid_payment_method(api, pm):
        print_stderr(
            "Payment method is invalid. Please specify a payment "
            "method from `transcriptic payments` or not specify the "
            "`--payment` flag to use the default payment method."
        )
        return
    project = get_project_id(api, project)
    if not project:
        return
    with click.open_file(file, "r") as f:
        try:
            protocol = json.loads(f.read())
        except ValueError:
            click.echo(
                "Error: Could not submit since your manifest.json "
                "file is improperly formatted."
            )
            return

    try:
        req_json = api.submit_run(
            protocol,
            project_id=project,
            title=title,
            test_mode=test,
            payment_method_id=pm,
        )
        run_id = req_json["id"]
        click.echo("Run created: %s" % api.url("%s/runs/%s" % (project, run_id)))
    except Exception as err:
        click.echo("\n" + str(err))


def release(api, name=None, package=None):
    deflated = zipfile.ZIP_DEFLATED
    if name:
        filename = f"release_{name}"
    else:
        filename = "release"
    if os.path.isfile(filename + ".zip"):
        new = click.prompt(
            f"You already have a release named {filename} in "
            f"this directory, make another one? [y/n]",
            default="y",
        )
        if new == "y":
            num_existing = sum([1 for x in os.listdir(".") if filename in x])
            filename = filename + "_" + str(num_existing)
        else:
            return
    click.echo("Compressing all files in this directory...")
    zf = zipfile.ZipFile(filename + ".zip", "w", deflated)
    for (path, dirs, files) in os.walk("."):
        for f in files:
            if ".zip" not in f:
                zf.write(os.path.join(path, f))
    zf.close()
    click.echo("Archive %s created." % (filename + ".zip"))
    if package:
        package_id = get_package_id(api, package) or get_package_name(api, package)
        upload_release(api, filename + ".zip", package_id)


def upload_release(api, archive, package):
    """Upload a release archive to a package."""
    try:
        package_id = get_package_id(api, package.lower()) or get_package_name(
            api, package.lower()
        )
        package_name = get_package_name(api, package_id.lower()) or get_package_id(
            api, package_id.lower()
        )
        click.echo(f"Uploading {archive} to {package_name}")
    except AttributeError:
        click.echo("Error: Invalid package id or name.")
        return

    with click.progressbar(
        None,
        100,
        "Upload Progress",
        show_eta=False,
        width=70,
        fill_char="|",
        empty_char="-",
    ) as bar:
        bar.update(40)
        file = open(os.path.basename(archive), "rb")
        upload_id = api.upload_to_uri(
            file, "application/zip, application/octet-stream", archive, archive
        )
        bar.update(20)
        try:
            up = api.post_release(
                data=json.dumps({"release": {"upload_id": upload_id}}),
                package_id=package_id,
            )
            re = up["id"]
        except (ValueError, PermissionError) as err:
            if type(err) == ValueError:
                click.echo(
                    "\nError: There was a problem uploading your release."
                    "\nVerify that your manifest.json file is properly  "
                    "formatted and that all previews in your manifest "
                    "produce valid Autoprotocol by using the "
                    "`transcriptic preview` and/or `transcriptic analyze` "
                    "commands."
                )
            elif type(err) == PermissionError:
                click.echo("\n" + str(err))
            return

        bar.update(20)
        time.sleep(10)
        status = api.get_release_status(
            package_id=package_id, release_id=re, timestamp=int(time.time())
        )
        errors = status["validation_errors"]
        bar.update(30)
        if errors:
            click.echo(
                "\nPackage upload to %s unsuccessful. "
                "The following error(s) was returned: \n%s"
                % (
                    get_package_name(api, package_id),
                    ("\n").join(e.get("message", "[Unknown]") for e in errors),
                )
            )
        else:
            click.echo(
                "\nPackage uploaded successfully! \n"
                "Visit %s to publish." % api.url("packages/%s" % package_id)
            )


def protocols(api, local, json_flag):
    """List protocols within your manifest or organization."""
    if not local:
        protocol_objs = api.get_protocols()
    else:
        manifest = load_manifest()
        if "protocols" not in list(manifest.keys()) or not manifest["protocols"]:
            click.echo(
                "Your manifest.json file doesn't contain any protocols or"
                " is improperly formatted."
            )
            return
        protocol_objs = manifest["protocols"]
    if json_flag:
        click.echo(json.dumps(protocol_objs))
    else:
        click.echo(
            "\n{:^60}".format(
                "Protocols within this {}:".format(
                    "organization" if not local else "manifest"
                )
            )
        )
        click.echo(f"{'':-^60}")
        for p in protocol_objs:
            if p.get("display_name"):
                display_str = f"{p['name']} ({p.get('display_name')})"
            else:
                display_str = p["name"]
            click.echo(f"{display_str}\n{'':-^60}")


def packages(api, i):
    """List packages in your organization."""
    response = api.packages()
    # there's probably a better way to do this
    package_names = OrderedDict(
        sorted(list({"yours": {}, "theirs": {}}.items()), key=lambda t: len(t[0]))
    )

    for pack in response:
        n = str(pack["name"]).lower().replace(f"com.{api.organization_id}.", "")

        latest = str(pack["latest_version"]) if pack["latest_version"] else "-"

        if pack.get("owner") and pack["owner"]["email"] == api.email:
            package_names["yours"][n] = {}
            package_names["yours"][n]["id"] = str(pack["id"])
            package_names["yours"][n]["latest"] = latest
        else:
            package_names["theirs"][n] = {}
            package_names["theirs"][n]["id"] = str(pack["id"])
            package_names["theirs"][n]["latest"] = latest
    if i:
        return dict(
            list(package_names["yours"].items()) + list(package_names["theirs"].items())
        )
    else:
        for category, packages in list(package_names.items()):
            if category == "yours":
                click.echo("\n{:^90}".format("YOUR PACKAGES:\n"))
                click.echo(
                    f"{'PACKAGE NAME':^30}"
                    + "|"
                    + f"{'PACKAGE ID':^30}"
                    + "|"
                    + f"{'LATEST PUBLISHED RELEASE':^30}"
                )
                click.echo(f"{'':-^90}")
            elif category == "theirs" and list(packages.values()):
                click.echo("\n{:^90}".format("OTHER PACKAGES IN YOUR ORG:\n"))
                click.echo(
                    f"{'PACKAGE NAME':^30}"
                    + "|"
                    + f"{'PACKAGE ID':^30}"
                    + "|"
                    + f"{'LATEST PUBLISHED RELEASE':^30}"
                )
                click.echo(f"{'':-^90}")
            for name, p in list(packages.items()):
                click.echo(
                    f"{name:<30}" + "|" + f"{p['id']:^30}" + "|" + f"{p['latest']:^30}"
                )
                click.echo(f"{'':-^90}")


def create_package(api, description, name):
    """Create a new empty protocol package"""
    existing = api.packages()
    for p in existing:
        if name == p["name"].split(".")[-1]:
            click.echo(
                f"You already have an existing package with the name "
                f'"{name}". Please choose a different package name.'
            )
            return
    try:
        new_pack = api.create_package(name, description)
        if new_pack:
            click.echo(
                "New package '%s' created with id %s \n"
                "View it at %s"
                % (name, new_pack["id"], api.url("packages/%s" % new_pack["id"]))
            )
        else:
            click.echo("There was an error creating this package.")
    except Exception as err:
        click.echo("\n" + str(err))


def delete_package(api, name, force):
    """Delete an existing protocol package"""
    package_id = get_package_id(api, name)
    if package_id:
        try:
            if not force:
                click.confirm(
                    "Are you sure you want to permanently delete the package "
                    "'%s'?  All releases within will be lost."
                    % get_package_name(api, package_id),
                    default=False,
                    abort=True,
                )
                click.confirm("Are you really really sure?", default=True)
            del_pack = api.delete_package(package_id=package_id)
            if del_pack:
                click.echo("Package deleted.")
            else:
                click.echo("There was a problem deleting this package.")
        except Exception as err:
            click.echo("\n" + str(err))


def generate_protocol(name):
    """Generate a python protocol scaffold"""
    # TODO we should update click to be like rails
    #   transcriptic generate protocol FOO
    #   transcriptic generate other_type FOO
    env = Environment(loader=PackageLoader("transcriptic", "templates"))
    template_infos = [
        {"template_name": "manifest.json.jinja", "file_name": "manifest.json"},
        {"template_name": "protocol.py.jinja", "file_name": f"{name}.py"},
        {"template_name": "requirements.txt.jinja", "file_name": "requirements.txt"},
    ]

    # make directory for protocol
    dirname = name
    makedirs(dirname, exist_ok=True)

    # write __init__ package file
    open(f"{dirname}/{'__init__.py'}", "w").write("")

    for template_info in template_infos:
        template_name = template_info["template_name"]
        file_name = template_info["file_name"]
        template = env.get_template(template_name)
        file = open(f"{dirname}/{file_name}", "w")
        output = template.render(name=name)
        file.write(output)

    click.echo(f"Successfully generated protocol '{name}'!")
    click.echo("Testing the protocol is as easy as:")
    click.echo("")
    click.echo(f"\tcd {name}")
    click.echo("\tpip install -r requirements.txt")
    click.echo(f"\ttranscriptic preview {name}")
    click.echo(f"\ttranscriptic launch --local {name} -p SOME_PROJECT_ID")


def upload_dataset(api, file_path, title, run_id, tool, version):
    """Uploads specified file as an analysis dataset to the specified run."""
    resp = api.upload_dataset_from_filepath(
        file_path=file_path,
        title=title,
        run_id=run_id,
        analysis_tool=tool,
        analysis_tool_version=version,
    )
    try:
        data_id = resp["data"]["id"]
        run_route = api.url(f"/api/runs/{run_id}?fields[runs]=project_id")
        run_resp = api.get(run_route)
        project = run_resp["data"]["attributes"]["project_id"]
        datasets_route = api.get_route("datasets", project_id=project, run_id=run_id)
        data_url = f"{datasets_route}/analysis/{data_id}"
        click.echo(f"Dataset uploaded to {data_url}")
    except KeyError:
        click.echo("An unexpected response was returned from the server. ")


def projects(api, i, json_flag):
    """List the projects in your organization"""
    try:
        projects = api.projects()
        proj_id_names = {}
        all_proj = {}
        for proj in projects:
            status = " (archived)" if proj["archived_at"] else ""
            proj_id_names[proj["id"]] = proj["name"]
            all_proj[proj["id"]] = proj["name"] + status
        if i:
            return proj_id_names
        elif json_flag:
            return click.echo(json.dumps(projects))
        else:
            click.echo("\n{:^80}".format("PROJECTS:\n"))
            click.echo(f"{'PROJECT NAME':^40}" + "|" + f"{'PROJECT ID':^40}")
            click.echo(f"{'':-^80}")
            for proj_id, name in list(all_proj.items()):
                click.echo(f"{name:<40}" + "|" + f"{proj_id:^40}")
                click.echo(f"{'':-^80}")
    except RuntimeError:
        click.echo(
            "There was an error listing the projects in your "
            "organization.  Make sure your login details are correct."
        )


def runs(api, project_name, json_flag):
    """List the runs that exist in a project"""
    project_id = get_project_id(api, project_name)
    run_list = []
    if project_id:
        req = api.runs(project_id=project_id)
        if not req:
            click.echo(f"Project '{project_name}' is empty.")
            return
        for r in req:
            run_list.append(
                [
                    r["title"] or "(Untitled)",
                    r["id"],
                    r["completed_at"].split("T")[0]
                    if r["completed_at"]
                    else r["created_at"].split("T")[0],
                    r["status"].replace("_", " "),
                ]
            )
        if json_flag:
            extraction = map(
                lambda x: {
                    "title": x["title"] or "(Untitled)",
                    "id": x["id"],
                    "completed_at": x["completed_at"] if x["completed_at"] else None,
                    "created_at": x["created_at"],
                    "status": x["status"],
                },
                req,
            )

            return click.echo(json.dumps(extraction))
        else:
            click.echo(
                "\n{:^120}".format(
                    "Runs in Project '%s':\n" % get_project_name(api, project_id)
                )
            )
            click.echo(
                f"{'RUN TITLE':^30}"
                + "|"
                + f"{'RUN ID':^30}"
                + "|"
                + f"{'RUN DATE':^30}"
                + "|"
                + f"{'RUN STATUS':^30}"
            )
            click.echo(f"{'':-^120}")
            for run in run_list:
                click.echo(
                    f"{run[0]:^30}"
                    + "|"
                    + f"{run[1]:^30}"
                    + "|"
                    + f"{run[2]:^30}"
                    + "|"
                    + f"{run[3]:^30}"
                )
                click.echo(f"{'':-^120}")


def create_project(api, name, dev):
    """Create a new empty project."""
    existing = api.projects()
    for p in existing:
        if name == p["name"].split(".")[-1]:
            click.confirm(
                f"You already have an existing project with the name '{name}'. "
                f"Are you sure you want to create another one?",
                default=False,
                abort=True,
            )
            break
    try:
        new_proj = api.create_project(name)
        click.echo(
            "New%s project '%s' created with id %s  \nView it at %s"
            % (
                " pilot" if dev else "",
                name,
                new_proj["id"],
                api.url("%s" % (new_proj["id"])),
            )
        )
    except RuntimeError:
        click.echo("There was an error creating this project.")


def delete_project(api, name, force):
    """Delete an existing project."""
    project_id = get_project_id(api, name)
    if project_id:
        if not force:
            click.confirm(
                "Are you sure you want to permanently delete '%s'?"
                % get_project_name(api, project_id),
                default=False,
                abort=True,
            )
        if api.delete_project(project_id=str(project_id)):
            click.echo("Project deleted.")
        else:
            click.confirm(
                "Could not delete project. This may be because it contains \
                runs. Try archiving it instead?",
                default=False,
                abort=True,
            )
            if api.archive_project(project_id=str(project_id)):
                click.echo("Project archived.")
            else:
                click.echo("Could not archive project!")


def resources(api, query):
    """Search catalog of provisionable resources"""
    resource_req = api.resources(query)
    if resource_req["results"]:
        kit_req = api.kits(query)
        if not kit_req["results"]:
            common_name = resource_req["results"][0]["name"]
            kit_req = api.kits(common_name)
        flat_items = list(
            flatmap(
                lambda x: [
                    {
                        "name": y["resource"]["name"],
                        "id": y["resource"]["id"],
                        "vendor": x["vendor"]["name"]
                        if "vendor" in list(x.keys())
                        else "",
                    }
                    for y in x["kit_items"]
                    if (y["provisionable"] and not y["reservable"])
                ],
                kit_req["results"],
            )
        )
        rs_id_list = [rs["id"] for rs in resource_req["results"]]

        matched_resources = []
        for item in flat_items:
            if item["id"] in rs_id_list and item not in matched_resources:
                matched_resources.append(item)

        if matched_resources:
            click.echo(f"Results for '{query}':")
            click.echo(
                f"{'Resource Name':^40}"
                + "|"
                + f"{'Vendor':^40}"
                + "|"
                + f"{'Resource ID':^40}"
            )
            click.echo(f"{'':-^120}")
            for resource in matched_resources:
                click.echo(
                    f"{ascii_encode(resource['name']):^40}"
                    + "|"
                    + f"{ascii_encode(resource['vendor']):^40}"
                    + "|"
                    + f"{ascii_encode(resource['id']):^40}"
                )
            click.echo(f"{'':-^120}")
        else:
            click.echo(f"No usable resource for '{query}'.")
    else:
        click.echo(f"No results for '{query}'.")


def inventory(api, include_aliquots, show_status, retrieve_all, query):
    """Search organization for inventory"""
    inventory_req = api.inventory(query)
    num_pages = inventory_req["num_pages"]
    per_page = inventory_req["per_page"]
    results = inventory_req["results"]
    max_results_bound = num_pages * per_page

    num_prefiltered = len(results)

    if retrieve_all:
        for i in range(1, num_pages):
            click.echo(
                f"Retrieved {i * per_page} records out of "
                f"{max_results_bound} total for '{query}'...\r",
                nl=False,
            )
            inventory_req = api.inventory(query, page=i)
            results.extend(inventory_req["results"])
        click.echo()

    if include_aliquots:
        results = [c if "label" in c else c["container"] for c in results]
    else:
        results = [c for c in results if "label" in c]
    results = [i for n, i in enumerate(results) if i not in results[n + 1 :]]

    if results:

        def truncate_time(d, k):
            old_time = d[k]
            d[k] = old_time.split("T")[0]
            return d

        results = [truncate_time(c, "created_at") for c in results]
        barcode_present = any(c["barcode"] for c in results)
        keys = ["label", "id", "container_type_id", "storage_condition", "created_at"]
        if barcode_present:
            keys.insert(2, "barcode")
        if show_status:
            keys.append("status")
        friendly_keys = {k: k.split("_")[0] for k in keys}
        spacing = {
            k: max(len(friendly_keys[k]), max([len(str(c[k])) for c in results]))
            for k in keys
        }
        spacing = {k: (v // 2 + 1) * 2 + 1 for k, v in spacing.items()}
        sum_spacing = sum(spacing.values()) + (len(keys) - 1) * 3 + 1
        spacing = {k: "{:^%s}" % v for k, v in spacing.items()}
        sum_spacing = "{:-^%s}" % sum_spacing
        click.echo(f"Results for '{query}':")
        click.echo(" | ".join([spacing[k].format(friendly_keys[k]) for k in keys]))
        click.echo(sum_spacing.format(""))
        for c in results:
            click.echo(
                " | ".join([spacing[k].format(ascii_encode(c[k])) for k in keys])
            )
            click.echo(sum_spacing.format(""))
        if not retrieve_all:
            if num_pages > 1:
                click.echo(
                    f"Retrieved {num_prefiltered} records out of "
                    f"{max_results_bound} total (use the --retrieve_all "
                    f"flag to request all records)."
                )
    else:
        if retrieve_all:
            click.echo(f"No results for '{query}'.")
        else:
            if num_pages > 1:
                click.echo(
                    f"Retrieved {num_prefiltered} records out of "
                    f"{max_results_bound} total but all were filtered "
                    f"out. Use the --retrieve_all flag to request all "
                    f"records."
                )
            else:
                click.echo(
                    "All records were filtered out. Use flags to modify your search"
                )


def payments(api):
    """Lists available payment methods"""
    methods = api.payment_methods()
    click.echo(f"{'Method':^50}" + "|" + f"{'Expiry':^20}" + "|" + f"{'Id':^20}")
    click.echo(f"{'':-^90}")
    if len(methods) == 0:
        print_stderr("No payment methods found.")
        return
    for method in methods:
        if method["type"] == "CreditCard":
            description = (
                f"{method['credit_card_type']} ending with "
                f"{method['credit_card_last_4']}"
            )
        elif method["type"] == "PurchaseOrder":
            description = f"Purchase Order \"{method['description']}\""
        else:
            description = method["description"]
        if method["is_default?"]:
            description += " (Default)"
        if not method["is_valid"]:
            description += " (Invalid)"
        click.echo(
            f"{ascii_encode(description):^50}"
            + "|"
            + f"{ascii_encode(method['expiry']):^20}"
            + "|"
            + f"{ascii_encode(method['id']):^20}"
        )


def init(path):
    """Initialize a directory with a manifest.json file."""
    manifest_data = OrderedDict(
        format="python",
        license="MIT",
        protocols=[
            {
                "name": "SampleProtocol",
                "version": "0.0.1",
                "display_name": "Sample Protocol",
                "description": "This is a protocol.",
                "command_string": "python sample_protocol.py",
                "inputs": {},
                "preview": {"refs": {}, "parameters": {}},
            }
        ],
    )
    try:
        os.makedirs(path)
    except OSError:
        click.echo("Specified directory already exists.")
    if isfile(f"{path}/manifest.json"):
        click.confirm(
            "This directory already contains a manifest.json file, "
            "would you like to overwrite it with an empty one? ",
            default=False,
            abort=True,
        )
    with open(f"{path}/manifest.json", "w+") as f:
        click.echo("Creating empty manifest.json...")
        f.write(json.dumps(dict(manifest_data), indent=2))
        click.echo("manifest.json created")


def analyze(api, file, test):
    """Analyze a block of Autoprotocol JSON."""
    with click.open_file(file, "r") as f:
        try:
            protocol = json.loads(f.read())
        except ValueError:
            click.echo(
                "Error: The Autoprotocol you're trying to analyze is "
                "not properly formatted. \n"
                "Check that your manifest.json file is "
                "valid JSON and/or your script "
                "doesn't print anything other than pure Autoprotocol "
                "to standard out."
            )
            return

    try:
        analysis = api.analyze_run(protocol, test_mode=test)
        click.echo("\u2713 Protocol analyzed")
        format_analysis(analysis)
    except Exception as err:
        click.echo("\n" + str(err))


def preview(api, protocol_name, view, dye_test):
    """Preview the Autoprotocol output of protocol in the current package."""
    manifest, protocol = load_manifest_and_protocol(protocol_name)

    try:
        inputs = protocol["preview"]
    except KeyError:
        click.echo(
            "Error: The manifest.json you're trying to preview doesn't "
            'contain a "preview" section'
        )
        return

    run_protocol(api, manifest, protocol, inputs, view, dye_test)


def summarize(api, file, html, tree, lookup, runtime):
    with click.open_file(file, "r") as f:
        try:
            protocol = json.loads(f.read())
        except ValueError:
            click.echo("The autoprotocol you're trying to summarize is invalid.")
            return

    if html:
        url = ProtocolPreview(protocol, api).preview_url
        click.echo(f"View your protocol here {url}")
        return

    parser = AutoprotocolParser(protocol, api=api)

    if tree:
        import multiprocessing

        print("\nGenerating Job Tree...")
        p = multiprocessing.Process(target=parser.job_tree)
        p.start()

        # Wait for <runtime_allowance> seconds or until process finishes
        p.join(runtime)

        # If thread is still active
        if p.is_alive():
            print("Still running... Aborting tree construction.")
            print(
                "Please allow for more runtime allowance, or opt for no tree construction.\n"
            )

            # Terminate
            p.terminate()
            p.join()
        else:
            print("\nYour Job Tree is complete!\n")


def compile(protocol_name, args):
    """Compile a protocol by passing it a config file (without submitting or
     analyzing)."""
    manifest, protocol = load_manifest_and_protocol(protocol_name)

    try:
        command = protocol["command_string"]
    except KeyError:
        click.echo(
            'Error: Your manifest.json file does not have a "command_string" \
            key.'
        )
        return
    from subprocess import call

    call(["bash", "-c", command + " " + " ".join(args)])


def launch(
    api,
    protocol,
    project,
    title,
    save_input,
    local,
    accept_quote,
    params,
    pm=None,
    test=None,
    pkg=None,
):
    """Configure and launch a protocol either using the local manifest file or remotely.
    If no parameters are specified, uses the webapp to select the inputs."""
    # Validate payment method
    if pm is not None and not is_valid_payment_method(api, pm):
        print_stderr(
            "Payment method is invalid. Please specify a payment "
            "method from `transcriptic payments` or not specify the "
            "`--payment` flag to use the default payment method."
        )
        return
    # Load protocol from local file if not remote and load from listed protocols otherwise
    if local:
        manifest, protocol_obj = load_manifest_and_protocol(protocol)
    else:
        print_stderr(f"Searching for {protocol}...")
        protocol_list = api.get_protocols()

        matched_protocols = [
            p
            for p in protocol_list
            if (p["name"] == protocol and (pkg is None or p["package_id"] == pkg))
        ]

        if len(matched_protocols) == 0:
            print_stderr(
                f"Protocol {protocol} in "
                f"{f'package {pkg}' if pkg else 'unspecified package'} "
                f"was not found."
            )
            return
        elif len(matched_protocols) > 1:
            print_stderr("More than one match found. Using the first match.")
        else:
            print_stderr("Protocol found.")
        protocol_obj = matched_protocols[0]

    # If parameters are not specified, use quick launch to get inputs
    if not params:
        # Project is required for quick launch
        if not project:
            click.echo("Project field is required if parameters file is not specified.")
            return
        project = get_project_id(api, project)
        if not project:
            return

        # Creates web browser and generates inputs for quick_launch
        quick_launch = _get_quick_launch(api, protocol_obj, project)

        # Save the protocol input locally if the user specified the save_input option
        if save_input:
            try:
                with click.open_file(save_input, "w") as f:
                    f.write(
                        json.dumps(
                            dict(parameters=quick_launch["raw_inputs"]), indent=2
                        )
                    )
            except Exception as e:
                print_stderr("\nUnable to save inputs: %s" % str(e))

    if not local:
        # For remote execution, use input params file if specified, else use quick_launch inputs
        if not params:
            params = dict(parameters=quick_launch["raw_inputs"])
            # Save parameters to file if specified
            if save_input:
                try:
                    with click.open_file(save_input, "w") as f:
                        f.write(json.dumps(params, indent=2))
                except Exception as e:
                    print_stderr("\nUnable to save inputs: %s" % str(e))
        else:
            try:
                params = json.loads(params.read())
            except ValueError:
                print_stderr(
                    "Unable to load parameters given. "
                    "File is probably incorrectly formatted."
                )
                return

        req_id, launch_protocol = _get_launch_request(api, params, protocol_obj, test)

        # Check for generation errors
        generation_errs = launch_protocol["generation_errors"]

        if len(generation_errs) > 0:
            for errors in generation_errs:
                click.echo("\n\n" + str(errors["message"]))
            click.echo("\nPlease fix the above errors and try again.")
            return

        # Confirm proceeding with purchase
        if not accept_quote:
            click.echo("\n\nCost Breakdown")
            resp = api.analyze_launch_request(req_id, test_mode=test)
            click.echo(price(resp))
            confirmed = click.confirm(
                "Would you like to continue with launching the protocol",
                prompt_suffix="? ",
                default=False,
            )
            if not confirmed:
                return

        # Project is required for run submission
        if not project:
            click.echo("\nProject field is required for run submission.")
            return
        project = get_project_id(api, project)
        if not project:
            return

        from time import strftime, gmtime

        if title:
            default_title = f"{title}_{strftime('%b_%d_%Y', gmtime())}"
        else:
            default_title = f"{protocol}_{strftime('%b_%d_%Y', gmtime())}"

        try:
            req_json = api.submit_launch_request(
                req_id,
                protocol_id=protocol_obj["id"],
                project_id=project,
                title=default_title,
                test_mode=test,
                payment_method_id=pm,
            )
            run_id = req_json["id"]
            click.echo("\nRun created: %s" % api.url("%s/runs/%s" % (project, run_id)))
        except Exception as err:
            click.echo("\n" + str(err))
    else:
        print_stderr("\nGenerating Autoprotocol....\n")
        if not params:
            run_protocol(api, manifest, protocol_obj, quick_launch["inputs"])
        else:
            """
            In the case of a local `launch`, we need to generate `inputs` from
            `raw_inputs`, since the `run_protocol` function takes in JSON which
            is `inputs`-formatted.
            `inputs` is basically an extended version of `raw_inputs`, where
            we populate properties such as aliquot information for specified
            containerIds.
            In order to generate these `inputs`, we can create a new quick
            launch
            """
            try:
                params = json.loads(params.read())
                # This is the input format required by resolve_inputs
                formatted_inputs = dict(inputs=params["parameters"])
            except ValueError:
                print_stderr(
                    "Unable to load parameters given. "
                    "File is probably incorrectly formatted."
                )
                return
            quick_launch = api.create_quick_launch(
                data=json.dumps({"manifest": protocol_obj}), project_id=project
            )
            quick_launch_obj = api.resolve_quick_launch_inputs(
                formatted_inputs, project_id=project, quick_launch_id=quick_launch["id"]
            )
            inputs = quick_launch_obj["inputs"]
            run_protocol(api, manifest, protocol_obj, inputs)

def generate_preview_parameters(api, protocol, project, local, filename, merge, pkg=None):
    """Generate preview parameters for a specified protocol from selected samples"""
    # Load protocol from local file if not remote and load from listed protocols otherwise
    if local:
        manifest, protocol_obj = load_manifest_and_protocol(protocol)
    else:
        print_stderr("Searching for {}...".format(protocol))
        protocol_list = api.get_protocols()

        matched_protocols = [p for p in protocol_list if (
            p['name'] == protocol and (pkg is None or p['package_id'] == pkg)
        )]

        if len(matched_protocols) == 0:
            print_stderr(
                "Protocol {} in {} was not found."
                "".format(
                    protocol,
                    "package {}".format(pkg) if pkg else "unspecified package"
                )
            )
            return
        elif len(matched_protocols) > 1:
            print_stderr("More than one match found. Using the first match.")
        else:
            print_stderr("Protocol found.")
        protocol_obj = matched_protocols[0]
    # Project is required for quick launch
    if not project:
        click.echo("Project field is required if parameters file is not specified.")
        return
    project = get_project_id(api, project)
    if not project:
        return
    # Creates web browser and generates inputs for quick_launch
    quick_launch = _get_quick_launch(api, protocol_obj, project)
    pp = PreviewParameters(api, quick_launch["raw_inputs"])
    # Determine where to place the generated preview parameters
    if not merge:
        if not filename:
            filename = 'preview_parameters.json'
        try:
            with click.open_file(filename, 'w') as f:
                f.write(json.dumps(pp.preview, indent=2))
                f.close()
        except Exception as e:
            print_stderr("\nUnable to save preview inputs due to not being"
                         " able to process: {} {}".format(type(e), str(e)))
    else:
        # Read manifest.json
        with click.open_file('manifest.json', 'r') as f:
            manifest = json.loads(f.read())
        # Get selected protocol
        selected_protocol = next(p for p in manifest['protocols'] if p['name'] == protocol)
        # Get the index of the protocol in the protocols list
        protocol_idx = manifest['protocols'].index(selected_protocol)
        # Merge generated preview parameters into the selected protocol
        selected_protocol['preview'] = pp.preview['preview']
        # Ensure that the merged protocol object has the same key order
        updated_protocol = OrderedDict()
        updated_protocol['name'] = selected_protocol['name']
        updated_protocol['display_name'] = selected_protocol['display_name']
        updated_protocol['categories'] = selected_protocol['categories']
        updated_protocol['description'] = selected_protocol['description']
        updated_protocol['version'] = selected_protocol['version']
        updated_protocol['command_string'] = selected_protocol['command_string']
        updated_protocol['inputs'] = selected_protocol['inputs']
        updated_protocol['preview'] = selected_protocol['preview']
        # Place modified protocol in the appropriate index
        manifest['protocols'][protocol_idx] = updated_protocol
        # Ensure that manifest has correct order
        merged_manifest = OrderedDict()
        merged_manifest['format'] = "python"
        merged_manifest['license'] = "MIT"
        merged_manifest['protocols'] = manifest['protocols']
        # Write new manifest to current working directory
        try:
            with click.open_file('manifest.json', 'w') as f:
                f.write(json.dumps(merged_manifest, indent=2))
                f.close()
        except Exception as e:
            print_stderr("\nUnable to save preview inputs due to not being"
                         " able to process: {} {}".format(type(e), str(e)))


def select_org(api, config, organization=None):
    """Allows you to switch organizations. If the organization argument
    is provided, this will directly select the specified organization.
    """
    org_list = [
        {"name": org["name"], "subdomain": org["subdomain"]}
        for org in api.organizations()
    ]
    if organization is None:
        organization = org_prompt(org_list)

    r = api.get_organization(org_id=organization)
    if r.status_code != 200:
        click.echo(f"Error accessing organization: {r.text}")
        sys.exit(1)

    api.organization_id = organization
    api.save(config)
    click.echo(f"Logged in with organization: {organization}")


def login(api, config, api_root=None, analytics=True, rsa_key=None):
    """Authenticate to your Transcriptic account."""
    if api_root is None:
        # Always default to the pre-defined api-root if possible, else use
        # the secure.transcriptic.com domain
        try:
            api_root = api.api_root
        except ValueError:
            api_root = "https://secure.transcriptic.com"

    rsa_auth = None
    rsa_key_path = None
    if rsa_key is not None:
        try:
            rsa_key_path = abspath(expanduser(rsa_key))
            with open(rsa_key_path, "rb") as key_file:
                rsa_secret = key_file.read()
        except Exception:
            click.echo(
                f"Error loading RSA key. Please check that the file "
                f"{rsa_key} is accessible"
            )
            sys.exit(1)

        # Try making an auth handler with a dummy email so that the command
        # fails early
        try:
            rsa_auth = StrateosSign("foo@bar.com", rsa_secret)
        except Exception as e:
            click.echo(f"Error loading RSA key: {e}")
            sys.exit(1)

    email = click.prompt("Email")
    password = click.prompt("Password", hide_input=True)

    # replace the dummy rsa_auth with a handler using the given email
    if rsa_auth is not None:
        rsa_auth = StrateosSign(email, rsa_auth.secret)

    try:
        r = api.post(
            routes.login(api_root=api_root),
            data=json.dumps({"user": {"email": email, "password": password,},}),
            headers={"Accept": "application/json", "Content-Type": "application/json",},
            status_response={
                "200": lambda resp: resp,
                "401": lambda resp: resp,
                "default": lambda resp: resp,
            },
            auth=rsa_auth,
        )

    except requests.exceptions.RequestException:
        click.echo(
            f"Error logging into specified host: {api_root}. "
            f"Please check your internet connection and host name"
        )
        sys.exit(1)

    except Exception as e:
        click.echo(f"Error connecting to host: {e}")
        sys.exit(1)

    if r.status_code != 200:
        click.echo(f"Error logging into Transcriptic: {r.json()['error']}")
        sys.exit(1)
    user = r.json()
    token = user.get("authentication_token") or user["test_mode_authentication_token"]
    user_id = user.get("id")
    feature_groups = user.get("feature_groups")
    organization = org_prompt(user["organizations"])

    try:
        r = api.get(
            routes.get_organization(api_root=api_root, org_id=organization),
            headers={
                "X-User-Email": email,
                "X-User-Token": token,
                "Accept": "application/json",
            },
            auth=rsa_auth,
            status_response={"200": lambda resp: resp, "default": lambda resp: resp},
        )
    except PermissionError as e:
        click.echo(e)
        if rsa_key is not None:
            click.echo("Are you sure you require the `--rsa-key` option?")
        sys.exit(1)

    if r.status_code != 200:
        click.echo(f"Error accessing organization: {r.text}")
        sys.exit(1)
    api = Connection(
        email=email,
        token=token,
        organization_id=organization,
        api_root=api_root,
        user_id=user_id,
        analytics=analytics,
        feature_groups=feature_groups,
        rsa_key=rsa_key_path,
    )
    api.save(config)
    click.echo(f"Logged in as {user['email']} ({organization})")


def format(manifest):
    """Check Autoprotocol format of manifest.json."""
    manifest = parse_json(manifest)
    try:
        iter_json(manifest)
        click.echo("No manifest formatting errors found.")
    except RuntimeError:
        pass


######################
# UTIL
######################


def is_valid_payment_method(api, id):
    """Determines if payment is valid"""
    methods = api.payment_methods()
    return any([id == method["id"] and method["is_valid"] for method in methods])


def format_analysis(response):
    def count(thing, things, num):
        click.echo(f"  {num} {thing if num == 1 else things}")

    count("instruction", "instructions", len(response["instructions"]))
    count("container", "containers", len(response["refs"]))
    price(response)
    for w in response["warnings"]:
        message = w["message"]
        if "instruction" in w["context"]:
            context = f"instruction {w['context']['instruction']}"
        else:
            context = json.dumps(w["context"])
        click.echo(f"WARNING ({context}): {message}")


def price(response):
    """Prints out price based on response"""

    # quote won't appear in response if user is missing permissions.
    if "quote" not in response or "items" not in response["quote"]:
        return

    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    separator_len = 24

    for quote_item in response["quote"]["items"]:
        locale_cost = locale.currency(float(quote_item["cost"]), grouping=True)
        quote_str = f"  {quote_item['title']}: {locale_cost}"
        click.echo(quote_str)
        separator_len = max(separator_len, len(quote_str))

    click.echo("-" * separator_len)

    click.echo(
        "  Total Cost: %s"
        % locale.currency(float(response["total_cost"]), grouping=True)
    )


def _create_launch_request(params, bsl=1, test_mode=False):
    """Creates launch_request from input params"""
    params_dict = dict()
    params_dict["launch_request"] = params
    params_dict["launch_request"]["bsl"] = bsl
    params_dict["launch_request"]["test_mode"] = test_mode
    return json.dumps(params_dict)


def _get_launch_request(api, params, protocol, test_mode):
    """Launches protocol from parameters"""
    launch_request = _create_launch_request(params, test_mode=test_mode)

    launch_protocol = api.launch_protocol(launch_request, protocol_id=protocol["id"])
    launch_request_id = launch_protocol["id"]

    # Wait until launch request is updated (max 5 minutes)
    count = 1
    while count <= 150 and launch_protocol["progress"] != 100:
        sys.stderr.write(
            "\rWaiting for launch request to be configured%s" % ("." * count)
        )
        sys.stderr.flush()
        time.sleep(2)
        launch_protocol = api.get_launch_request(
            protocol_id=protocol["id"], launch_request_id=launch_request_id
        )
        count += 1

    return launch_request_id, launch_protocol


def _get_quick_launch(api, protocol, project):
    """Creates quick launch object and opens it in a new tab"""
    quick_launch = api.create_quick_launch(
        data=json.dumps({"manifest": protocol}), project_id=project
    )
    quick_launch_mtime = quick_launch["updated_at"]

    format_str = "\nOpening %s"
    url = api.get_route(
        "get_quick_launch", project_id=project, quick_launch_id=quick_launch["id"]
    )
    print_stderr(format_str % url)

    """
    Open the URL in the webbrowser. We have to temporarily suppress stdout/
    stderr because the webbrowser module dumps some garbage which gets into
    out stdout and corrupts the generated autoprotocol
    """
    import webbrowser

    with stdchannel_redirected(sys.stderr, os.devnull):
        with stdchannel_redirected(sys.stdout, os.devnull):
            webbrowser.open_new_tab(url)

    # Wait until the quick launch inputs are updated (max 15 minutes)
    count = 1
    while (
        count <= 180
        and quick_launch["inputs"] is None
        or quick_launch_mtime >= quick_launch["updated_at"]
    ):
        sys.stderr.write("\rWaiting for inputs to be configured%s" % ("." * count))
        sys.stderr.flush()
        time.sleep(5)

        quick_launch = api.get_quick_launch(
            project_id=project, quick_launch_id=quick_launch["id"]
        )
        count += 1
    return quick_launch


def org_prompt(org_list):
    """Organization prompt for helping with selecting organization"""
    if len(org_list) < 1:
        click.echo(
            f"Error: You don't appear to belong to any organizations. \n"
            f"Visit {'https://secure.transcriptic.com'} and create an "
            f"organization."
        )
        sys.exit(1)
    if len(org_list) == 1:
        organization = org_list[0]["subdomain"]
    else:
        click.echo("You belong to %s organizations:" % len(org_list))
        for indx, o in enumerate(org_list):
            click.echo(f"{indx + 1}.  {o['name']} ({o['subdomain']})")

        def parse_valid_org(indx):
            from click.exceptions import BadParameter

            try:
                org_indx = int(indx) - 1
                if org_indx < 0 or org_indx >= len(org_list):
                    raise ValueError("Value out of range")
                return org_list[org_indx]["subdomain"]
            except:
                raise BadParameter(
                    "Please enter an integer between 1 and %s" % (len(org_list))
                )

        organization = click.prompt(
            "Which organization would you like to log in as",
            default=1,
            prompt_suffix="? ",
            type=int,
            value_proc=lambda x: parse_valid_org(x),
        )
        # Catch since `value_proc` doesn't properly parse default
        if organization == 1:
            organization = org_list[0]["subdomain"]
    return organization


def get_project_id(api, name):
    projs = projects(api, True, True)
    if name in projs:
        return name
    else:
        project_ids = [k for k, v in projs.items() if v == name]
        if not project_ids:
            click.echo(f"The project '{name}' was not found in your organization.")
            return
        elif len(project_ids) > 1:
            click.echo(f"Found multiple projects: {project_ids} that match '{name}'.")
            # TODO: Add project selector with dates and number of runs
            return
        else:
            return project_ids[0]


def get_project_name(api, id):
    projs = projects(api, True, True)
    name = projs.get(id)
    if not name:
        name = id if id in projs.values() else None
        if not name:
            click.echo(f"The project '{name}' was not found in your organization.")
            return
    return name


def get_package_id(api, name):
    package_names = packages(api, True)
    package_names = {k.lower(): v["id"] for k, v in list(package_names.items())}
    package_id = package_names.get(name)
    if not package_id:
        package_id = name if name in list(package_names.values()) else None
    if not package_id:
        click.echo(f"The package '{name}' does not exist in your organization.")
        return
    return package_id


def get_package_name(api, package_id):
    package_names_all = packages(api, True)
    package_names = {v["id"]: k for k, v in list(package_names_all.items())}
    package_name = package_names.get(package_id)
    if not package_name:
        package_name = (
            package_id if package_id in list(package_names.values()) else None
        )
    if not package_name:
        click.echo(
            f"The id '{package_id}' does not match any package in your "
            f"organization."
        )
        return
    return package_name


def load_manifest():
    try:
        with click.open_file("manifest.json", "r") as f:
            manifest = json.loads(f.read(), object_pairs_hook=OrderedDict)
    except IOError:
        click.echo("The current directory does not contain a manifest.json file.")
        sys.exit(1)
    except ValueError:
        click.echo(
            "Error: Your manifest.json file is improperly formatted. "
            "Please double check your brackets and commas!"
        )
        sys.exit(1)
    return manifest


def load_protocol(manifest, protocol_name):
    try:
        p = next(p for p in manifest["protocols"] if p["name"] == protocol_name)
    except KeyError:
        click.echo(
            'Error: Your manifest.json file does not have a "protocols" \
             key.'
        )
        sys.exit(1)
    except StopIteration:
        click.echo(
            f"Error: The protocol name '{protocol_name}' does not match "
            f"any protocols that can be previewed from within this "
            f"directory.  \n"
            f"Check either your protocol's spelling or your "
            f"manifest.json file and try again."
        )
        sys.exit(1)
    return p


def load_manifest_and_protocol(protocol_name):
    manifest = load_manifest()
    protocol = load_protocol(manifest, protocol_name)
    return (manifest, protocol)


def run_protocol(api, manifest, protocol, inputs, view=False, dye_test=False):
    try:
        command = protocol["command_string"]
    except KeyError:
        click.echo(
            'Error: Your manifest.json file does not have a "command_string" \
             key.'
        )
        return

    from subprocess import check_output, CalledProcessError
    import tempfile

    with tempfile.NamedTemporaryFile() as fp:
        fp.write(bytes(json.dumps(inputs), "UTF-8"))
        fp.flush()
        try:
            if dye_test:
                protocol = check_output(
                    ["bash", "-c", command + " " + fp.name + " --dye_test"]
                )
            else:
                protocol = check_output(["bash", "-c", command + " " + fp.name])
            click.echo(protocol)
            if view:
                click.echo(
                    f"View your protocol's raw JSON above or see the "
                    f"instructions rendered at the following link: \n"
                    f"{ProtocolPreview(protocol, api).preview_url}"
                )
        except CalledProcessError as e:
            click.echo(e.output)
            return


def parse_json(json_file):
    try:
        return json.load(open(json_file))
    except ValueError as e:
        click.echo(f"Invalid json: {e}")
        return None


def print_stderr(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


@contextmanager
def stdchannel_redirected(stdchannel, dest_filename):
    """
    A context manager to temporarily redirect stdout or stderr

    e.g.:


    with stdchannel_redirected(sys.stderr, os.devnull):
        if compiler.has_function('clock_gettime', libraries=['rt']):
            libraries.append('rt')
    """
    try:
        oldstdchannel = os.dup(stdchannel.fileno())
        dest_file = open(dest_filename, "w")
        os.dup2(dest_file.fileno(), stdchannel.fileno())

        yield
    finally:
        if oldstdchannel is not None:
            os.dup2(oldstdchannel, stdchannel.fileno())
        if dest_file is not None:
            dest_file.close()


# Placing this here since this is exclusively used by the CLI currently
class ProtocolPreview(object):
    """
    An object for previewing protocols
    """

    def __init__(self, protocol, api):
        self.protocol = protocol
        preview_id = api.preview_protocol(protocol)
        self.preview_url = api.get_route(
            "preview_protocol_embed", preview_id=preview_id
        )

    def _repr_html_(self):
        return f"""<iframe src="{self.preview_url}" frameborder="0"
        allowtransparency="true" style="height:500px" seamless></iframe>"""
