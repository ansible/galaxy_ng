package main

import (
	"encoding/json"
	"log"
	"net/http"
)

func RoleDefinitionsHandler(w http.ResponseWriter, r *http.Request) {
	roleDefinitionsMutex.Lock()
	defer roleDefinitionsMutex.Unlock()

	results := []RoleDefinition{}
	for _, roledef := range roleDefinitions {
		results = append(results, roledef)
	}
	response := map[string][]RoleDefinition{
		"results": results,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func RoleUserAssignmentsHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		getRoleUserAssignments(w)
	case http.MethodPost:
		addRoleUserAssignments(w, r)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func getRoleUserAssignments(w http.ResponseWriter) {
	roleUserAssignmentsMutex.Lock()
	defer roleUserAssignmentsMutex.Unlock()

	results := []RoleUserAssignment{}
	for _, assignment := range roleUserAssignments {
		results = append(results, assignment)
	}
	response := map[string][]RoleUserAssignment{
		"results": results,
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func addRoleUserAssignments(w http.ResponseWriter, r *http.Request) {
	roleUserAssignmentsMutex.Lock()
	defer roleUserAssignmentsMutex.Unlock()

	var newAssignment RoleUserAssignmentRequest
	if err := json.NewDecoder(r.Body).Decode(&newAssignment); err != nil {
		log.Printf("%\n", err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	keys := []int{}
	for key := range roleUserAssignments {
		keys = append(keys, key)
	}
	for key := range deletedEntities {
		if key.ContentType != "role_user_assignment" {
			continue
		}
		keys = append(keys, key.ID)
	}
	highestId := MaxOrDefault(keys)
	newId := highestId + 1

	newUserAssignment := RoleUserAssignment{
		Id:             newId,
		RoleDefinition: newAssignment.RoleDefinition,
		User:           newAssignment.User,
		ObjectId:       newAssignment.ObjectId,
	}
	roleUserAssignments[newId] = newUserAssignment

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(newUserAssignment)
}
