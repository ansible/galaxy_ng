import django.core.validators
from django.db import migrations
import hashlib
import json

from django.db import migrations, models
import django.db.models.deletion

def calculate_metadata_sha256(metadata):
    """Calculates the metadata_sha256 from the other metadata fields."""
    metadata_json = json.dumps(metadata, sort_keys=True).encode("utf-8")
    hasher = hashlib.sha256(metadata_json)
    
    return hasher.hexdigest()


def add_pulp_ansible_namespace_metadata_objects(apps, schema_editor):
    """Migrate galaxy namespaces to pulp ansible namespace metadata content."""

    """
    for each namespace:
    - create AnsibleNamespaceMetadata object
        - calculate the metadata sha
    - add namespace permissions to pulp namespace obj
        - or maybe not? should we just enforce the rbac on our
          namespaces?

    Add the new namespace to the following repos:
        - published
        - should these be added to the rest?
    """

    AnsibleNamespaceMetadata = apps.get_model('ansible', 'AnsibleNamespaceMetadata')
    AnsibleNamespace = apps.get_model('ansible', 'AnsibleNamespace')
    Namespace = apps.get_model('galaxy', 'Namespace')

    # ContentType = apps.get_model("contenttypes", "ContentType")
    # GroupRole = apps.get_model("core", "GroupRole")
    # old_ns_type = ContentType.objects.get(app_label="galaxy", model="namespace")
    # new_ns_type = ContentType.objects.get(app_label="ansible", model="ansiblenamespace")


    for old_ns in Namespace.objects.all():
        new_ns = AnsibleNamespace.objects.create(name=old_ns.name)
        links = {l.name: l.url for l in old_ns.links.all()}

        metadata = {
            "company": old_ns.company,
            "email": old_ns.email,
            "description": old_ns.description,
            "resources": old_ns.resources,
            "links": links,
            "avatar_sha256": None,
        }

        # skip metadata creation for namespaces with no data.
        create_metadata = False
        for f in metadata:
            if metadata[f] not in ('', dict(), None):
                create_metadata = True
                break

        if create_metadata:
            metadata["name"] = old_ns.name
            ns_metadata = AnsibleNamespaceMetadata.objects.create(
                **{
                    **metadata,
                    "metadata_sha256": calculate_metadata_sha256(metadata),
                    "namespace": new_ns,
                    "pulp_type": "ansible.namespace",
                }
            )

            old_ns.last_created_pulp_metadata = ns_metadata
            old_ns.save

        # we'll have to handle permissions separately when we move over to the pulp ansible
        # namespaces
        # roles = GroupRole.objects.filter(object_id=old_ns.pk, content_type=old_ns_type)

        # # Migrate permissions
        # group_roles = [
        #     GroupRole(
        #         group=r.group,
        #         role=r.role,
        #         content_type=new_ns_type,
        #         object_id=new_ns.pk
        #     ) for r in roles]
        
        # GroupRole.objects.bulk_create(group_roles)


def add_namespace_metadata_to_published_repository(apps, schema_editor):
    """ Create RepositoryContent for AnsibleCollectionDeprecated."""
    AnsibleNamespaceMetadata = apps.get_model('ansible', 'AnsibleNamespaceMetadata')
    AnsibleDistribution = apps.get_model('ansible', 'AnsibleDistribution')
    RepositoryContent = apps.get_model('core', 'RepositoryContent')
    RepositoryVersion = apps.get_model('core', 'RepositoryVersion')
    RepositoryVersionContentDetails = apps.get_model('core', 'RepositoryVersionContentDetails')
    RepositoryVersionContentDetails = apps.get_model('core', 'RepositoryVersionContentDetails')
    
    repo = AnsibleDistribution.objects.get(base_path="published").repository
    repo_v = RepositoryVersion.objects.filter(repository=repo).order_by("-number").first()

    repo_content = []

    # Create RepositoryContent for namespaces
    namespaces = AnsibleNamespaceMetadata.objects.all()
    for ns in namespaces:
        repo_content.append(RepositoryContent(
                content=ns,
                repository_id=repo.pk,
                version_added=repo_v,
                repository=repo,
            ))
        if len(repo_content) >= 1024:
            RepositoryContent.objects.bulk_create(repo_content)
            repo_content.clear()
    RepositoryContent.objects.bulk_create(repo_content)
    repo_content.clear()

    # Update repository counts
    RepositoryVersionContentDetails.objects.create(
        content_type="ansible.namespace",
        repository_version=repo_v,
        count=namespaces.count(),
        count_type="A", # Added
    )

    RepositoryVersionContentDetails.objects.create(
        content_type="ansible.namespace",
        repository_version=repo_v,
        count=namespaces.count(),
        count_type="P", # Present
    )



class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0037_pulp_ansible_permissions'),
        ('ansible', '0047_ansible_namespace'),
    ]

    operations = [
        migrations.AddField(
            model_name='namespace',
            name='last_created_pulp_metadata',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='galaxy_namespace', to='ansible.ansiblenamespacemetadata'),
        ),
        migrations.RunPython(
            code=add_pulp_ansible_namespace_metadata_objects,
            reverse_code=migrations.RunPython.noop
        ),
        migrations.RunPython(
            code=add_namespace_metadata_to_published_repository,
            reverse_code=migrations.RunPython.noop
        ),
        migrations.RenameField(
            model_name='namespace',
            old_name='avatar_url',
            new_name='_avatar_url',
        ),
    ]
