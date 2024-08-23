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

func OrganizationHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		getOrgs(w)
	case http.MethodPost:
		addOrg(w, r)
	case http.MethodDelete:
		deleteOrg(w, r)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func getOrgs(w http.ResponseWriter) {
	orgsMutex.Lock()
	defer orgsMutex.Unlock()

	var orgList []Organization
	for _, org := range orgs {
		orgList = append(orgList, org)
	}
	sort.Slice(orgList, func(i, j int) bool {
		return orgList[i].Id < orgList[j].Id
	})

	var responseOrgs []OrgResponse

	for _, orgdata := range orgList {
		responseOrg := OrgResponse{
			ID:   orgdata.Id,
			Name: orgdata.Name,
			SummaryFields: struct {
				Resource struct {
					AnsibleID string `json:"ansible_id"`
				} `json:"resource"`
			}{Resource: struct {
				AnsibleID string `json:"ansible_id"`
			}{AnsibleID: orgdata.AnsibleId}},
		}
		responseOrgs = append(responseOrgs, responseOrg)
	}

	response := map[string][]OrgResponse{
		"results": responseOrgs,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func addOrg(w http.ResponseWriter, r *http.Request) {
	// fmt.Println("body", r.Body)
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Failed to read request body", http.StatusInternalServerError)
		return
	}
	fmt.Println("Request Body:", string(body))
	r.Body = io.NopCloser(bytes.NewBuffer(body))

	var newOrgRequest OrgRequest
	if err := json.NewDecoder(r.Body).Decode(&newOrgRequest); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if newOrgRequest.Name == "" {
		http.Error(w, "Org name can not be blank", http.StatusConflict)
		return
	}

	orgsMutex.Lock()
	defer orgsMutex.Unlock()

	for _, org := range orgs {
		if org.Name == newOrgRequest.Name || org.CodeName == newOrgRequest.Name {
			http.Error(w, "org name is already taken", http.StatusBadRequest)
			return
		}
	}

	keys := []int{}
	for key := range orgs {
		keys = append(keys, key)
	}
	for key := range deletedEntities {
		if key.ContentType != "org" {
			continue
		}
		keys = append(keys, key.ID)
	}
	highestId := MaxOrDefault(keys)
	newId := highestId + 1

	var newOrg Organization

	newOrg.CodeName = newOrgRequest.Name
	newOrg.Name = newOrgRequest.Name
	newOrg.Id = newId
	newAnsibleID := uuid.NewString()
	newOrg.AnsibleId = newAnsibleID
	orgs[newOrg.Id] = newOrg

	fmt.Println(newOrg)

	responseOrg := OrgResponse{
		ID:   newOrg.Id,
		Name: newOrg.Name,
		SummaryFields: struct {
			Resource struct {
				AnsibleID string `json:"ansible_id"`
			} `json:"resource"`
		}{Resource: struct {
			AnsibleID string `json:"ansible_id"`
		}{AnsibleID: newOrg.AnsibleId}},
	}

	// create the org in the downstream service index ...
	client := NewServiceIndexClient()
	payload := ServiceIndexPayload{
		AnsibleId:    newOrg.AnsibleId,
		ServiceId:    SERVICE_ID,
		ResourceType: "shared.organization",
		ResourceData: ServiceIndexResourceData{
			Name:        newOrg.Name,
			Description: "",
		},
	}
	user, _ := GetRequestUser(r)
	client.PostData(user, payload)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(responseOrg)
}

func deleteOrg(w http.ResponseWriter, r *http.Request) {

	orgsMutex.Lock()
	defer orgsMutex.Unlock()

	teamsMutex.Lock()
	defer teamsMutex.Unlock()

	roleUserAssignmentsMutex.Lock()
	defer roleUserAssignmentsMutex.Unlock()

	deletedEntitiesMutex.Lock()
	defer deletedEntitiesMutex.Unlock()

	orgId := GetLastNumericPathElement(r.URL.Path)
	org := orgs[orgId]

	// delete org last
	ansibleId := org.AnsibleId
	DeleteOrganization(org)

	// Perform any additional cleanup or API calls
	user, _ := GetRequestUser(r)
	client := NewServiceIndexClient()
	if err := client.Delete(user, ansibleId); err != nil {
		log.Printf("Failed to notify Service Index Client: %v", err)
	}

	// Respond with success
	w.WriteHeader(http.StatusNoContent)
}
