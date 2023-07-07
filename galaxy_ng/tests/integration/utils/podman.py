import subprocess


def ensure_test_container_is_pulled(container="alpine"):
    """
    Pulls the selected container if it doesn't already exist.
    """

    cmd = ["podman", "image", "exists", container]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode == 1:
        cmd = ["podman", "image", "pull", container]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.returncode == 0


def tag_hub_with_registry(config, src_image, dest_image):
    registry = config["container_registry"]
    dest = registry + f"/{dest_image}"
    tag_cmd = ["podman", "image", "tag", src_image, dest]
    proc = subprocess.run(tag_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    assert proc.returncode == 0

    return dest
