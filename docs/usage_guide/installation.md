---
tags:
  - on-premise
  - tech preview
---

# How to install Galaxy NG

Galaxy NG is a Pulp plugin ...

## Installing from source using pulp-installer

The [pulp_installer](https://github.com/pulp/pulp_installer) project is no longer being released. The galaxy dev team no longer validates this install method.


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
PULP_PUBLIC_KEY_PATH=/src/galaxy_ng/dev/common/container_auth_public_key.pem                
PULP_PRIVATE_KEY_PATH=/src/galaxy_ng/dev/common/container_auth_private_key.pem                                                           
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

### Run docker

Start the container with these docker args ...
```
docker run \                                                        
    -v $(pwd)/galaxy-importer.cfg:/etc/galaxy-importer/galaxy-importer.cfg
    --env-file=pulp_settings.env \
    -p 8080:80 \                                                    
    quay.io/pulp/galaxy:4.9.0 
```
