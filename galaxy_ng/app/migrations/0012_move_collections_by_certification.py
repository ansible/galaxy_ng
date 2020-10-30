from django.db import migrations

MIGRATE_COLLECTIONS_QUERY = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE FUNCTION _new_repository_version(repository_id UUID) RETURNS UUID AS $$
DECLARE
    result UUID;
BEGIN
     INSERT INTO core_repositoryversion (
        pulp_id, pulp_created, pulp_last_updated, number,
        complete, base_version_id, repository_id
    ) VALUES (
        uuid_generate_v4(), now(), now(),
        (SELECT next_version FROM core_repository WHERE pulp_id = repository_id),
        TRUE, NULL, repository_id
    ) RETURNING pulp_id INTO result;

    UPDATE core_repository SET next_version = next_version + 1 WHERE pulp_id = repository_id;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION _move_collection_versions_by_certification(
    from_repo_name TEXT, to_repo_name TEXT,  filter TEXT
) RETURNS void AS
$$
DECLARE
    from_repo UUID := (
        SELECT pulp_id FROM core_repository WHERE name = from_repo_name
    );
    to_repo UUID := (
        SELECT pulp_id FROM core_repository WHERE name = to_repo_name
    );
    from_version UUID;
    to_version   UUID;
BEGIN
    IF NOT EXISTS(SELECT 1 FROM ansible_collectionversion cv WHERE cv.certification = filter) THEN
        RAISE NOTICE 'Nothing to migrate from %, to %, filter %', 
            from_repo_name, to_repo_name, filter;
        RETURN;
    END IF;

    from_version := (SELECT _new_repository_version(from_repo));
    to_version := (SELECT _new_repository_version(to_repo));

    UPDATE core_repositorycontent SET version_removed_id = from_version
    WHERE version_removed_id IS NULL AND content_id IN (
        SELECT cv.content_ptr_id
        FROM ansible_collectionversion cv
        WHERE cv.certification = filter
    );

    INSERT INTO core_repositorycontent (
        pulp_id, pulp_created, pulp_last_updated, content_id,
        repository_id, version_added_id, version_removed_id
    ) SELECT
        uuid_generate_v4(), now(), now(), cv.content_ptr_id,
        to_repo, to_version, NULL
    FROM ansible_collectionversion cv
    WHERE cv.certification = filter;

END ;
$$ LANGUAGE plpgsql;

LOCK TABLE
    core_repository,
    core_repositoryversion,
    core_repositorycontent,
    ansible_collectionversion
IN ACCESS EXCLUSIVE MODE;
    
SELECT _move_collection_versions_by_certification(
    'published', 'rejected', 'not_certified'
);
               
SELECT _move_collection_versions_by_certification(
    'published', 'staging', 'needs_review'
);

DROP FUNCTION _move_collection_versions_by_certification(TEXT, TEXT, TEXT);
DROP FUNCTION _new_repository_version(UUID);
"""


class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0011_collection_import_task_id_fk'),
    ]

    operations = [
        migrations.RunSQL(sql=MIGRATE_COLLECTIONS_QUERY, elidable=True),
    ]
