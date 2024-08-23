package main

import (
	"encoding/json"
	"log"
	"net/http"
	"sort"

	"github.com/google/uuid"
)

func UserHandler(w http.ResponseWriter, r *http.Request) {
	//usersMutex.Lock()
	//defer usersMutex.Unlock()

	switch r.Method {
	case http.MethodGet:
		getUsers(w)
	case http.MethodPost:
		addUser(w, r)
	case http.MethodDelete:
		deleteUser(w, r)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func getUsers(w http.ResponseWriter) {
	//usersMutex.Lock()
	//defer usersMutex.Unlock()

	var userList []User
	for _, user := range users {
		userList = append(userList, user)
	}
	sort.Slice(userList, func(i, j int) bool {
		return userList[i].Id < userList[j].Id
	})

	var responseUsers []UserResponse

	for _, userdata := range userList {
		responseUser := UserResponse{
			ID:       userdata.Id,
			Username: userdata.Username,
			SummaryFields: struct {
				Resource struct {
					AnsibleID string `json:"ansible_id"`
				} `json:"resource"`
			}{Resource: struct {
				AnsibleID string `json:"ansible_id"`
			}{AnsibleID: userdata.Sub}},
		}
		responseUsers = append(responseUsers, responseUser)
	}

	response := map[string][]UserResponse{
		"results": responseUsers,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func addUser(w http.ResponseWriter, r *http.Request) {
	/*
		# PAYLOAD
		{"username": "foo", "password": "redhat1234"}

		# RESPONSE
		{
			"id":96,
			"url":"/api/gateway/v1/users/96/",
			"related":{
				"personal_tokens":"/api/gateway/v1/users/96/personal_tokens/",
				"authorized_tokens":"/api/gateway/v1/users/96/authorized_tokens/",
				"tokens":"/api/gateway/v1/users/96/tokens/",
				"activity_stream":"/api/gateway/v1/activitystream/?content_type=1&object_id=96",
				"created_by":"/api/gateway/v1/users/6/",
				"modified_by":"/api/gateway/v1/users/6/",
				"authenticators":"/api/gateway/v1/users/96/authenticators/"
			},
			"summary_fields":{
				"modified_by":{"id":6,"username":"dev","first_name":"","last_name":""},
				"created_by":{"id":6,"username":"dev","first_name":"","last_name":""},
				"resource":{"ansible_id":"5fc36ea7-5c54-4f12-b47c-5213d648b2c0","resource_type":"shared.user"}
			},
			"created":"2024-07-31T02:20:31.734404Z",
			"created_by":6,
			"modified":"2024-07-31T02:20:31.734386Z",
			"modified_by":6,
			"username":"foo",
			"email":"",
			"first_name":"",
			"last_name":"",
			"last_login":null,
			"password":"$encrypted$",
			"is_superuser":false,
			"is_platform_auditor":false,
			"managed":false,
			"last_login_results":{},
			"authenticators":[],
			"authenticator_uid":""
		}
	*/

	usersMutex.Lock()
	defer usersMutex.Unlock()

	var newUser User
	if err := json.NewDecoder(r.Body).Decode(&newUser); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if newUser.Username == "" {
		http.Error(w, "username can not be blank.", http.StatusBadRequest)
		return
	}

	//usersMutex.Lock()
	//defer usersMutex.Unlock()

	checkUser := GetUserByUserName(newUser.Username)
	if checkUser.Username == newUser.Username {
		http.Error(w, "User already exists", http.StatusConflict)
		return
	}

	keys := []int{}
	for key := range users {
		keys = append(keys, key)
	}
	for key := range deletedEntities {
		if key.ContentType != "user" {
			continue
		}
		keys = append(keys, key.ID)
	}
	highestId := MaxOrDefault(keys)
	newId := highestId + 1

	newUser.Id = newId
	newAnsibleID := uuid.NewString()
	newUser.Sub = newAnsibleID
	users[newUser.Id] = newUser

	responseUser := UserResponse{
		ID:       newUser.Id,
		Username: newUser.Username,
		SummaryFields: struct {
			Resource struct {
				AnsibleID string `json:"ansible_id"`
			} `json:"resource"`
		}{Resource: struct {
			AnsibleID string `json:"ansible_id"`
		}{AnsibleID: newAnsibleID}},
	}

	// create the team in the downstream service index ...
	client := NewServiceIndexClient()
	payload := ServiceIndexPayload{
		AnsibleId:    newUser.Sub,
		ServiceId:    SERVICE_ID,
		ResourceType: "shared.user",
		ResourceData: ServiceIndexResourceData{
			UserName:  newUser.Username,
			Email:     newUser.Email,
			FirstName: newUser.FirstName,
			LastName:  newUser.LastName,
			SuperUser: newUser.IsSuperuser,
		},
	}
	user, _ := GetRequestUser(r)
	client.PostData(user, payload)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(responseUser)
}

func deleteUser(w http.ResponseWriter, r *http.Request) {

	orgsMutex.Lock()
	defer orgsMutex.Unlock()

	teamsMutex.Lock()
	defer teamsMutex.Unlock()

	roleUserAssignmentsMutex.Lock()
	defer roleUserAssignmentsMutex.Unlock()

	deletedEntitiesMutex.Lock()
	defer deletedEntitiesMutex.Unlock()

	userId := GetLastNumericPathElement(r.URL.Path)
	user := users[userId]

	ansibleId := user.Sub
	DeleteUser(user)

	// Perform any additional cleanup or API calls
	ruser, _ := GetRequestUser(r)
	client := NewServiceIndexClient()
	if err := client.Delete(ruser, ansibleId); err != nil {
		log.Printf("Failed to notify Service Index Client: %v", err)
	}

	// Respond with success
	w.WriteHeader(http.StatusNoContent)
}
