package main

var prepopulatedOrgs = map[string]Organization{
	"default": {
		Id:        1,
		AnsibleId: "bc243368-a9d4-4f8f-9ffe-5d2d921fcee0",
		Name:      "Default",
		CodeName:  "default",
	},
	"org1": {
		Id:        2,
		AnsibleId: "bc243368-a9d4-4f8f-9ffe-5d2d921fcee1",
		Name:      "Organization 1",
		CodeName:  "org1",
	},
	"org2": {
		Id:        3,
		AnsibleId: "bc243368-a9d4-4f8f-9ffe-5d2d921fcee2",
		Name:      "Organization 2",
		CodeName:  "org2",
	},
	"pe": {
		Id:        4,
		AnsibleId: "bc243368-a9d4-4f8f-9ffe-5d2d921fcee3",
		Name:      "system:partner-engineers",
		CodeName:  "pe",
	},
}

var prepopulatedTeams = map[string]Team{
	"ateam": {
		Id:        1,
		AnsibleId: "34a58292-1e0f-49f0-9383-fb7e63d771aa",
		Name:      "ateam",
		Org:       2,
	},
	"bteam": {
		Id:        2,
		AnsibleId: "34a58292-1e0f-49f0-9383-fb7e63d771ab",
		Name:      "bteam",
		Org:       1,
	},
	"peteam": {
		Id:        3,
		AnsibleId: "34a58292-1e0f-49f0-9383-fb7e63d771ac",
		Name:      "peteam",
		Org:       4,
	},
}

// Define users
var prepopulatedUsers = map[string]User{
	"admin": {
		Id:              1,
		Username:        "admin",
		Password:        "admin",
		FirstName:       "ad",
		LastName:        "min",
		IsSuperuser:     true,
		Email:           "admin@example.com",
		Organizations:   []string{"default"},
		Teams:           []string{},
		IsSystemAuditor: true,
		Sub:             "bc243368-a9d4-4f8f-9ffe-5d2d921fce99",
	},
	"notifications_admin": {
		Id:              2,
		Username:        "notifications_admin",
		Password:        "redhat",
		FirstName:       "notifications",
		LastName:        "admin",
		IsSuperuser:     true,
		Email:           "notifications_admin@example.com",
		Organizations:   []string{"default"},
		Teams:           []string{},
		IsSystemAuditor: true,
		Sub:             "bc243368-a9d4-4f8f-9ffe-5d2d921fce98",
	},
	"ee_admin": {
		Id:              3,
		Username:        "ee_admin",
		Password:        "redhat",
		FirstName:       "ee",
		LastName:        "admin",
		IsSuperuser:     true,
		Email:           "ee_admin@example.com",
		Organizations:   []string{"default"},
		Teams:           []string{},
		IsSystemAuditor: true,
		Sub:             "bc243368-a9d4-4f8f-9ffe-5d2d921fce97",
	},
	"jdoe": {
		Id:        4,
		Username:  "jdoe",
		Password:  "redhat",
		FirstName: "John",
		LastName:  "Doe",
		//IsSuperuser: false,
		IsSuperuser: true,
		Email:       "john.doe@example.com",
		Organizations: []string{
			"default",
			"org1",
			"org2",
			"pe",
		},
		Teams:           []string{"peteam"},
		IsSystemAuditor: false,
		Sub:             "bc243368-a9d4-4f8f-9ffe-5d2d921fce96",
	},
	"iqe_normal_user": {
		Id:          5,
		Username:    "iqe_normal_user",
		Password:    "redhat",
		FirstName:   "iqe",
		LastName:    "normal_user",
		IsSuperuser: false,
		Email:       "iqe_normal_user@example.com",
		Organizations: []string{
			"default",
			"org1",
			"org2",
		},
		//Teams:           []string{"ateam", "bteam"},
		//Teams:           []string{"bteam"},
		Teams:           []string{},
		IsSystemAuditor: false,
		Sub:             "bc243368-a9d4-4f8f-9ffe-5d2d921fce95",
	},
}

var prepopulatedRoleDefinitions = []RoleDefinition{
	{
		Id:      1,
		Name:    "Platform Auditor",
		Managed: true,
		Permissions: []string{
			"shared.view_organization",
			"shared.view_team",
		},
	},
	{
		Id:      2,
		Name:    "Team Member",
		Managed: false,
		Permissions: []string{
			"shared.member_team",
			"shared.view_team",
		},
	},
	{
		Id:      3,
		Name:    "Team Admin",
		Managed: false,
		Permissions: []string{
			"shared.change_team",
			"shared.delete_team",
			"shared.member_team",
			"shared.view_team",
		},
	},
	{
		Id:      4,
		Name:    "Organization Admin",
		Managed: true,
		Permissions: []string{
			"shared.change_organization",
			"shared.delete_organization",
			"shared.member_organization",
			"shared.view_organization",
			"shared.add_team",
			"shared.change_team",
			"shared.delete_team",
			"shared.member_team",
			"shared.view_team",
		},
	},
	{
		Id:      5,
		Name:    "Organization Member",
		Managed: true,
		Permissions: []string{
			"shared.member_organization",
			"shared.view_organization",
		},
	},
}
