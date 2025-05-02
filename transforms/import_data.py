import sys
import json
from infrahub_sdk import Config, InfrahubClientSync
from infrahub_sdk.exceptions import NodeNotFoundError, BranchNotFoundError


def get_or_create(
    client: InfrahubClientSync, kind, lookup_attrs: dict, create_attrs: dict
):
    """
    Tries to get a node of type `kind` matching `lookup_attrs`.
    If not found, creates it with `create_attrs`.
    Returns the node.
    """
    try:
        node = client.get(kind=kind, **lookup_attrs)
    except NodeNotFoundError:
        node = client.create(kind=kind, **create_attrs)
        node.save()
    return node


def main(source):
    # Read the JSON file
    with open(source, "r") as file:
        data = json.load(file)

    client = InfrahubClientSync(config=Config(username="admin", password="infrahub"))

    # get or create new branch for importing new application
    branch_name = f"import-{data['name'].replace(' ', '-')}-app"

    try:
        client.branch.get(branch_name=branch_name)
    except BranchNotFoundError:
        client.branch.create(branch_name=branch_name, sync_with_git=False)

    # Re-instantiate client on the new branch
    client = InfrahubClientSync(
        config=Config(username="admin", password="infrahub", default_branch=branch_name)
    )

    app = get_or_create(
        client,
        kind="NetApplication",
        lookup_attrs={"name__value": data["name"]},
        create_attrs={"name": data["name"], "description": data.get("description", "")},
    )

    # Bandwidths
    app.bandwidths.fetch()
    for bw in data.get("bandwidths", []):
        bw_obj = get_or_create(
            client,
            kind="NetBandwidth",
            lookup_attrs={"human_readable_name__value": bw["human_readable_name"]},
            create_attrs={
                "human_readable_name": bw["human_readable_name"],
                "value": bw["value"],
            },
        )
        app.bandwidths.add(bw_obj)
    app.save()

    # Entitlements
    app.entitlements.fetch()
    for ent in data.get("entitlements", []):
        ent_obj = get_or_create(
            client,
            kind="NetEntitlement",
            lookup_attrs={"name__value": ent},
            create_attrs={"name": ent},
        )
        app.entitlements.add(ent_obj)
    app.save()

    # Access Points
    app.access_points.fetch()
    for ap in data.get("access_points", []):
        os_type = get_or_create(
            client,
            kind="NetAccessPointOSType",
            lookup_attrs={"name__value": ap["os_type"]},
            create_attrs={"name": ap["os_type"]},
        )
        router_type = get_or_create(
            client,
            kind="NetAccessPointRouterType",
            lookup_attrs={"name__value": ap["router_type"]},
            create_attrs={"name": ap["router_type"]},
        )
        side = get_or_create(
            client,
            kind="NetSide",
            lookup_attrs={"name__value": ap["side"]},
            create_attrs={"name": ap["side"]},
        )
        ap_obj = get_or_create(
            client,
            kind="NetAccessPoint",
            lookup_attrs={"name__value": ap["name"]},
            create_attrs={
                "name": ap["name"],
                "os_type": os_type,
                "router_type": router_type,
                "side": side,
            },
        )
        app.access_points.add(ap_obj)
    app.save()

    # Environment Variables
    for ev in data.get("environment_variables", []):
        var_type = get_or_create(
            client,
            kind="NetEnvironmentVariableType",
            lookup_attrs={"name__value": ev["variable_type"]},
            create_attrs={"name": ev["variable_type"]},
        )
        ent = get_or_create(
            client,
            kind="NetEntitlement",
            lookup_attrs={"name__value": ev["entitlement"]},
            create_attrs={"name": ev["entitlement"]},
        )
        side = get_or_create(
            client,
            kind="NetSide",
            lookup_attrs={"name__value": ev["side"]},
            create_attrs={"name": ev["side"]},
        )

        ev_object = client.create(
            kind="NetEnvironmentVariable",
            data={
                "name": ev["name"],
                "value": ev["value"],
                "application": app,
                "entitlement": ent,
                "side": side,
                "variable_type": var_type,
            },
        )
        ev_object.save()

    print(f"Application {app.name} imported successfully on branch {branch_name}.")
    return app


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python import_data.py <input.json>")
        sys.exit(1)
    main(sys.argv[1])
