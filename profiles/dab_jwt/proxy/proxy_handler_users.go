package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"reflect"
	"sort"

	"github.com/google/uuid"
)

// List of allowed fields to be updated
var allowedFields = map[string]bool{
	"username":         true,
	"email":            true,
	"first_name":       true,
	"last_name":        true,
	"is_superuser":     true,
	"is_systemauditor": true,
}

func UserToResponseUser(user User) UserResponse {
	responseUser := UserResponse{
		ID:                user.Id,
		Username:          user.Username,
		FirstName:         user.FirstName,
		LastName:          user.LastName,
		Email:             user.Email,
		IsSuperUser:       user.IsSuperuser,
		IsPlatformAuditor: user.IsPlatformAuditor,
		IsSystemAuditor:   user.IsSystemAuditor,
		SummaryFields: struct {
			Resource struct {
				AnsibleID string `json:"ansible_id"`
			} `json:"resource"`
		}{Resource: struct {
			AnsibleID string `json:"ansible_id"`
		}{AnsibleID: user.Sub}},
	}
	return responseUser
}

func MeHandler(w http.ResponseWriter, r *http.Request) {
	user, error := GetRequestUser(r)
	if error != nil {
		return
	}
	responseUser := UserToResponseUser(user)
	var responseUsers []UserResponse
	responseUsers = append(responseUsers, responseUser)

	response := map[string][]UserResponse{
		"results": responseUsers,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func UserHandler(w http.ResponseWriter, r *http.Request) {
	//usersMutex.Lock()
	//defer usersMutex.Unlock()

	switch r.Method {
	case http.MethodGet:
		getUsers(w, r)
	case http.MethodPost:
		addUser(w, r)
	case http.MethodPatch:
		patchUser(w, r)
	case http.MethodPut:
		putUser(w, r)
	case http.MethodDelete:
		deleteUser(w, r)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func getUsers(w http.ResponseWriter, r *http.Request) {
	//usersMutex.Lock()
	//defer usersMutex.Unlock()

	userId := GetLastNumericPathElement(r.URL.Path)
	fmt.Printf("USERID: %d\n", userId)
	if userId > 0 {
		user := users[userId]
		responseUser := UserToResponseUser(user)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(responseUser)
		return
	}

	var userList []User
	for _, user := range users {
		userList = append(userList, user)
	}
	sort.Slice(userList, func(i, j int) bool {
		return userList[i].Id < userList[j].Id
	})

	var responseUsers []UserResponse

	for _, userdata := range userList {
		responseUser := UserToResponseUser(userdata)
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
	log.Printf("newuser -> username:%s password:%s\n", newUser.Username, newUser.Password)
	//tmpPassword := newUser.Password
	//tmpUsername := newUser.Username

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

	// FIXME - why isn't the password being saved?
	// FIXME - why is the username nulled at some point?
	/*
		newUser.Id = newId
		newUser.Username = tmpUsername
		newAnsibleID := uuid.NewString()
		newUser.Sub = newAnsibleID
		newUser.Password = tmpPassword
	*/
	createdUser := User{
		Id:        newId,
		Username:  newUser.Username,
		FirstName: newUser.FirstName,
		LastName:  newUser.LastName,
		Email:     newUser.Email,
		Password:  newUser.Password,
		Sub:       uuid.NewString(),
	}
	users[newId] = createdUser

	log.Print("---------------------------------------------")
	log.Printf("NEWUSER: %d.%s:%s\n", createdUser.Id, createdUser.Username, createdUser.Password)
	log.Print("---------------------------------------------")

	responseUser := UserToResponseUser(createdUser)

	// create the user in the downstream service index ...
	client := NewServiceIndexClient()
	payload := ServiceIndexPayload{
		AnsibleId:    createdUser.Sub,
		ServiceId:    SERVICE_ID,
		ResourceType: "shared.user",
		ResourceData: ServiceIndexResourceData{
			UserName:  createdUser.Username,
			Email:     createdUser.Email,
			FirstName: createdUser.FirstName,
			LastName:  createdUser.LastName,
			SuperUser: createdUser.IsSuperuser,
		},
	}
	ruser, _ := GetRequestUser(r)
	client.PostData(ruser, payload)

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

func patchUser(w http.ResponseWriter, r *http.Request) {
	usersMutex.Lock()
	defer usersMutex.Unlock()

	userId := GetLastNumericPathElement(r.URL.Path)

	// Check if the user exists
	_, exists := users[userId]
	if !exists {
		http.Error(w, "User not found", http.StatusNotFound)
		return
	}

	// Parse the full serialized User data from the JSON body
	var newUser User
	err := json.NewDecoder(r.Body).Decode(&newUser)
	if err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Use reflection to ensure only allowed fields are updated
	userValue := reflect.ValueOf(&newUser).Elem()
	userType := reflect.TypeOf(newUser)

	existingUser := users[userId]
	log.Printf("euser.username:%s\n", existingUser.Username)
	existingUserValue := reflect.ValueOf(&existingUser).Elem()

	for i := 0; i < userValue.NumField(); i++ {
		field := userType.Field(i)
		jsonKey := field.Tag.Get("json")
		log.Printf("process field:%s jsonKey:%s", field, jsonKey)

		// Skip updating fields that are not in the allowedFields list
		if _, ok := allowedFields[jsonKey]; !ok {
			log.Printf("skip setting %s\n", jsonKey)
			continue
		}

		newFieldValue := userValue.Field(i)
		existingFieldValue := existingUserValue.Field(i)

		// we can't allow null usernames or auth will get jacked ...
		if jsonKey == "username" && newFieldValue.Kind() == reflect.String {
			if newFieldValue.String() == "" {
				log.Printf("skip updating %s because it is empty\n", jsonKey)
				continue
			}
		}

		// Update each field that is allowed to be changed
		existingFieldValue.Set(newFieldValue)
	}

	// Save the updated user back into the users map
	users[userId] = existingUser
	responseUser := UserToResponseUser(existingUser)

	// Return the updated user as a JSON response
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(responseUser)
}

func putUser(w http.ResponseWriter, r *http.Request) {
	patchUser(w, r)
}
