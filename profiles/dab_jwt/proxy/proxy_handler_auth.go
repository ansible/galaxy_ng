package main

import (
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"
)

// BasicAuth middleware
func BasicAuth(next http.Handler) http.Handler {

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {

		log.Printf("Request: %s %s", r.Method, r.URL.String())
		PrintHeaders(r)

		// don't muck the auth header for these paths
		prefixes := []string{"/v2", "/token"}

		// the path CAN determine if auth should be mucked
		path := r.URL.Path

		// extract the authorization header
		auth := r.Header.Get("Authorization")
		log.Printf("\tAuthorization: %s", auth)

		// normalize the header for comparison
		lowerAuth := strings.ToLower(auth)

		// is there a csrftoken and is it valid?
		csrftoken, err := GetCookieValue(r, "csrftoken")
		log.Printf("CHECKING CSRFTOKEN %s", csrftoken)
		if err == nil && !isCSRFTokenKnown(csrftoken) {

			// allow if this was a token from the downstream ...
			if isDownstreamCSRFToken(csrftoken) {
				log.Printf("Found known downstream csrftoken in request headers: %s\n", csrftoken)
				next.ServeHTTP(w, r)
				return
			}

			log.Printf("Unauthorized Invalid csrftoken\n")
			printKnownCSRFTokens()
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(403)
			responseBody := fmt.Sprintf(`{"error": "invalid csrftoken"}`)
			w.Write([]byte(responseBody))
			return
		}

		// is there a sessionid ...?
		gatewaySessionID, _ := GetCookieValue(r, "gateway_sessionid")
		gatewaySessionIDPtr := &gatewaySessionID
		sessionUsernamePtr := sessionIDToUsername(gatewaySessionIDPtr)

		// Check if the pointer is nil and convert it to a string
		var sessionUsername string
		if sessionUsernamePtr != nil {
			sessionUsername = *sessionUsernamePtr
		} else {
			sessionUsername = ""
		}

		if (strings.HasPrefix(lowerAuth, "basic") || sessionUsername != "") && !pathHasPrefix(path, prefixes) {

			if sessionUsername != "" {
				var user User
				user, _ = users[sessionUsername]
				log.Printf("*****************************************")
				log.Printf("username:%s user:%s\n", sessionUsername, user)
				log.Printf("*****************************************")

				// Generate the JWT token
				token, err := generateJWT(user)
				if err != nil {
					http.Error(w, "Internal Server Error", http.StatusInternalServerError)
					return
				}

				// Set the X-DAB-JW-TOKEN header
				r.Header.Set("X-DAB-JW-TOKEN", token)

			} else {

				const basicPrefix = "Basic "
				if !strings.HasPrefix(auth, basicPrefix) {
					log.Printf("Unauthorized2\n")
					http.Error(w, "Unauthorized2", http.StatusUnauthorized)
					return
				}

				decoded, err := base64.StdEncoding.DecodeString(auth[len(basicPrefix):])
				if err != nil {
					log.Printf("Unauthorized3\n")
					http.Error(w, "Unauthorized3", http.StatusUnauthorized)
					return
				}

				credentials := strings.SplitN(string(decoded), ":", 2)
				fmt.Printf("credentials %s\n", credentials)
				if len(credentials) != 2 {
					log.Printf("Unauthorized4\n")
					http.Error(w, "Unauthorized4", http.StatusUnauthorized)
					return
				}

				user, exists := users[credentials[0]]
				log.Printf("extracted user:%s from creds[0]:%s creds:%s\n", user, credentials[0], credentials)
				if !exists || user.Password != credentials[1] {
					log.Printf("Unauthorized5\n")
					http.Error(w, "Unauthorized5", http.StatusUnauthorized)
					return
				}

				// Generate the JWT token
				token, err := generateJWT(user)
				if err != nil {
					http.Error(w, "Internal Server Error", http.StatusInternalServerError)
					return
				}

				// Set the X-DAB-JW-TOKEN header
				r.Header.Set("X-DAB-JW-TOKEN", token)
			}

			// Remove the Authorization header
			r.Header.Del("Authorization")
		}

		next.ServeHTTP(w, r)
	})
}

// jwtKeyHandler handles requests to /api/gateway/v1/jwt_key/
func jwtKeyHandler(w http.ResponseWriter, r *http.Request) {
	log.Printf("Request: %s %s", r.Method, r.URL.String())

	pubKeyBytes, err := x509.MarshalPKIXPublicKey(rsaPublicKey)
	if err != nil {
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}
	pubKeyPem := pem.EncodeToMemory(&pem.Block{
		Type:  "PUBLIC KEY",
		Bytes: pubKeyBytes,
	})

	w.Header().Set("Content-Type", "application/x-pem-file")
	w.Write(pubKeyPem)
}

// LoginHandler handles the login requests
func LoginHandler(w http.ResponseWriter, r *http.Request) {

	log.Printf("Request: %s %s", r.Method, r.URL.String())
	PrintHeaders(r)

	switch r.Method {
	case http.MethodGet:
		// Generate a CSRF token for the GET request
		csrfToken := GenerateCSRFToken()

		// Set the CSRF token as a cookie
		http.SetCookie(w, &http.Cookie{
			Name:    "csrfToken",
			Value:   csrfToken,
			Expires: time.Now().Add(24 * time.Hour),
		})

		// Manually format the response to match the regex pattern
		responseBody := fmt.Sprintf(`{"csrfToken": "%s"}`, csrfToken)

		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(responseBody))

	case http.MethodPost:

		// Parse the multipart form
		err := r.ParseMultipartForm(10 << 20) // 10 MB max memory
		if err != nil {
			http.Error(w, "Failed to parse multipart form", http.StatusBadRequest)
			return
		}

		PrintFormValues(r)

		// Extract form values
		username := r.FormValue("username")
		//password := r.FormValue("password")
		//csrfTokenForm := r.FormValue("csrfToken")

		// Retrieve the CSRF token from the request header
		csrfTokenHeader := r.Header.Get("X-CSRFtoken")

		// Retrieve the CSRF token from the cookies
		cookie, err := r.Cookie("csrfToken")
		if err != nil {
			http.Error(w, "CSRF token cookie not found", http.StatusForbidden)
			return
		}

		if csrfTokenHeader == "" {
			http.Error(w, "CSRF token header not found", http.StatusForbidden)
			return
		}

		if cookie.Value != csrfTokenHeader {
			http.Error(w, "CSRF token in cookie does not match header", http.StatusForbidden)
			return
		}

		// Here you would normally validate the username and password.
		// For this example, we assume the login is always successful.

		// Set the CSRF token as a cookie
		csrfToken := GenerateCSRFToken()
		http.SetCookie(w, &http.Cookie{
			Name:    "csrftoken",
			Value:   csrfToken,
			Expires: time.Now().Add(24 * time.Hour),
		})

		// Set the sessionid token as a cookie
		gatewaySessionID := GenerateSessionID()
		http.SetCookie(w, &http.Cookie{
			Name:    "gateway_sessionid",
			Value:   gatewaySessionID,
			Expires: time.Now().Add(24 * time.Hour),
		})

		// add this session to the table
		tokenTable.Lock()
		tokenTable.data[gatewaySessionID] = UserSession{
			Username:  username,
			CSRFToken: csrfToken,
			SessionID: gatewaySessionID,
		}
		tokenTable.Unlock()

		// Respond with a success message (you can customize this as needed)
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"message": "Login successful"}`))

	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// LoginHandler handles the login requests
func LogoutHandler(w http.ResponseWriter, r *http.Request) {
}
