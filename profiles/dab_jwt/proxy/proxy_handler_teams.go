package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"sort"
	"strconv"
	"strings"

	"github.com/google/uuid"
)

func TeamHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		getTeams(w, r)
	case http.MethodPost:
		addTeam(w, r)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func AssociateTeamUsersHandler(w http.ResponseWriter, r *http.Request) {

	teamsMutex.Lock()
	defer teamsMutex.Unlock()

	usersMutex.Lock()
	defer usersMutex.Unlock()

	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	// Extract the team_id from the URL path
	pathParts := strings.Split(r.URL.Path, "/")
	if len(pathParts) < 9 || pathParts[7] != "associate" {
		http.Error(w, "Invalid URL path", http.StatusBadRequest)
		return
	}
	teamIDStr := pathParts[5]
	teamID, _ := strconv.Atoi(teamIDStr)
	fmt.Println("teamid", teamID)

	// find the team codename ...
	var teamName = ""
	for _, team := range teams {
		fmt.Println(team)
		if team.Id == teamID {
			fmt.Println(team)
			teamName = team.Name
			break
		}
	}
	fmt.Println("teamname", teamName)

	// fmt.Println("body", r.Body)
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Failed to read request body", http.StatusInternalServerError)
		return
	}
	fmt.Println("Request Body:", string(body))
	r.Body = io.NopCloser(bytes.NewBuffer(body))

	// AssociationRequest
	var newAssociationRequest AssociationRequest
	if err := json.NewDecoder(r.Body).Decode(&newAssociationRequest); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	fmt.Println(newAssociationRequest)

	for _, uid := range newAssociationRequest.Instances {
		fmt.Println("uid", uid)
		// find this user ..
		for _, user := range users {
			if user.Id == uid {
				fmt.Println(user)
				fmt.Println(user.Teams)
				if containsString(user.Teams, teamName) == false {
					fmt.Println("add", user.Username, "to", teamName)
					user.Teams = append(user.Teams, teamName)
					users[user.Username] = user
				} else {
					fmt.Println("do not need to add", teamName, "to", user)
				}
			} else {
				fmt.Println(user.Id, "!=", uid)
			}
		}
	}

}

func getTeams(w http.ResponseWriter, r *http.Request) {
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

		var orgId = 0
		for _, org := range orgs {
			if org.CodeName == teamdata.Org {
				orgId = org.Id
				break
			}
		}

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

	if _, exists := teams[newTeamRequest.Name]; exists {
		http.Error(w, "Team already exists", http.StatusConflict)
		return
	}

	orgName := ""
	for _, org := range orgs {
		if org.Id == newTeamRequest.Organization {
			orgName = org.CodeName
			break
		}
	}
	if orgName == "" {
		http.Error(w, "Org not found", http.StatusConflict)
		return
	}

	highestId := 0
	for _, team := range teams {
		if team.Id > highestId {
			highestId = team.Id
		}
	}

	var newTeam Team

	newTeam.Name = newTeamRequest.Name
	newTeam.Id = highestId + 1
	newAnsibleID := uuid.NewString()
	newTeam.AnsibleId = newAnsibleID
	newTeam.Org = orgName
	teams[newTeam.Name] = newTeam

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

	idCounter++

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(responseTeam)
}
