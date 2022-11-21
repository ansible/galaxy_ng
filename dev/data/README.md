### Test fixtures

`fixture.tar.gz` is a database dump that was created using `oci-env db snapshot`. It can be restored into an oci-env environment by copying it to `OCI_ENV_PATH/db_back/fixture.tar.gz` and running `oci-env db -f fixture restore`.

To change the contents of the db backup, launch galaxy_ng in insights mode using oci-env, restore the database snapshot, run the migrations, make any changes you need (uploading new test collections, signing, deprecating etc) and then snapshot the DB again.