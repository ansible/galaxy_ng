import argparse
import os
import django
from django.core.exceptions import AppRegistryNotReady, ImproperlyConfigured

from jinja2 import Template


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create Pulp's nginx conf file based on current settings.",
    )
    parser.add_argument("template_file", type=open)
    parser.add_argument("output_file", type=argparse.FileType("w"))
    args = parser.parse_args()

    https = os.getenv("PULP_HTTPS", "false")
    values = {
        "https": https.lower() == "true",
        "api_root": "/pulp/",
        "content_path": "/pulp/content/",
        "domain_enabled": False,
    }

    try:
        django.setup()
        from django.conf import settings
    except (AppRegistryNotReady, ImproperlyConfigured):
        print("Failed to find settings for nginx template, using defaults")
    else:
        values["api_root"] = settings.API_ROOT
        values["content_path"] = settings.CONTENT_PATH_PREFIX
        values["domain_enabled"] = getattr(settings, "DOMAIN_ENABLED", False)

    values['NGINX_PORT'] = os.environ.get('NGINX_PORT', '55001')

    template = Template(args.template_file.read())
    output = template.render(**values)
    args.output_file.write(output)
