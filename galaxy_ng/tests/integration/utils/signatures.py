import os
import tarfile
import tempfile


def create_local_signature_for_tarball(tarball):
    """
    Sign a tarball just like PE would do for CRC.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(tarball, "r:gz") as tar:
            tar.extractall(tmpdir)
        manifest_file = os.path.join(tmpdir, "MANIFEST.json")
        signature_filename = f"{manifest_file}.asc"
        os.system(
            "gpg --batch --no-default-keyring --keyring test.kbx "
            "--import dev/common/ansible-sign.key"
        )
        os.system(f"KEYRING=test.kbx dev/common/collection_sign.sh {manifest_file}")

        with open(signature_filename, "rb") as f:
            signature_data = f.read()

    return signature_data
