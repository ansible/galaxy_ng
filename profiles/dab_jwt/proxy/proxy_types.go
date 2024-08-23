package main

import (
	"fmt"
	"time"
)

// UserSession represents the user session information
type UserSession struct {
	Username  string
	CSRFToken string
	SessionID string
}

// User represents a user's information
type User struct {
	Id              int
	Username        string
	Password        string
	FirstName       string
	LastName        string
	IsSuperuser     bool
	Email           string
	Organizations   []string
	Teams           []string
	IsSystemAuditor bool
	Sub             string
}

/*
pulp-1          | {'aud': 'ansible-services',
pulp-1          |  'exp': 1718658788,
pulp-1          |  'global_roles': [],
pulp-1          |  'iss': 'ansible-issuer',
pulp-1          |  'object_roles': {'Team Member': {'content_type': 'team', 'objects': [0]}},
pulp-1          |  'objects': {'organization': [{'ansible_id': 'bc243368-a9d4-4f8f-9ffe-5d2d921fcee5',
pulp-1          |                                'name': 'Default'}],
pulp-1          |              'team': [{'ansible_id': '34a58292-1e0f-49f0-9383-fb7e63d771d9',
pulp-1          |                        'name': 'ateam',
pulp-1          |                        'org': 0}]},
pulp-1          |  'sub': '4f6499bf-3ad2-45ff-8411-0188c4f817c1',
pulp-1          |  'user_data': {'email': 'sa@localhost.com',
pulp-1          |                'first_name': 'sa',
pulp-1          |                'is_superuser': True,
pulp-1          |                'last_name': 'asdfasdf',
pulp-1          |                'username': 'superauditor'},
pulp-1          |  'version': '1'}
*/

// JWT claims
type UserClaims struct {
	Version     int                    `json:"version"`
	Iss         string                 `json:"iss"`
	Aud         string                 `json:"aud"`
	Expires     int64                  `json:"exp"`
	GlobalRoles []string               `json:"global_roles"`
	UserData    UserData               `json:"user_data"`
	Sub         string                 `json:"sub"`
	ObjectRoles map[string]interface{} `json:"object_roles"`
	Objects     map[string]interface{} `json:"objects"`
}

// Implement the jwt.Claims interface
func (c UserClaims) Valid() error {
	if time.Unix(c.Expires, 0).Before(time.Now()) {
		return fmt.Errorf("token is expired")
	}
	return nil
}

type UserData struct {
	Username    string `json:"username"`
	FirstName   string `json:"first_name"`
	LastName    string `json:"last_name"`
	IsSuperuser bool   `json:"is_superuser"`
	Email       string `json:"email"`
}

type Organization struct {
	Id        int    `json:"id"`
	AnsibleId string `json:"ansible_id"`
	Name      string `json:"name"`
	CodeName  string `json:"code_name"`
}

// for the jwt
type OrganizationObject struct {
	AnsibleId string `json:"ansible_id"`
	Name      string `json:"name"`
}

type Team struct {
	Id        int    `json:"id"`
	AnsibleId string `json:"ansible_id"`
	Name      string `json:"name"`
	Org       string `json:"org"`
}

// for the jwt
type TeamObject struct {
	AnsibleId string `json:"ansible_id"`
	Name      string `json:"name"`
	Org       int    `json:"org"`
}

type ObjectRole struct {
	ContentType string `json:"content_type"`
	Objects     []int  `json:"objects"`
}

// LoginRequest represents the login request payload
type LoginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

// LoginResponse represents the login response payload
type LoginResponse struct {
	CSRFToken string `json:"csrfToken"`
}

type OrgResponse struct {
	ID            int    `json:"id"`
	Name          string `json:"name"`
	SummaryFields struct {
		Resource struct {
			AnsibleID string `json:"ansible_id"`
		} `json:"resource"`
	} `json:"summary_fields"`
}

type TeamResponse struct {
	ID            int    `json:"id"`
	Name          string `json:"name"`
	Organization  int    `json:"organization"`
	SummaryFields struct {
		Resource struct {
			AnsibleID string `json:"ansible_id"`
		} `json:"resource"`
	} `json:"summary_fields"`
}

type UserResponse struct {
	ID            int    `json:"id"`
	Username      string `json:"username"`
	SummaryFields struct {
		Resource struct {
			AnsibleID string `json:"ansible_id"`
		} `json:"resource"`
	} `json:"summary_fields"`
}

type OrgRequest struct {
	Name string `json:"name"`
}

type TeamRequest struct {
	Name         string `json:"name"`
	Organization int    `json:"organization"`
}

type AssociationRequest struct {
	Instances []int `json:"instances"`
}

type RoleDefinition struct {
	Id          int      `json:"id"`
	Name        string   `json:"name"`
	Managed     bool     `json:"managed"`
	Permissions []string `json:"permissions"`
}

// payload for adding roledefs to users
type RoleUserAssignmentRequest struct {
	User           int `json:"user"`
	RoleDefinition int `json:"role_definition"`
	ObjectId       int `json:"object_id"`
}

// list view
type RoleUserAssignment struct {
	Id             int    `json:"id"`
	ContentType    string `json:"content_type"`
	RoleDefinition int    `json:"role_definition"`
	User           int    `json:"user"`
	ObjectId       int    `json:"object_id"`
}
