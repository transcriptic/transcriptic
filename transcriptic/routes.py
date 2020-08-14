"""
Big dumb file of routes, please do not add any logic into this file
Note: {api_root} and {org_id} are automatically supplied in the Connection.get_route and do not need to be specified
"""

def get_container(api_root, org_id, container_id):
    return "{api_root}/{org_id}/samples/{container_id}".format(**locals())


def create_project(api_root, org_id):
    return "{api_root}/{org_id}".format(**locals())


def delete_project(api_root, org_id, project_id):
    return "{api_root}/{org_id}/{project_id}".format(**locals())


def archive_project(api_root, org_id, project_id):
    return "{api_root}/{org_id}/{project_id}".format(**locals())


def get_project(api_root, org_id, project_id):
    return "{api_root}/{org_id}/{project_id}".format(**locals())


def get_projects(api_root, org_id):
    return "{api_root}/{org_id}/?q=&per_page=500".format(**locals())


def get_project_runs(api_root, org_id, project_id):
    return "{api_root}/{org_id}/{project_id}/runs".format(**locals())


def create_package(api_root, org_id):
    return "{api_root}/{org_id}/packages".format(**locals())


def delete_package(api_root, org_id, package_id):
    return "{api_root}/{org_id}/packages/{package_id}".format(**locals())


def get_package(api_root, org_id, package_id):
    return "{api_root}/{org_id}/packages/{package_id}".format(**locals())


def get_packages(api_root, org_id):
    return "{api_root}/{org_id}/packages/".format(**locals())


def get_protocols(api_root, org_id):
    return "{api_root}/{org_id}/protocols".format(**locals())


def launch_protocol(api_root, org_id, protocol_id):
    return "{api_root}/{org_id}/protocols/{protocol_id}/launch".format(**locals())


def get_launch_request(api_root, org_id, protocol_id, launch_request_id):
    return "{api_root}/{org_id}/protocols/{protocol_id}/launch/{launch_request_id}".format(
        **locals()
    )


def post_release(api_root, org_id, package_id):
    return "{api_root}/{org_id}/packages/{package_id}/releases/".format(**locals())


def get_release_status(api_root, org_id, package_id, release_id, timestamp):
    return "{api_root}/{org_id}/packages/{package_id}/releases/{release_id}?_={timestamp}".format(
        **locals()
    )


def query_kits(api_root, query):
    return "{api_root}/_commercial/kits?q={query}&per_page=1000&full_json=true".format(
        **locals()
    )


def query_resources(api_root, query):
    return "{api_root}/_commercial/resources?q={query}&per_page=1000".format(**locals())


def query_inventory(api_root, org_id, query, page=0):
    return "{api_root}/{org_id}/inventory/samples?q={query}&per_page=75&page={page}".format(
        **locals()
    )


def get_quick_launch(api_root, org_id, project_id, quick_launch_id):
    return "{api_root}/{org_id}/{project_id}/runs/quick_launch/{quick_launch_id}".format(
        **locals()
    )


def create_quick_launch(api_root, org_id, project_id):
    return "{api_root}/{org_id}/{project_id}/runs/quick_launch".format(**locals())


def resolve_quick_launch_inputs(api_root, org_id, project_id, quick_launch_id):
    return (
        "{api_root}/{org_id}/{project_id}/runs/quick_launch/"
        "{quick_launch_id}/resolve_inputs".format(**locals())
    )


def login(api_root):
    return "{api_root}/users/sign_in".format(**locals())


def get_organizations(api_root):
    return "{api_root}/organizations".format(**locals())


def get_organization(api_root, org_id):
    return "{api_root}/{org_id}".format(**locals())


def deref_route(api_root, obj_id):
    return "{api_root}/-/{obj_id}".format(**locals())


def analyze_run(api_root, org_id):
    return "{api_root}/{org_id}/analyze_run".format(**locals())


def analyze_launch_request(api_root, org_id):
    return "{api_root}/{org_id}/analyze_run".format(**locals())


def submit_run(api_root, org_id, project_id):
    return "{api_root}/{org_id}/{project_id}/runs".format(**locals())


def submit_launch_request(api_root, org_id, project_id):
    return "{api_root}/{org_id}/{project_id}/runs".format(**locals())


def dataset_short(api_root, data_id):
    return "{api_root}/datasets/{data_id}.json".format(**locals())


def dataset(api_root, data_id, key):
    return "{api_root}/datasets/{data_id}.json?key={key}".format(**locals())


def datasets(api_root, org_id, project_id, run_id):
    return "{api_root}/{org_id}/{project_id}/runs/{run_id}/data".format(**locals())


def data_object(api_root, id):
    return "{api_root}/api/data_objects/{id}".format(**locals())


def data_objects(api_root, dataset_id):
    return "{api_root}/api/data_objects?filter[dataset_id]={dataset_id}".format(
        **locals()
    )


def get_uploads(api_root, key):
    return "{api_root}/upload/url_for?key={key}".format(**locals())


def upload(api_root):
    return "{api_root}/api/uploads".format(**locals())


def upload_datasets(api_root):
    return "{api_root}/api/datasets".format(**locals())


def modify_aliquot_properties(api_root, aliquot_id):
    return "{api_root}/api/aliquots/{aliquot_id}/modify_properties".format(**locals())


def preview_protocol(api_root):
    return "{api_root}/runs/preview".format(**locals())


def preview_protocol_embed(api_root, preview_id):
    return "{api_root}/runs/preview/{preview_id}.embed".format(**locals())


def view_data(api_root, data_id):
    return "{api_root}/datasets/{data_id}.embed".format(**locals())


def view_run(api_root, org_id, project_id, run_id):
    return "{api_root}/{org_id}/{project_id}/runs/{run_id}.embed".format(**locals())


def view_instruction(api_root, org_id, project_id, run_id, instruction_id):
    return "{api_root}/{org_id}/{project_id}/runs/{run_id}/instructions/{instruction_id}.embed".format(
        **locals()
    )


def view_raw_image(api_root, data_id):
    return "{api_root}/-/{data_id}.raw".format(**locals())


def get_data_zip(api_root, data_id):
    return "{api_root}/-/{data_id}.zip".format(**locals())


def monitoring_data(
    api_root, data_type, instruction_id, grouping=None, start_time=None, end_time=None
):
    base_route = "{api_root}/sensor_data/{data_type}?instruction_id={instruction_id}".format(
        **locals()
    )
    if grouping:
        base_route += "&grouping={grouping}".format(**locals())
    if start_time:
        base_route += "&start_time={start_time}".format(**locals())
    if end_time:
        base_route += "&end_time={end_time}".format(**locals())
    return base_route


def get_payment_methods(api_root, org_id):
    return "{api_root}/{org_id}/payment_methods".format(**locals())
