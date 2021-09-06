"""
Constants to be use by testing scripts and development management commands.
"""

TEST_COLLECTION_CONFIGS = [
    {"name": "a", "namespace": "test", "dependencies": {"test.b": "*"}},
    {"name": "b", "namespace": "test", "dependencies": {"test.c": "*"}},
    {"name": "c", "namespace": "test", "dependencies": {"test.d": "*"}},
    {"name": "d", "namespace": "test"},
    {"name": "e", "namespace": "test", "dependencies": {"test.f": "*", "test.g": "*"}},
    {"name": "f", "namespace": "test", "dependencies": {"test.h": "<=3.0.0"}},
    {"name": "g", "namespace": "test", "dependencies": {"test.d": "*"}},
    {"name": "h", "namespace": "test", "version": "1.0.0"},
    {"name": "h", "namespace": "test", "version": "2.0.0"},
    {"name": "h", "namespace": "test", "version": "3.0.0"},
    {"name": "h", "namespace": "test", "version": "4.0.0"},
    {"name": "h", "namespace": "test", "version": "5.0.0"},
]
"""
TEST_COLLECTION_CONFIGS Dependency Trees:

        A               E
        |             /   \
        B            F     G
        |            |     |
        C         H(1-3)   D
        |
        D

        H has 5 versions, no dependencies


The TEST_COLLECTION_CONFIGS are used to build collections with orionutils.

ex:

    from orionutils.generator import build_collection
    collection = build_collection("skeleton", config=TEST_COLLECTION_CONFIGS)
    print(collection.filename)

"""

TAGS = [
    "system",
    "database",
    "web",
    "middleware",
    "infra",
    "linux",
    "rhel",
    "fedora",
    "cloud",
    "monitoring",
    "windows",
    "nginx_config",
    "container",
    "docker",
    "development",
    "kubernetes",
    "java",
    "python",
    "rust",
    "proxy",
]
