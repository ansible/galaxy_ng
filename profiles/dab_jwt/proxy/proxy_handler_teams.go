package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"sort"

	"github.com/google/uuid"
)

func TeamHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		getTeams(w)
	case http.MethodPost:
		addTeam(w, r)
	case http.MethodDelete:
		deleteTeam(w, r)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func getTeams(w http.ResponseWriter) {
	teamsMutex.Lock()
	defer teamsMutex.Unlock()

	orgsMutex.Lock()
	defer orgsMutex.Unlock()

	var teamList []Team
	for _, team := range teams {
		teamList = append(teamList, team)
	}
	sort.Slice(teamList, func(i, j int) bool {
		return teamList[i].Id < teamList[j].Id
	})

	var responseTeams []TeamResponse

	for _, teamdata := range teamList {

		var orgId = teamdata.Org
		/*
			for _, org := range orgs {
				if org.CodeName == teamdata.Org {
					orgId = org.Id
					break
				}
			}
		*/

		responseTeam := TeamResponse{
			ID:           teamdata.Id,
			Name:         teamdata.Name,
			Organization: orgId,
			SummaryFields: struct {
				Resource struct {
					AnsibleID string `json:"ansible_id"`
				} `json:"resource"`
			}{Resource: struct {
				AnsibleID string `json:"ansible_id"`
			}{AnsibleID: teamdata.AnsibleId}},
		}
		responseTeams = append(responseTeams, responseTeam)
	}

	response := map[string][]TeamResponse{
		"results": responseTeams,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func addTeam(w http.ResponseWriter, r *http.Request) {

	// fmt.Println("body", r.Body)
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Failed to read request body", http.StatusInternalServerError)
		return
	}
	fmt.Println("Request Body:", string(body))
	r.Body = io.NopCloser(bytes.NewBuffer(body))

	var newTeamRequest TeamRequest
	if err := json.NewDecoder(r.Body).Decode(&newTeamRequest); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if newTeamRequest.Name == "" {
		http.Error(w, "Team name can not be blank", http.StatusConflict)
		return
	}

	orgsMutex.Lock()
	defer orgsMutex.Unlock()

	teamsMutex.Lock()
	defer teamsMutex.Unlock()

	checkTeam := GetTeamByName(newTeamRequest.Name)
	if checkTeam.Name == newTeamRequest.Name {
		http.Error(w, "Team already exists", http.StatusConflict)
		return
	}

	keys := []int{}
	for key := range teams {
		keys = append(keys, key)
	}
	for key := range deletedEntities {
		if key.ContentType != "team" {
			continue
		}
		keys = append(keys, key.ID)
	}
	highestId := MaxOrDefault(keys)
	newId := highestId + 1

	var newTeam Team

	newTeam.Name = newTeamRequest.Name
	newTeam.Id = newId
	newAnsibleID := uuid.NewString()
	newTeam.AnsibleId = newAnsibleID
	newTeam.Org = newTeamRequest.Organization
	teams[newTeam.Id] = newTeam

	responseTeam := TeamResponse{
		ID:           newTeam.Id,
		Name:         newTeam.Name,
		Organization: newTeamRequest.Organization,
		SummaryFields: struct {
			Resource struct {
				AnsibleID string `json:"ansible_id"`
			} `json:"resource"`
		}{Resource: struct {
			AnsibleID string `json:"ansible_id"`
		}{AnsibleID: newAnsibleID}},
	}

	// create the team in the downstream service index ...
	org := orgs[newTeamRequest.Organization]
	client := NewServiceIndexClient()
	payload := ServiceIndexPayload{
		AnsibleId:    newTeam.AnsibleId,
		ServiceId:    SERVICE_ID,
		ResourceType: "shared.team",
		ResourceData: ServiceIndexResourceData{
			Name:         newTeam.Name,
			Organization: &org.AnsibleId,
			Description:  "",
		},
	}
	user, _ := GetRequestUser(r)
	client.PostData(user, payload)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(responseTeam)
}

func deleteTeam(w http.ResponseWriter, r *http.Request) {

	orgsMutex.Lock()
	defer orgsMutex.Unlock()

	teamsMutex.Lock()
	defer teamsMutex.Unlock()

	roleUserAssignmentsMutex.Lock()
	defer roleUserAssignmentsMutex.Unlock()

	deletedEntitiesMutex.Lock()
	defer deletedEntitiesMutex.Unlock()

	teamId := GetLastNumericPathElement(r.URL.Path)
	team := teams[teamId]

	// delete org last
	ansibleId := team.AnsibleId
	DeleteTeam(team)

	// Perform any additional cleanup or API calls
	user, _ := GetRequestUser(r)
	client := NewServiceIndexClient()
	if err := client.Delete(user, ansibleId); err != nil {
		log.Printf("Failed to notify Service Index Client: %v", err)
	}

	// Respond with success
	w.WriteHeader(http.StatusNoContent)
}
