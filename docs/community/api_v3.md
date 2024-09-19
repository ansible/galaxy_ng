# Galaxy V3 API 

The following sections describe the API endpoints that are relevant to the Galaxy NG API.
if you have questions or looking for help please post to the [Ansible forum](https://forum.ansible.com/c/help/6)
with the appropriate tags; for example, `ansible-galaxy` or `galaxy-ng`.

## Authentication

To obtain an authentication token go to https://beta-galaxy.ansible.com/ui/token/ and click on Load Token button and copy the token provided.

!!! warning
    loading a new token will invalidate any previous loaded token. 

!!! tip
    When acessing a /pulp/ endpoint the authentication is performed by passing `Basic` authentication instead of the Token.

## Namespaces

### List namespaces 

URL:

`https://beta-galaxy.ansible.com/api/v3/namespaces/`


Parameters:

- `limit`: number of results to return
- `offset`: offset into the results
- `fields` (optional): comma separated list of fields to return
- `exclude_fields` (optional): comma separated list of fields to exclude from the response
- `company`: filter to only return namespaces with the specified company
- `name`: filter to only return namespaces with the specified name 
- `keywords`: filter to only return namespaces with the specified keywords
- `sort`: comma separated list of fields to sort the results by  
    Available values : -company, -id, -name, company, id, name

```bash
curl -X 'GET' \
  'https://beta-galaxy.ansible.com/api/v3/namespaces/?limit=2' \
  -H 'accept: application/json' \
  -H 'Authorization: Token YOURTOKEN'
```
```json
{
  "meta":{
    "count":1421
  },
  "links":{
    "first":"/api/v3/namespaces/?limit=2&offset=0",
    "previous":null,
    "next":"/api/v3/namespaces/?limit=2&offset=2",
    "last":"/api/v3/namespaces/?limit=2&offset=1419"
  },
  "data":[
    {
      "pulp_href":"/api/pulp/api/v3/pulp_ansible/namespaces/1/",
      "id":1,
      "name":"adityamulik",
      "company":"",
      "email":"",
      "avatar_url":"",
      "description":"",
      "groups":[
        
      ],
      "related_fields":{
        
      },
      "metadata_sha256":"7c7df8772e0199517e72094ea38a44ccb09864f1d47b535e13efde9388fb90eb",
      "avatar_sha256":null
    },
    {
      "pulp_href":"/api/pulp/api/v3/pulp_ansible/namespaces/2/",
      "id":2,
      "name":"ansible",
      "company":"",
      "email":"",
      "avatar_url":"",
      "description":"",
      "groups":[
        
      ],
      "related_fields":{
        
      },
      "metadata_sha256":"68073fd148635456d3810a0367602ebfcd4a6f48736c93ffdcd48777cd1e0aeb",
      "avatar_sha256":null
    }
  ]
}
```

### Get a namespace

URL:

`/api/v3/namespaces/{namespace_id}/`

```bash
curl -X 'GET' \
  'https://beta-galaxy.ansible.com/api/v3/namespaces/ansible/' \        
  -H 'accept: application/json' \
  -H 'Authorization: Token YOURTOKEN'

```
```json
{
  "pulp_href":"/api/pulp/api/v3/pulp_ansible/namespaces/2/",
  "id":2,
  "name":"ansible",
  "company":"",
  "email":"",
  "avatar_url":"",
  "description":"",
  "links":[
    
  ],
  "groups":[
    
  ],
  "resources":"",
  "related_fields":{
    
  },
  "metadata_sha256":"68073fd148635456d3810a0367602ebfcd4a6f48736c93ffdcd48777cd1e0aeb",
  "avatar_sha256":null
}
```

### Legacy Roles Namespace

URL:

`https://beta-galaxy.ansible.com/api/v1/roles/` 

```bash
curl -X 'GET' \
  'https://beta-galaxy.ansible.com/api/v1/roles/?page_size=2' \
  -H 'accept: application/json' \
  -H 'Authorization: Token YOURTOKEN'
```
```json
{
  "count":31888,
  "next":"http://beta-galaxy.ansible.com/api/v1/roles/?page=2&page_size=2",
  "previous":null,
  "results":[
    {
      "id":1,
      "upstream_id":24559,
      "created":"2023-02-06T14:33:16.015752Z",
      "modified":"2023-02-06T14:33:16.018665Z",
      "github_user":"00willo",
      "username":"00willo",
      "github_repo":"ansible-role_sublimetext",
      "github_branch":null,
      "commit":"a1c5df38855094dbd9b09e1d2f576cb4644942d3",
      "name":"sublimetext-3",
      "description":"Install Sublime Text 3 on your machine. Supports both the dev and stable release channels.",
      "summary_fields":{
        "dependencies":[
          
        ],
        "namespace":{
          "id":1,
          "name":"00willo",
          "avatar_url":"https://github.com/00willo.png"
        },
        "provider_namespace":{
          "id":1,
          "name":"00willo"
        },
        "repository":{
          "name":"sublimetext-3",
          "original_name":"ansible-role_sublimetext"
        },
        "tags":[
          "development",
          "editor",
          "ide",
          "workstation"
        ],
        "versions":[
          
        ]
      }
    },
    {
      "id":2,
      "upstream_id":48126,
      "created":"2023-02-06T14:33:16.719592Z",
      "modified":"2023-02-06T14:33:16.722476Z",
      "github_user":"030",
      "username":"030",
      "github_repo":"ansible-bfg",
      "github_branch":null,
      "commit":"18a9d15033bb5131d0133187053b49a9f207f4f0",
      "name":"ansible_bfg",
      "description":"ansible-bfg",
      "summary_fields":{
        "dependencies":[
          
        ],
        "namespace":{
          "id":2,
          "name":"030",
          "avatar_url":"https://github.com/030.png"
        },
        "provider_namespace":{
          "id":2,
          "name":"030"
        },
        "repository":{
          "name":"ansible_bfg",
          "original_name":"ansible-bfg"
        },
        "tags":[
          "bfg"
        ],
        "versions":[
          {
            "id":124481,
            "url":"",
            "name":"1.0.0",
            "active":null,
            "created":"2020-04-22T08:10:56.446123Z",
            "related":{
              
            },
            "version":"1.0.0",
            "modified":"2020-04-22T08:10:56.446146Z",
            "commit_sha":"0c1894afb716e4ce716e09834f4a49a277300ff7",
            "commit_date":"2020-04-22T03:59:00-04:00",
            "download_url":"https://github.com/030/ansible-bfg/archive/1.0.0.tar.gz",
            "summary_fields":{
              
            }
          },
          {
            "id":125411,
            "url":"",
            "name":"1.0.1",
            "active":null,
            "created":"2020-05-03T07:55:52.421610Z",
            "related":{
              
            },
            "version":"1.0.1",
            "modified":"2020-05-03T07:55:52.421636Z",
            "commit_sha":"18a9d15033bb5131d0133187053b49a9f207f4f0",
            "commit_date":"2020-05-03T03:29:17-04:00",
            "download_url":"https://github.com/030/ansible-bfg/archive/1.0.1.tar.gz",
            "summary_fields":{
              
            }
          }
        ]
      }
    }
  ]
}
```

## Collections

### List Collections

URL:

`/api/v3/plugin/ansible/content/published/collections/index/`

Parameters:

- `limit`: number of results to return
- `offset`: offset into the results
- `namespace`: filter to only return collections in the specified namespace
- `name`: filter to only return collections with the specified name
- `deprecated`: filter to only return collections that are deprecated
- `ordering`: comma separated list of fields to order the results by  
    Available values : -name, -namespace, -pk, -pulp_created, -pulp_id, -pulp_last_updated, name, namespace, pk, pulp_created, pulp_id, pulp_last_updated

```bash
curl -X 'GET' \
  'https://beta-galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections/index/?limit=2' \
  -H 'accept: application/json' \
  -H 'Authorization: Token YOURTOKEN'

```
```json
{
  "meta":{
    "count":2346
  },
  "links":{
    "first":"/api/v3/plugin/ansible/content/published/collections/index/?limit=2&offset=0",
    "previous":null,
    "next":"/api/v3/plugin/ansible/content/published/collections/index/?limit=2&offset=2",
    "last":"/api/v3/plugin/ansible/content/published/collections/index/?limit=2&offset=2344"
  },
  "data":[
    {
      "href":"/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/",
      "namespace":"namespace",
      "name":"collection_name",
      "deprecated":false,
      "versions_url":"/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/versions/",
      "highest_version":{
        "href":"/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/versions/1.0.4/",
        "version":"1.0.4"
      },
      "created_at":"2023-04-13T17:57:18.960283Z",
      "updated_at":"2023-04-13T18:10:23.981051Z"
    },
    {
      "href":"/api/v3/plugin/ansible/content/published/collections/index/namespace/nicecollection/",
      "namespace":"namespace",
      "name":"nicecollection",
      "deprecated":false,
      "versions_url":"/api/v3/plugin/ansible/content/published/collections/index/namespace/nicecollection/versions/",
      "highest_version":{
        "href":"/api/v3/plugin/ansible/content/published/collections/index/namespace/nicecollection/versions/1.0.1/",
        "version":"1.0.1"
      },
      "created_at":"2023-04-13T17:51:57.476396Z",
      "updated_at":"2023-04-13T18:10:23.981051Z"
    }
  ]
}
```

### Get a specific collection 

URL:

`/api/v3/plugin/ansible/content/published/collections/index/{namespace}/{name}/`

Parameters:

- `fields` (optional): comma separated list of fields to return
- `exclude_fields` (optional): comma separated list of fields to exclude from the response

```bash
curl -X 'GET' \
  'https://beta-galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/' \
  -H 'accept: application/json' \                                   
  -H 'Authorization: Token YOURTOKEN'

```
```json
{
  "href":"/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/",
  "namespace":"namespace",
  "name":"collection_name",
  "deprecated":false,
  "versions_url":"/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/versions/",
  "highest_version":{
    "href":"/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/versions/1.0.4/",
    "version":"1.0.4"
  },
  "created_at":"2023-04-13T17:57:18.960283Z",
  "updated_at":"2023-04-13T18:10:23.981051Z"
}
```

### List collection versions

URL:

`/api/v3/plugin/ansible/content/published/collections/index/{namespace}/{name}/versions/`

Parameters:

- `limit`: number of results to return
- `offset`: offset into the results
- `is_highest`: filter to only return the highest version of the collection
- `ordering`: comma separated list of fields to order the results by  
    Available values : -authors, -contents, -dependencies, -description, -docs_blob, -documentation, -files, -homepage, -is_highest, -issues, -license, -manifest, -name, -namespace, -pk, -pulp_created, -pulp_id, -pulp_last_updated, -pulp_type, -repository, -requires_ansible, -search_vector, -timestamp_of_interest, -upstream_id, -version, authors, contents, dependencies, description, docs_blob, documentation, files, homepage, is_highest, issues, license, manifest, name, namespace, pk, pulp_created, pulp_id, pulp_last_updated, pulp_type, repository, requires_ansible, search_vector, timestamp_of_interest, upstream_id, version
- `tags`: Commas separated list of tags to filter the results by
- `fields` (optional): comma separated list of fields to return
- `exclude_fields` (optional): comma separated list of fields to exclude from the response

```bash
curl -X 'GET' \
  'https://beta-galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/versions/?limit=2' \
  -H 'accept: application/json' \
  -H 'Authorization: Token YOURTOKEN'
```
```json
{
  "meta":{
    "count":5
  },
  "links":{
    "first":"/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/versions/?limit=2&offset=0",
    "previous":null,
    "next":"/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/versions/?limit=2&offset=2",
    "last":"/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/versions/?limit=2&offset=3"
  },
  "data":[
    {
      "version":"1.0.4",
      "href":"/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/versions/1.0.4/",
      "created_at":"2023-04-13T17:57:18.960283Z",
      "updated_at":"2023-04-13T17:57:18.960309Z",
      "requires_ansible":">=2.9.10",
      "marks":[
        
      ]
    },
    {
      "version":"1.0.3",
      "href":"/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/versions/1.0.3/",
      "created_at":"2023-04-13T17:57:18.960283Z",
      "updated_at":"2023-04-13T17:57:18.960309Z",
      "requires_ansible":">=2.9.10",
      "marks":[
        
      ]
    }
  ]
}
```
### Get a specific collection version

URL:
    
`/api/v3/plugin/ansible/content/published/collections/index/{namespace}/{name}/versions/{version}/`

Parameters:

- `fields` (optional): comma separated list of fields to return
- `exclude_fields` (optional): comma separated list of fields to exclude from the response

```bash
curl -X 'GET' \
  'https://beta-galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/versions/1.0.3/' \  
  -H 'accept: application/json' \
  -H 'Authorization: Token YOURTOKEN'
```
```json
{
  "version":"1.0.3",
  "href":"/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/versions/1.0.3/",
  "created_at":"2023-04-13T17:57:18.960283Z",
  "updated_at":"2023-04-13T17:57:18.960309Z",
  "requires_ansible":">=2.9.10",
  "marks":[
    
  ],
  "artifact":{
    "filename":"namespace-collection_name-1.0.3.tar.gz",
    "sha256":"3016ee8c1b75c7ee31fc58df757d8f349e73c0cb6af76f7279b1ffa211ede6f7",
    "size":8499
  },
  "collection":{
    "id":"80361571-1c6e-48b6-ab28-8c72ea3079cd",
    "name":"collection_name",
    "href":"/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/"
  },
  "download_url":"https://beta-galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections/artifacts/namespace-collection_name-1.0.3.tar.gz",
  "name":"collection_name",
  "namespace":{
    "name":"namespace",
    "metadata_sha256":null
  },
  "signatures":[
    
  ],
  "metadata":{
    "authors":[
      "Efsdfsd Dfgsdgdfg <sdfsdfsd@sdfsdf.com>"
    ],
    "contents":[
      {
        "name":"csv_report",
        "description":"check several objects",
        "content_type":"role"
      }
    ],
    "dependencies":{
      
    },
    "description":"some handy roles put in a collections",
    "documentation":"https://github.com/namespace/collection_name-collections/blob/main/README.md",
    "homepage":"http://example.com",
    "issues":"http://example.com/issue/tracker",
    "license":[
      "GPL-2.0-or-later"
    ],
    "repository":"https://github.com/namespace/collection_name-collections",
    "tags":[
      "tools"
    ]
  },
  "git_url":null,
  "git_commit_sha":null,
  "manifest":{
    "format":1,
    "collection_info":{
      "name":"collection_name",
      "issues":"http://example.com/issue/tracker",
      "authors":[
        "Dfsfsd Dfsfds <sdfsdf@sfsdfsdf.com>"
      ],
      "license":[
        "GPL-2.0-or-later"
      ],
      "version":"1.0.3",
      "homepage":"http://example.com",
      "namespace":"namespace",
      "repository":"https://github.com/namespace/collection_name-collections",
      "description":"some handy roles put in a collections",
      "dependencies":{
        
      },
      "documentation":"https://github.com/namespace/collection_name-collections/blob/main/README.md"
    },
    "file_manifest_file":{
      "name":"FILES.json",
      "ftype":"file",
      "format":1,
      "chksum_type":"sha256",
      "chksum_sha256":"6ca424a6dec38d47d29d4c3c9ce6ddfdd5264be5bee1687b75eeb7d12bc5bd59"
    }
  },
  "files":{
    "files":[
      {
        "name":".",
        "ftype":"dir",
        "format":1,
        "chksum_type":null,
        "chksum_sha256":null
      },
      ...
      {
        "name":"README.md",
        "ftype":"file",
        "format":1,
        "chksum_type":"sha256",
        "chksum_sha256":"a3dbdbdc6d87aa0e9c8adae5481a91588cfc7a4f8f447b871ae39993a07927f0"
      }
    ],
    "format":1
  }
}
```

### Get a specific collection version docs

URL:

`/api/v3/plugin/ansible/content/published/collections/index/{namespace}/{name}/versions/{version}/docs-blob/`

Parameters:

- `fields` (optional): comma separated list of fields to return
- `exclude_fields` (optional): comma separated list of fields to exclude from the response

```bash
 curl -X 'GET' \
  'https://beta-galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections/index/namespace/collection_name/versions/1.0.3/docs-blob/' \
  -H 'accept: application/json' \
  -H 'Authorization: Token YOURTOKEN'
```
```json
{
  "docs_blob":{
    "contents":[
      {
        "doc_strings":{
          
        },
        "readme_file":"README.md",
        "readme_html":"<h1>Role Name: LONG README TEXT....</p>",
        "content_name":"csv_report",
        "content_type":"role"
      }
    ],
    "collection_readme":{
      "html":"<h1>Ansible Collection - namespace.collection_name</h1>\n<p>Documentation for the collection.</p>",
      "name":"README.md"
    },
    "documentation_files":[
      
    ]
  }
}

```

### Delete a Collection or a specific version

!!! Warning
    This endpoint requires permission to delete the collection or version, your user 
    must be listed as the namespace owner.

URL:

`/api/v3/plugin/ansible/content/published/collections/index/{namespace}/{name}/`
`/api/v3/plugin/ansible/content/published/collections/index/{namespace}/{name}/versions/{version}/`

```bash
curl -X 'DELETE' \
'https://beta-galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections/index/mynamespace/mycollection/' \
  -H 'accept: application/json' \
  -H 'Authorization: Token YOURTOKEN'
```

!!! note
    Deleting a collection will also delete all versions of that collection, the task will succeed
    only if there are no other collection published that depends on the collection being deleted.


### Upload a collection

```bash
curl -X 'POST' \
  'http://beta-galaxy.ansible.com/api/v3/artifacts/collections/' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -H 'Authorization: Token YOURTOKEN' \
  -F 'file=@namespace-name-1.0.0.tar.gz;type=application/gzip' \
  -F 'sha256=...'
```

## More info

The complete Galaxy NG v3 API spec is available at [https://beta-galaxy.ansible.com/api/v3/swagger-ui/](https://beta-galaxy.ansible.com/api/v3/swagger-ui/), however that spec contains a lot of information that is not relevant to the Galaxy NG API.  
