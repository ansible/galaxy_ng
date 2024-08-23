package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
)

type ServiceIndexPayload struct {
	AnsibleId    string                   `json:"ansible_id"`
	ServiceId    string                   `json:"service_id"`
	ResourceType string                   `json:"resource_type"`
	ResourceData ServiceIndexResourceData `json:"resource_data"`
}

// ResourceData represents the data structure for resource_data in the payload
type ServiceIndexResourceData struct {
	Name         string  `json:"name,omitempty"`
	UserName     string  `json:"username,omitempty"`
	Email        string  `json:"email,omitempty"`
	FirstName    string  `json:"first_name,omitempty"`
	LastName     string  `json:"last_name,omitempty"`
	SuperUser    bool    `json:"is_superuser,omitempty"`
	Description  string  `json:"description,omitempty"`
	Organization *string `json:"organization,omitempty"`
}

// Payload represents an arbitrary map of data
type Payload map[string]interface{}

// ServiceIndexClient is the client that will handle the HTTP requests
type ServiceIndexClient struct {
	BaseURL string
	Client  *http.Client
}

// NewServiceIndexClient initializes and returns a ServiceIndexClient
func NewServiceIndexClient() *ServiceIndexClient {
	return &ServiceIndexClient{
		Client: &http.Client{},
	}
}

// PostData sends a POST request to the remote endpoint with User and Payload
func (c *ServiceIndexClient) PostData(user User, payload ServiceIndexPayload) error {

	log.Printf("starting indexclient POST ...")

	target := getEnv("UPSTREAM_URL", "http://localhost:5001")
	endpoint := target + getEnv("UPSTREAM_API_PREFIX", "/api/galaxy") + "/service-index/resources/"

	log.Printf("using endpoint %s", endpoint)

	// Generate the JWT token
	log.Printf("generating token for request user ...")
	token, err := generateJWT(user)
	if err != nil {
		//http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		log.Printf("token generation failed %s", err)
		return err
	}
	log.Printf("generated token %s", token)

	// Marshal the data into JSON
	jsonData, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal data: %v", err)
	}

	// Create a new POST request
	log.Printf("POST %s to %s", jsonData, endpoint)
	req, err := http.NewRequest("POST", endpoint, bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create request: %v", err)
	}

	// Set headers
	req.Header.Set("X-DAB-JW-TOKEN", token)
	req.Header.Set("Content-Type", "application/json")

	// Perform the request
	resp, err := c.Client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to make request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("received non-200 response: %d", resp.StatusCode)
	}

	// Optionally, read and process response body here
	return nil
}
