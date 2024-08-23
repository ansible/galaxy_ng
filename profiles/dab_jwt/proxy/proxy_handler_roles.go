package main

import (
	"encoding/json"
	"log"
	"net/http"
)

func RoleDefinitionsHandler(w http.ResponseWriter, r *http.Request) {
	roleDefinitionsMutex.Lock()
	defer roleDefinitionsMutex.Unlock()

	response := map[string][]RoleDefinition{
		"results": roleDefinitions,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func RoleUserAssignmentsHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		getRoleUserAssignments(w, r)
	case http.MethodPost:
		addRoleUserAssignments(w, r)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func getRoleUserAssignments(w http.ResponseWriter, r *http.Request) {
	roleUserAssignmentsMutex.Lock()
	defer roleUserAssignmentsMutex.Unlock()

	response := map[string][]RoleUserAssignment{
		"results": roleUserAssignments,
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

	newId := len(roleUserAssignments) + 1
	//log.Printf("NEWID:%d\n", newId)

	newUserAssignment := RoleUserAssignment{
		Id:             newId,
		RoleDefinition: newAssignment.RoleDefinition,
		User:           newAssignment.User,
		ObjectId:       newAssignment.ObjectId,
	}
	roleUserAssignments = append(roleUserAssignments, newUserAssignment)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(newUserAssignment)
}
