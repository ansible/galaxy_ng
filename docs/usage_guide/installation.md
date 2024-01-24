---
tags:
  - on-premise
  - tech preview
---

# How to install Galaxy NG

Galaxy NG is a [Pulp plugin](https://pulpproject.org/content-plugins/). As a plugin, Galaxy_NG has multiple installation methods available. Historically the galaxy team advocated for the [pulp_installer](https://github.com/pulp/pulp_installer) project as the best path for installation. Unfortunately the pulp-installer project is no longer being released or updated for newer pulp versions and we have to drop support for it.

We currently support 2 methods to spin up galaxy_ng

1. Pulp OCI Images with docker
2. Pulp OCI Images with [oci_env](https://github.com/pulp/oci_env) + docker


If you'd like to learn more about the oci-env path, please check the [community devstack](/galaxy_ng/community/devstack/#oci-env) page. 

The rest of this document covers using the OCI images directly with docker.

## Installing with docker and oci images

The easiest method to running galaxy_ng is through pulp's [OCI images](https://github.com/pulp/pulp-oci-images).

The full list of published images is on [quay.io](https://quay.io/repository/pulp/galaxy?tab=tags&tag=latest)

The images contain all of the software necessary to run the galaxy_ng backend, but will need some special config set to be functional. The rest of the steps in this section will explain how to create the required config and to launch a docker container.

### Defining the galaxy-importer.cfg

Create a galaxy-importer.cfg with the following content ...
```                                                                 
[galaxy-importer]                                                                                                                        
ansible_local_tmp=~/.ansible/tmp                                                                                                         
ansible_test_local_image=false                                      
check_required_tags=false                                                                                                                
check_runtime_yaml=false                                                                                                                 
check_changelog=false                                               
infra_osd=false                                                                                                                          
local_image_docker=false                                            
log_level_main=INFO                                                 
require_v1_or_greater=false                                         
run_ansible_doc=false                                               
run_ansible_lint=false                                              
run_ansible_test=false                                              
run_flake8=false                                                    
```

The galaxy-importer settings are version specific. If you plan to run an older version of galaxy-importer, you should check the source repo for the definitive list of settings available.

https://github.com/ansible/galaxy-importer/blob/master/galaxy_importer/config.py#L43-L57

If you want to run galaxy-importer standalone, check the [README.md](https://github.com/ansible/galaxy-importer/blob/master/README.md)


### Defining the pulp settings

Create a pulp_settings.env file with the following content ...
```
PULP_CONTENT_ORIGIN=http://localhost:8080
PULP_ANSIBLE_API_HOSTNAME=http://localhost:8080
PULP_GALAXY_API_PATH_PREFIX=/api/galaxy/                            
PULP_ANSIBLE_CONTENT_HOSTNAME=http://localhost:8080/pulp/content/api/galaxy/v3/artifacts/collections/
PULP_CONTENT_PATH_PREFIX=/pulp/content/api/galaxy/v3/artifacts/collections/
PULP_GALAXY_AUTHENTICATION_CLASSES=['rest_framework.authentication.SessionAuthentication', 'rest_framework.authentication.TokenAuthentication', 'rest_framework.authentication.BasicAuthentication', 'django.contrib.auth.backends.ModelBackend']
PULP_GALAXY_REQUIRE_CONTENT_APPROVAL=true
PULP_GALAXY_DEPLOYMENT_MODE=standalone                              
PULP_GALAXY_AUTO_SIGN_COLLECTIONS=false                             
PULP_GALAXY_COLLECTION_SIGNING_SERVICE=ansible-default              
PULP_RH_ENTITLEMENT_REQUIRED=insights
PULP_TOKEN_AUTH_DISABLED=false
PULP_TOKEN_SERVER=http://localhost:8080/token/                      
PULP_TOKEN_SIGNATURE_ALGORITHM=ES256
PULP_PUBLIC_KEY_PATH=/app/dev/common/container_auth_public_key.pem                
PULP_PRIVATE_KEY_PATH=/app/dev/common/container_auth_private_key.pem
PULP_ANALYTICS=false
PULP_GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS=true     
PULP_GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD=true
PULP_GALAXY_ENABLE_LEGACY_ROLES=true
PULP_GALAXY_FEATURE_FLAGS__execution_environments=false
PULP_SOCIAL_AUTH_LOGIN_REDIRECT_URL=/
PULP_GALAXY_FEATURE_FLAGS__ai_deny_index=true
PULP_DEFAULT_ADMIN_PASSWORD=password
PULP_WORKERS=1
```

Any setting containing "localhost:8080" will be environment specific. Whenever the system is spun up, the backend expects incoming and redirected requests to go to that address. This example uses "localhost:8080" because we will use docker in the next step to bind the underlying host's port 8080 to the container's port 80.

Understanding every setting in the file is beyond the scope of this document, but there are a few to highlight ...

- PULP_DEFAULT_ADMIN_PASSWORD
    - sets the http password for the "admin" user
- PULP_WORKERS
    - defines the number of asynchronous workers to run in the container
- PULP_GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS
    - allows listing collections without authentication
- PULP_GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD
    - allows downloading collections without authentication
- PULP_GALAXY_ENABLE_LEGACY_ROLES
    - enables api/v1/roles and related features

### Run docker

Start the container with these docker args ...
```
docker run \                                                        
    --name=galaxy_ng \
    -v $(pwd)/galaxy-importer.cfg:/etc/galaxy-importer/galaxy-importer.cfg
    --env-file=pulp_settings.env \
    -p 8080:80 \                                                    
    quay.io/pulp/galaxy:4.9.0 
```

The container uses the s6 init system to spin up postgresql, gunicorn, nginx and various pulp services all in the same container. Once migrations have finished and the log entries settle and end with a "New worker XXXXXX discovered", the system is ready to use.

### Using the container

##### API basics

The container should come up with a default "admin" account with a password of "password". Pass "-u admin:password" with any curl command that interacts with an endpoint that requires authentication. Many endpoints in galaxy_ng are redirects so it's best to pass "-L" to all curl commands. 

To check access to the system run this curl command ...
```
curl -u admin:password -L http://localhost:8080/api/galaxy/pulp/api/v3/status/
```

To list collections ...
```
curl -u admin:password -L http://localhost:8080/api/galaxy/v3/collections/
```
To list roles ...
```
curl -u admin:password -L http://localhost:8080/api/galaxy/v1/roles/
```

To explore other available endpoints ...
```
docker exec -it galaxy_ng pip install django-extensions
docker exec -it galaxy_ng pulpcore-manager show_urls
```
