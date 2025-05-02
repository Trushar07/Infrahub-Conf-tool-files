from infrahub_sdk.transforms import InfrahubTransform
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import os
import logging


class DeviceConfigTransform(InfrahubTransform):

    query = "get_conf_data"

    async def collect_data(self, params=None):
        """
        Override to process parameters before executing query.
        The params argument contains values passed on the command line.
        """
        # Process the entitlements parameter if it exists as a string
        if (
            params
            and "entitlements" in params
            and isinstance(params["entitlements"], str)
        ):
            entitlements_str = params["entitlements"]
            # Split by comma and strip whitespace
            entitlements_list = [
                e.strip() for e in entitlements_str.split(",") if e.strip()
            ]
            # Replace the string with the array in params
            params["entitlements"] = entitlements_list
            params["timestamp"] = datetime.now()  # Add timestamp to params

        # Execute the query with our processed parameters
        result = await self.client.query_gql_query(
            name=self.query, branch_name=self.branch_name, variables=params
        )

        print(result)

        return result

    async def transform(self, data):

        log = logging.getLogger("infrahub.tasks")
        log.info("This log will be captured within the task")
        # Collect data
        data = await self.collect_data()

        # Set up Jinja environment
        templates_dir = os.path.join(
            os.environ.get("INFRAHUB_HOME", "/opt/infrahub/render_configurations"),
            "templates",
        )
        env = Environment(loader=FileSystemLoader(templates_dir))

        app_name = (
            data["NetApplication"]["edges"][0]["node"]["name"]["value"]
            if data["NetApplication"]["edges"]
            else None
        )

        # Determine template path
        if not app_name:
            return "Error: Could not determine application name from query results"

        template_path = f"{app_name}/access_point.j2"

        # Load and render template
        try:
            template = env.get_template(template_path)
            print(data)
            rendered_config = template.render(data=data)
            print(rendered_config)
            return rendered_config
        except Exception as e:
            return f"Error rendering template {template_path}: {str(e)}"
