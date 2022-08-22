import random
from argparse import ArgumentError
from collections import defaultdict
from functools import lru_cache

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls.base import reverse
from rest_framework.test import APIClient

from galaxy_ng.app.constants import INBOUND_REPO_NAME_FORMAT
from galaxy_ng.app.models.auth import Group, User
from galaxy_ng.app.models.namespace import Namespace, create_inbound_repo
from galaxy_ng.tests.constants import TAGS, TEST_COLLECTION_CONFIGS

STRATEGIES = ["test", "faux"]


def valid_prefix(prefix):
    if prefix and prefix[0].isdigit():
        raise CommandError("Prefix cannot start with a number")
    return prefix


class Command(BaseCommand):
    """Django management command to feed the system with testing collections
    Those collections are meant for testing only.
    namespace defaults to 'test'
    """

    def add_arguments(self, parser):
        parser.add_argument("--namespace", help="namespace name")
        parser.add_argument(
            "--strategy",
            help="generation stategy to call",
            type=str,
            default="faux",
            required=False,
            choices=STRATEGIES,
        )
        parser.add_argument(
            "-n",
            "--ns",
            help="number of namespaces to generate",
            required=False,
            type=int,
            default=21,  # 21 is good for pagination testing
        )
        parser.add_argument(
            "-c",
            "--cols",
            help="number of collections to generate",
            required=False,
            type=int,
            default=21,  # 21 is good for pagination testing
        )
        parser.add_argument(
            "-p",
            "--prefix",
            help="prefix for namespaces and collections",
            required=False,
            type=valid_prefix,
            default="",
        )
        parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            help="don't ask confirmation",
            default=False,
            required=False,
        )

    def echo(self, message):
        self.stdout.write(self.style.SUCCESS(message))

    @property
    def generator(self):
        """Imports on demand, avoids import error when dep not installed"""
        if not hasattr(self, "_generator"):
            from orionutils import generator  # noqa

            self._generator = generator
        return self._generator

    @property
    def faux(self):
        """Imports on demand, avoids import error when dep not installed"""
        if not hasattr(self, "_faux"):
            import fauxfactory  # noqa

            self._faux = fauxfactory
        return self._faux

    def handle(self, *args, **options):
        """Handle command"""

        if options.get("strategy") == "test":
            total = len(TEST_COLLECTION_CONFIGS)
        else:
            total = options["cols"] * options["ns"]

        if not options["yes"]:
            confirm = input(
                f"You are about to populate the system with {total} test collections.\n"
                "This operation cannot be undone\n"
                "Proceed? (Y/n)"
            ).lower()
            while 1:
                if confirm not in ("y", "n", "yes", "no"):
                    confirm = input('Please enter either "y/yes" or "n/no": ')
                    continue
                if confirm in ("y", "yes"):
                    break
                else:
                    self.echo("Process canceled.")
                    return

        self.client = APIClient()
        self.admin_user = User.objects.get(username="admin")
        self.client.force_authenticate(user=self.admin_user)
        self.prefix = options["prefix"].lower()
        self.strategy = options.get("strategy")
        getattr(self, f"strategy_{self.strategy}", self.raise_for_strategy)(*args, **options)

    def upload_collection(self, filename):
        collection_upload_url = reverse(
            "galaxy:api:v3:collection-artifact-upload",
        )
        return self.client.post(collection_upload_url, {"file": open(filename, "rb")})

    def raise_for_strategy(self, *args, **kwargs):
        """No strategy, no action"""
        raise ArgumentError("Selected strategy doen't exist")

    @lru_cache(maxsize=None)
    def create_namespace(self, namespace_name, groups=None):
        namespace_name = f"{self.prefix}{namespace_name}".lower()
        np, _ = Namespace.objects.get_or_create(name=namespace_name)
        if not np.groups:
            if groups:
                np.groups = groups
            else:
                pe = Group.objects.get(name="system:partner-engineers")
                np.groups = {
                    pe: [
                        "galaxy.collection_admin"
                    ]
                }
            np.save()
        self.echo(f"Created namespace {namespace_name}")
        self.echo(reverse("galaxy:api:v3:namespaces-detail", kwargs={"name": namespace_name}))

        return np

    def apply_prefix(self, config):
        """Apply a prefix to a config"""
        if self.prefix and self.prefix != "":
            for key in ["namespace", "name"]:
                if not config[key].startswith(self.prefix):
                    config[key] = f"{self.prefix}{config[key]}".lower()
        return config

    def build_collection(self, template, config):
        """Build a collection from a template and a config"""
        return self.generator.build_collection(template, config=config)

    def gen_version(self):
        x = random.randint(0, 3)
        y = random.randint(1, 9)
        z = random.randint(0, 9)
        return f"{x}.{y}.{z}"

    def apply_dep_prefix(self, dep, np):
        _, col = dep.split(".")
        collection_name = f"{self.prefix}{col}"
        return f"{np.name}.{collection_name}"

    def strategy_test(self, *args, **options):
        """Use constants.TEST_COLLECTION_CONFIGS to generate collections"""
        for config in TEST_COLLECTION_CONFIGS:
            namespace_name = config["namespace"]
            create_inbound_repo(namespace_name)
            np = self.create_namespace(namespace_name)
            config["namespace"] = np.name

            if settings.GALAXY_REQUIRE_CONTENT_APPROVAL:
                distro = INBOUND_REPO_NAME_FORMAT.format(namespace_name=np.name)
            else:
                distro = "published"

            _new_deps = {}
            if config.get("dependencies"):
                _new_deps = {
                    self.apply_dep_prefix(key, np): value
                    for key, value in config["dependencies"].items()
                }

            if _new_deps:
                config["dependencies"] = _new_deps

            config = self.apply_prefix(config)
            collection = self.build_collection("skeleton", config=config)
            response = self.upload_collection(collection.filename)

            self.echo(response.status_code)
            self.echo(response.data)
            self.echo(f"Collection '{collection.name}' created")
            if config.get("dependencies"):
                self.echo(f"Dependencies: {collection.name} depends on {config['dependencies']}")
            else:
                self.echo("No dependencies")
            self.echo(
                reverse(
                    "galaxy:api:v3:collection-versions-detail",
                    kwargs={
                        "distro_base_path": distro,
                        "namespace": np.name,
                        "name": collection.name,
                        "version": collection.version,
                    },
                )
            )

    def strategy_faux(self, *args, **options):
        """Use fauxfactory to generate"""
        _configs = defaultdict(list)
        _dependency_pool = []
        for _ in range(options["ns"]):
            namespace_name = self.faux.gen_string(
                "alpha",
                8,
                validator=lambda v: v not in _configs,
                tries=100,
                default=self.faux.gen_string("alpha", 8),
            ).lower()
            create_inbound_repo(namespace_name)
            np = self.create_namespace(namespace_name)
            _collections = []

            if settings.GALAXY_REQUIRE_CONTENT_APPROVAL:
                distro = INBOUND_REPO_NAME_FORMAT.format(namespace_name=namespace_name)
            else:
                distro = "published"

            for i in range(options["cols"]):
                config = {
                    "name": self.faux.gen_string(
                        "alpha",
                        10,
                        validator=lambda v: v not in _collections,
                        tries=100,
                        default=self.faux.gen_string("alpha", 10),
                    ).lower(),
                    "description": self.faux.gen_iplum(words=8),
                    "namespace": np.name,
                    "version": self.gen_version(),
                    "tags": random.sample(TAGS, 3),
                }

                if i > 2:
                    deps = random.sample(_dependency_pool, random.randint(1, 3))
                    config["dependencies"] = dict(deps)

                _collections.append(config["name"])
                _configs[namespace_name].append(config)

                config = self.apply_prefix(config)
                collection = self.build_collection("skeleton", config=config)
                response = self.upload_collection(collection.filename)
                self.echo(response.status_code)
                self.echo(response.data)
                self.echo(f"Collection '{collection.name}' created")
                if config.get("dependencies"):
                    self.echo(
                        f"Dependencies: {collection.name} depends on {config['dependencies']}"
                    )
                else:
                    self.echo("No dependencies")
                self.echo(
                    reverse(
                        "galaxy:api:v3:collection-versions-detail",
                        kwargs={
                            "distro_base_path": distro,
                            "namespace": np.name,
                            "name": config["name"],
                            "version": config["version"],
                        },
                    )
                )

                if i <= 2:
                    _config = config.copy()
                    x, y, z = config["version"].split(".")
                    _config["version"] = f"{x}.{y}.{int(z) + 1}"
                    _config = self.apply_prefix(_config)
                    _collection = self.build_collection("skeleton", config=_config)
                    _response = self.upload_collection(_collection.filename)
                    self.echo(_response.status_code)
                    self.echo(_response.data)
                    self.echo(f"A new version for '{_collection.name}' created")
                    self.echo(
                        reverse(
                            "galaxy:api:v3:collection-versions-detail",
                            kwargs={
                                "distro_base_path": distro,
                                "namespace": np.name,
                                "name": _config["name"],
                                "version": _config["version"],
                            },
                        )
                    )

                    # add as a dependency to the next collection
                    spec = random.choice(["==", ">=", "<="])
                    _dependency_pool.append(
                        (f"{config['namespace']}.{config['name']}", f"{spec}{config['version']}")
                    )
                    _spec = random.choice(["==", ">=", "<="])
                    _dependency_pool.append(
                        (f"{config['namespace']}.{config['name']}", f"{_spec}{_config['version']}")
                    )
