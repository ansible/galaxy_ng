package main

import (
	"encoding/base64"
	"encoding/json"
	"log"
	"net/http"
	"strings"
)

func MyJWTHandler(w http.ResponseWriter, r *http.Request) {

	//usersMutex.Lock()
	//defer usersMutex.Unlock()

	// Get the Authorization header
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		http.Error(w, "Authorization header missing", http.StatusUnauthorized)
		return
	}

	// The token normally comes in the format "Basic <base64encoded(username:password)>"
	if !strings.HasPrefix(authHeader, "Basic ") {
		http.Error(w, "Invalid authorization method", http.StatusUnauthorized)
		return
	}

	// Decode the base64 encoded credentials
	encodedCredentials := strings.TrimPrefix(authHeader, "Basic ")
	decodedCredentials, err := base64.StdEncoding.DecodeString(encodedCredentials)
	if err != nil {
		http.Error(w, "Invalid base64 encoded credentials", http.StatusUnauthorized)
		return
	}

	// Split the decoded string into username and password
	credentials := strings.SplitN(string(decodedCredentials), ":", 2)
	if len(credentials) != 2 {
		http.Error(w, "Invalid credentials format", http.StatusUnauthorized)
		return
	}

	username := credentials[0]
	log.Printf("USERNAME:%s\n", username)
	user := users[username]
	log.Printf("MAKE CLAIMS")
	claims, _ := GenerateUserClaims(user)
	log.Printf("CLAIMS:%s\n", claims)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(claims)
	log.Printf("DONE")

}
