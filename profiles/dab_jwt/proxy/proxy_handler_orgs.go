package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"sort"

	"github.com/google/uuid"
)

func OrganizationHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		getOrgs(w, r)
	case http.MethodPost:
		addOrg(w, r)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func getOrgs(w http.ResponseWriter, r *http.Request) {
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

	highestId := 0
	for _, org := range orgs {
		if org.Name == newOrgRequest.Name || org.CodeName == newOrgRequest.Name {
			http.Error(w, "org name is already taken", http.StatusBadRequest)
			return
		}
		if org.Id > highestId {
			highestId = org.Id
		}
	}

	var newOrg Organization

	newOrg.CodeName = newOrgRequest.Name
	newOrg.Name = newOrgRequest.Name
	newOrg.Id = highestId + 1
	newAnsibleID := uuid.NewString()
	newOrg.AnsibleId = newAnsibleID
	orgs[newOrg.CodeName] = newOrg

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

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(responseOrg)
}
