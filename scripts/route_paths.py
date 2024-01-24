#!/usr/bin/env python3

import pkgutil
import json
import re
import sys
import nginx
from pathlib import Path

nginx_configs = []

for i in pkgutil.iter_modules():
    # filter pulp and galaxy packages
    if re.search(r'pulp_.*|galaxy_ng',i.name):
        snippet_file = i.module_finder.path + "/" + i.name + "/app/webserver_snippets/nginx.conf"
        # only add the filename to array if it exists
        if Path(snippet_file).is_file():
            nginx_configs.append(snippet_file)

name = sys.argv[1]
router = []

for plugin_conf in nginx_configs:
    app = "galaxy" if "galaxy" in plugin_conf else plugin_conf.split("pulp_")[1].split("/")[0]
    conf = nginx.loadf(plugin_conf)
    for location in conf.filter("Location"):
        path = location.value
        if not path.startswith("/"):
            path = f"/{path}"
        rewrite = ""
        for key in location.keys:
            target_port = ""
            svc_name = ""
            if key.name.strip("'") == "proxy_pass":
                if "pulp-api" in key.value:
                    target_port = "api-8000"
                    svc_name = f"{name}-api-svc"
                    break
                if "pulp-content" in key.value:
                    target_port = "content-24816"
                    svc_name = f"{name}-content-svc"
                    break
            if key.name.strip("'") == "rewrite":
                rewrite = key.value.split()[1]

        if not svc_name:
            raise RuntimeError(f"Location {path} doesn't have proxy_pass")

        new_path = {
            "name":f"{name}-{app}{path.rstrip('/').replace('/', '-').replace('_', '-')}",
            "path": path,
            "targetPort": target_port,
            "serviceName": svc_name,
        }
        if rewrite:
            new_path["rewrite"] = rewrite
            router.append({
                "name":f"{name}-{app}{path.rstrip('/').replace('/', '-').replace('_', '-')}2",
                "path": path.rstrip("/"),
                "targetPort": target_port,
                "serviceName": svc_name,
                "rewrite": rewrite,
            })

        router.append(new_path)

print(json.dumps(router, indent=4))
