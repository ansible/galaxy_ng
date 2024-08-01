/*************************************************************

    DAB JWT Proxy

    Given a galaxy_ng stack that is configured to enable
    ansible_base.jwt_consumer.hub.auth.HubJWTAuth from
    an upstream proxy, this script serves as that proxy.

    The clients use basic auth to talk to the proxy,
    and then the proxy replaces their authorization header
    with a JWT before passing it on to the galaxy system.
    The galaxy backend decrypts and decodes the token
    to determine the username, email, first, last, teams,
    and groups.

    If the client tries to auth via a token, the proxy
    should not alter the authorization header and instead
    pass it unmodified to galaxy. This presumably keeps
    backwards compatibility for ansible-galaxy cli clients
    which have been configured to use django api tokens.

*************************************************************/

package main

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"sort"
	"strings"
	"sync"
	"time"

	"crypto/hmac"
	"crypto/sha256"
	"encoding/json"
	"errors"

	"github.com/golang-jwt/jwt/v4"
	"github.com/google/uuid"
)

/************************************************************
	TYPES
************************************************************/

// UserSession represents the user session information
type UserSession struct {
	Username  string
	CSRFToken string
	SessionID string
}

// User represents a user's information
type User struct {
	Id              int
	Username        string
	Password        string
	FirstName       string
	LastName        string
	IsSuperuser     bool
	Email           string
	Organizations   []string
	Teams           []string
	IsSystemAuditor bool
	Sub             string
}

/*
pulp-1          | {'aud': 'ansible-services',
pulp-1          |  'exp': 1718658788,
pulp-1          |  'global_roles': [],
pulp-1          |  'iss': 'ansible-issuer',
pulp-1          |  'object_roles': {'Team Member': {'content_type': 'team', 'objects': [0]}},
pulp-1          |  'objects': {'organization': [{'ansible_id': 'bc243368-a9d4-4f8f-9ffe-5d2d921fcee5',
pulp-1          |                                'name': 'Default'}],
pulp-1          |              'team': [{'ansible_id': '34a58292-1e0f-49f0-9383-fb7e63d771d9',
pulp-1          |                        'name': 'ateam',
pulp-1          |                        'org': 0}]},
pulp-1          |  'sub': '4f6499bf-3ad2-45ff-8411-0188c4f817c1',
pulp-1          |  'user_data': {'email': 'sa@localhost.com',
pulp-1          |                'first_name': 'sa',
pulp-1          |                'is_superuser': True,
pulp-1          |                'last_name': 'asdfasdf',
pulp-1          |                'username': 'superauditor'},
pulp-1          |  'version': '1'}
*/

// JWT claims
type UserClaims struct {
	Version     int                    `json:"version"`
	Iss         string                 `json:"iss"`
	Aud         string                 `json:"aud"`
	Expires     int64                  `json:"exp"`
	GlobalRoles []string               `json:"global_roles"`
	UserData    UserData               `json:"user_data"`
	Sub         string                 `json:"sub"`
	ObjectRoles map[string]interface{} `json:"object_roles"`
	Objects     map[string]interface{} `json:"objects"`
}

// Implement the jwt.Claims interface
func (c UserClaims) Valid() error {
	if time.Unix(c.Expires, 0).Before(time.Now()) {
		return fmt.Errorf("token is expired")
	}
	return nil
}

type UserData struct {
	Username    string `json:"username"`
	FirstName   string `json:"first_name"`
	LastName    string `json:"last_name"`
	IsSuperuser bool   `json:"is_superuser"`
	Email       string `json:"email"`
}

type Organization struct {
	AnsibleId string `json:"ansible_id"`
	Name      string `json:"name"`
}

type Team struct {
	AnsibleId string `json:"ansible_id"`
	Name      string `json:"name"`
	Org       string `json:"org"`
}

type TeamObject struct {
	AnsibleId string `json:"ansible_id"`
	Name      string `json:"name"`
	Org       int    `json:"org"`
}

type ObjectRole struct {
	ContentType string `json:"content_type"`
	Objects     []int  `json:"objects"`
}

// LoginRequest represents the login request payload
type LoginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

// LoginResponse represents the login response payload
type LoginResponse struct {
	CSRFToken string `json:"csrfToken"`
}

type UserResponse struct {
	ID            int    `json:"id"`
	Username      string `json:"username"`
	SummaryFields struct {
		Resource struct {
			AnsibleID string `json:"ansible_id"`
		} `json:"resource"`
	} `json:"summary_fields"`
}

/************************************************************
	GLOBALS & SETTINGS
************************************************************/

// Global table to store CSRF tokens, session IDs, and usernames
var tokenTable = struct {
	sync.RWMutex
	data map[string]UserSession
}{
	data: make(map[string]UserSession),
}

// tokens we discover in the response headers ...
var csrfTokenStore = struct {
	sync.RWMutex
	tokens []string
}{
	tokens: make([]string, 0),
}

var (
	rsaPrivateKey *rsa.PrivateKey
	rsaPublicKey  *rsa.PublicKey
)

var ANSIBLE_BASE_SHARED_SECRET = "redhat1234"

var orgmap = map[string]int{
	"default": 0,
	"org1":    1,
	"org2":    2,
}

var orgs = map[string]Organization{
	"default": {
		AnsibleId: "bc243368-a9d4-4f8f-9ffe-5d2d921fcee0",
		Name:      "Default",
	},
	"org1": {
		AnsibleId: "bc243368-a9d4-4f8f-9ffe-5d2d921fcee1",
		Name:      "Organization 1",
	},
	"org2": {
		AnsibleId: "bc243368-a9d4-4f8f-9ffe-5d2d921fcee2",
		Name:      "Organization 2",
	},
	"pe": {
		AnsibleId: "bc243368-a9d4-4f8f-9ffe-5d2d921fcee3",
		Name:      "system:partner-engineers",
	},
}

var teams = map[string]Team{
	"ateam": {
		AnsibleId: "34a58292-1e0f-49f0-9383-fb7e63d771aa",
		Name:      "ateam",
		Org:       "org1",
	},
	"bteam": {
		AnsibleId: "34a58292-1e0f-49f0-9383-fb7e63d771ab",
		Name:      "bteam",
		Org:       "default",
	},
	"peteam": {
		AnsibleId: "34a58292-1e0f-49f0-9383-fb7e63d771ac",
		Name:      "peteam",
		Org:       "pe",
	},
}

// Define users
var prepopulatedUsers = map[string]User{
	"admin": {
		Id:              1,
		Username:        "admin",
		Password:        "admin",
		FirstName:       "ad",
		LastName:        "min",
		IsSuperuser:     true,
		Email:           "admin@example.com",
		Organizations:   []string{"default"},
		Teams:           []string{},
		IsSystemAuditor: true,
		Sub:             "bc243368-a9d4-4f8f-9ffe-5d2d921fce99",
	},
	"notifications_admin": {
		Id:              2,
		Username:        "notifications_admin",
		Password:        "redhat",
		FirstName:       "notifications",
		LastName:        "admin",
		IsSuperuser:     true,
		Email:           "notifications_admin@example.com",
		Organizations:   []string{"default"},
		Teams:           []string{},
		IsSystemAuditor: true,
		Sub:             "bc243368-a9d4-4f8f-9ffe-5d2d921fce98",
	},
	"ee_admin": {
		Id:              3,
		Username:        "ee_admin",
		Password:        "redhat",
		FirstName:       "ee",
		LastName:        "admin",
		IsSuperuser:     true,
		Email:           "ee_admin@example.com",
		Organizations:   []string{"default"},
		Teams:           []string{},
		IsSystemAuditor: true,
		Sub:             "bc243368-a9d4-4f8f-9ffe-5d2d921fce97",
	},
	"jdoe": {
		Id:        4,
		Username:  "jdoe",
		Password:  "redhat",
		FirstName: "John",
		LastName:  "Doe",
		//IsSuperuser: false,
		IsSuperuser: true,
		Email:       "john.doe@example.com",
		Organizations: []string{
			"default",
			"org1",
			"org2",
			"pe",
		},
		Teams:           []string{"peteam"},
		IsSystemAuditor: false,
		Sub:             "bc243368-a9d4-4f8f-9ffe-5d2d921fce96",
	},
	"iqe_normal_user": {
		Id:          5,
		Username:    "iqe_normal_user",
		Password:    "redhat",
		FirstName:   "iqe",
		LastName:    "normal_user",
		IsSuperuser: false,
		Email:       "iqe_normal_user@example.com",
		Organizations: []string{
			"default",
			"org1",
			"org2",
		},
		//Teams:           []string{"ateam", "bteam"},
		//Teams:           []string{"bteam"},
		Teams:           []string{},
		IsSystemAuditor: false,
		Sub:             "bc243368-a9d4-4f8f-9ffe-5d2d921fce95",
	},
}

var (
	users      = map[string]User{}
	usersMutex = &sync.Mutex{}
	idCounter  = 6
)

/************************************************************
	FUNCTIONS
************************************************************/

func init() {
	// Generate RSA keys
	var err error
	rsaPrivateKey, err = rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		panic(err)
	}
	rsaPublicKey = &rsaPrivateKey.PublicKey
}

// PrintHeaders prints all headers from the request
func PrintHeaders(r *http.Request) {
	for name, values := range r.Header {
		for _, value := range values {
			log.Printf("\trequest header \t%s: %s\n", name, value)
		}
	}
}

func PrintResponseHeaders(resp *http.Response) {
	if resp == nil {
		fmt.Println("Response is nil")
		return
	}

	fmt.Println("Response Headers:")
	for key, values := range resp.Header {
		for _, value := range values {
			//fmt.Printf("%s: %s\n", key, value)
			log.Printf("\tresponse header \t%s: %s\n", key, value)
		}
	}
}

// PrintFormValues prints all form values from the request
func PrintFormValues(r *http.Request) {
	for key, values := range r.MultipartForm.Value {
		for _, value := range values {
			log.Printf("\tform %s: %s\n", key, value)
		}
	}
}

func getEnv(key string, fallback string) string {
	if key, ok := os.LookupEnv(key); ok {
		return key
	}
	return fallback
}

// GetCookieValue retrieves the value of a specific cookie by name
func GetCookieValue(r *http.Request, name string) (string, error) {
	cookie, err := r.Cookie(name)
	if err != nil {
		return "", err
	}
	return cookie.Value, nil
}

// GetCookieValue retrieves the value of a specific cookie by name
//
//	Set-Cookie: csrftoken=TXb2gLP6dGd8pksgZ88ICXhbW664wCbQ; expires=Thu, 29 May 2025 ...
func ExtractCSRFCookie(resp *http.Response) (string, error) {
	if resp == nil {
		return "", fmt.Errorf("response is nil")
	}

	// Retrieve the Set-Cookie headers
	cookies := resp.Cookies()

	// Loop through cookies to find the CSRF token
	for _, cookie := range cookies {
		if cookie.Name == "csrftoken" {
			return cookie.Value, nil
		}
	}

	return "", fmt.Errorf("CSRF token not found")
}

func pathHasPrefix(path string, prefixes []string) bool {
	for _, prefix := range prefixes {
		if strings.HasPrefix(path, prefix) {
			return true
		}
	}
	return false
}

// GenerateCSRFToken generates a new CSRF token
func GenerateCSRFToken() string {
	return uuid.New().String()
}

// GenerateSessionID generates a new session ID
func GenerateSessionID() string {
	return uuid.New().String()
}

// sessionIDToUsername checks the tokenTable for the sessionID and returns the username or nil
func sessionIDToUsername(sessionID *string) *string {
	if sessionID == nil || *sessionID == "" {
		return nil
	}

	tokenTable.RLock()
	defer tokenTable.RUnlock()

	userSession, exists := tokenTable.data[*sessionID]
	if !exists {
		return nil
	}

	return &userSession.Username
}

func generateHmacSha256SharedSecret(nonce *string) (string, error) {

	//const ANSIBLE_BASE_SHARED_SECRET = "redhat1234"
	var SharedSecretNotFound = errors.New("the setting ANSIBLE_BASE_SHARED_SECRET was not set, some functionality may be disabled")

	if ANSIBLE_BASE_SHARED_SECRET == "" {
		log.Println("The setting ANSIBLE_BASE_SHARED_SECRET was not set, some functionality may be disabled.")
		return "", SharedSecretNotFound
	}

	if nonce == nil {
		currentNonce := fmt.Sprintf("%d", time.Now().Unix())
		nonce = &currentNonce
	}

	message := map[string]string{
		"nonce":         *nonce,
		"shared_secret": ANSIBLE_BASE_SHARED_SECRET,
	}

	messageBytes, err := json.Marshal(message)
	if err != nil {
		return "", err
	}

	mac := hmac.New(sha256.New, []byte(ANSIBLE_BASE_SHARED_SECRET))
	mac.Write(messageBytes)
	signature := fmt.Sprintf("%x", mac.Sum(nil))

	secret := fmt.Sprintf("%s:%s", *nonce, signature)
	return secret, nil
}

// generateJWT generates a JWT for the user
func generateJWT(user User) (string, error) {

	// make a list of org structs for this user ...
	userOrgs := []Organization{}
	userTeams := []TeamObject{}

	localOrgMap := map[string]int{}
	counter := -1
	for _, orgName := range user.Organizations {
		counter += 1
		localOrgMap[orgName] = counter
		userOrgs = append(userOrgs, orgs[orgName])
	}
	for _, team := range user.Teams {
		orgName := teams[team].Org
		orgIndex := localOrgMap[orgName]
		userTeams = append(userTeams, TeamObject{
			AnsibleId: teams[team].AnsibleId,
			Name:      team,
			Org:       orgIndex,
		})
	}

	objects := map[string]interface{}{
		"organization": userOrgs,
		"team":         userTeams,
	}
	objectRoles := map[string]interface{}{}
	if len(userTeams) > 0 {
		objectRoles["Team Member"] = ObjectRole{
			ContentType: "team",
			Objects:     []int{0},
		}
	}

	// make the expiration time
	numericDate := jwt.NewNumericDate(time.Now().Add(time.Hour))
	unixTime := numericDate.Unix()

	claims := UserClaims{
		Version:     1,
		Iss:         "ansible-issuer",
		Aud:         "ansible-services",
		Expires:     unixTime,
		GlobalRoles: []string{},
		UserData: UserData{
			Username:    user.Username,
			FirstName:   user.FirstName,
			LastName:    user.LastName,
			IsSuperuser: user.IsSuperuser,
			Email:       user.Email,
		},
		Sub:         user.Sub,
		ObjectRoles: objectRoles,
		Objects:     objects,
	}
	log.Printf("\tMake claim for %s\n", user)
	log.Printf("\tClaim %s\n", claims)
	jsonData, _ := json.Marshal(claims)
	log.Printf("\t%s\n", jsonData)

	token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
	return token.SignedString(rsaPrivateKey)
}

// Function to check if a CSRF token is known
func isCSRFTokenKnown(token string) bool {
	tokenTable.RLock()
	defer tokenTable.RUnlock()

	for _, session := range tokenTable.data {
		if session.CSRFToken == token {
			return true
		}
	}
	return false
}

// check if we've ever seen this token come back in the response headers
// from the downstream service
func isDownstreamCSRFToken(token string) bool {
	csrfTokenStore.RLock()
	defer csrfTokenStore.RUnlock()
	for _, t := range csrfTokenStore.tokens {
		if t == token {
			return true
		}
	}
	return false
}

func printKnownCSRFTokens() {
	tokenTable.RLock()
	defer tokenTable.RUnlock()

	for _, session := range tokenTable.data {
		log.Printf("\t\tcsrf:%s sid:%s uid:%s\n", session.CSRFToken, session.SessionID, session.Username)
	}
}

/************************************************************
	HANDLERS
************************************************************/

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
			w.WriteHeader(401)
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

func UserHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		getUsers(w, r)
	case http.MethodPost:
		addUser(w, r)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func getUsers(w http.ResponseWriter, r *http.Request) {
	usersMutex.Lock()
	defer usersMutex.Unlock()

	var userList []User
	for _, user := range users {
		userList = append(userList, user)
	}
	sort.Slice(userList, func(i, j int) bool {
		return userList[i].Id < userList[j].Id
	})

	var responseUsers []UserResponse

	//for _, userdata := range users {
	for _, userdata := range userList {
		responseUser := UserResponse{
			ID:       userdata.Id,
			Username: userdata.Username,
			SummaryFields: struct {
				Resource struct {
					AnsibleID string `json:"ansible_id"`
				} `json:"resource"`
			}{Resource: struct {
				AnsibleID string `json:"ansible_id"`
			}{AnsibleID: userdata.Sub}},
		}
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

	var newUser User
	if err := json.NewDecoder(r.Body).Decode(&newUser); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	usersMutex.Lock()
	defer usersMutex.Unlock()

	if _, exists := users[newUser.Username]; exists {
		http.Error(w, "User already exists", http.StatusConflict)
		return
	}

	highestId := 0
	for _, user := range users {
		if user.Id > highestId {
			highestId = user.Id
		}
	}

	newUser.Id = highestId + 1
	newAnsibleID := uuid.NewString()
	newUser.Sub = newAnsibleID
	users[newUser.Username] = newUser

	responseUser := UserResponse{
		ID:       idCounter,
		Username: newUser.Username,
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
	json.NewEncoder(w).Encode(responseUser)
}

func init() {
	usersMutex.Lock()
	defer usersMutex.Unlock()

	for _, user := range prepopulatedUsers {
		users[user.Username] = user
	}
}

func main() {

	// listen port
	proxyPort := getEnv("PROXY_PORT", "8080")

	// downstream host
	target := getEnv("UPSTREAM_URL", "http://localhost:5001")

	// verify the url
	url, err := url.Parse(target)
	if err != nil {
		panic(err)
	}

	// instantiate the proxy
	proxy := httputil.NewSingleHostReverseProxy(url)

	originalDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		// log every reqest
		log.Printf("Request: %s %s", req.Method, req.URL.String())

		// just assume this proxy is http ...
		req.Header.Add("X-Forwarded-Proto", "http")

		// https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/headers#x-envoy-internal
		req.Header.Add("X-Envoy-Internal", "true")

		// each request has a unique ID
		newUUID := uuid.New()
		req.Header.Add("X-Request-Id", newUUID.String())

		// make the x-trusted-proxy header
		newSecret, _ := generateHmacSha256SharedSecret(nil)
		req.Header.Add("X-Trusted-Proxy", newSecret)

		originalDirector(req)
	}

	proxy.ModifyResponse = func(resp *http.Response) error {
		// TODO: add any relevant headers to the response
		//resp.Header.Add("X-Proxy-Response-Header", "Header-Value")
		PrintResponseHeaders(resp)

		// did the response contain any csrftokens? save them ...
		csrftoken, err := ExtractCSRFCookie(resp)
		if err == nil {
			log.Printf("### FOUND CSRFTOKEN IN RESPONSE ---> %s\n", csrftoken)
			csrfTokenStore.Lock()
			defer csrfTokenStore.Unlock()
			csrfTokenStore.tokens = append(csrfTokenStore.tokens, csrftoken)
		}

		return nil
	}

	// serve /api/gateway/v1/jwt_key/ from this service so the client can
	// get the decryption keys for the jwts
	http.HandleFunc("/api/gateway/v1/jwt_key/", jwtKeyHandler)

	// allow direct logins
	http.HandleFunc("/api/gateway/v1/login/", LoginHandler)
	http.HandleFunc("/api/gateway/v1/logout/", LogoutHandler)
	http.HandleFunc("/api/gateway/v1/users/", UserHandler)

	// send everything else downstream
	http.Handle("/", BasicAuth(proxy))

	fmt.Printf("Starting proxy server on :%s\n", proxyPort)
	if err := http.ListenAndServe(fmt.Sprintf(":%s", proxyPort), nil); err != nil {
		panic(err)
	}
}
