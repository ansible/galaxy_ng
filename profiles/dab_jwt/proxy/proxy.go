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

// Global table to store CSRF tokens, session IDs, and usernames
var tokenTable = struct {
	sync.RWMutex
	data map[string]UserSession
}{
	data: make(map[string]UserSession),
}

// UserSession represents the user session information
type UserSession struct {
	Username  string
	CSRFToken string
	SessionID string
}

// User represents a user's information
type User struct {
	Username        string
	Password        string
	FirstName       string
	LastName        string
	IsSuperuser     bool
	Email           string
	Organizations   map[string]interface{}
	Teams           []string
	IsSystemAuditor bool
}

// JWT claims
type UserClaims struct {
	Iss             string                 `json:"iss"`
	Aud             string                 `json:"aud"`
	Username        string                 `json:"username"`
	FirstName       string                 `json:"first_name"`
	LastName        string                 `json:"last_name"`
	IsSuperuser     bool                   `json:"is_superuser"`
	Email           string                 `json:"email"`
	Sub             string                 `json:"sub"`
	Claims          map[string]interface{} `json:"claims"`
	IsSystemAuditor bool                   `json:"is_system_auditor"`
	jwt.RegisteredClaims
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

/************************************************************
	GLOBALS & SETTINGS
************************************************************/

var (
	rsaPrivateKey *rsa.PrivateKey
	rsaPublicKey  *rsa.PublicKey
)

var ANSIBLE_BASE_SHARED_SECRET = "redhat1234"

// Define users
var users = map[string]User{
	"admin": {
		Username:        "admin",
		Password:        "admin",
		FirstName:       "ad",
		LastName:        "min",
		IsSuperuser:     true,
		Email:           "admin@example.com",
		Organizations:   map[string]interface{}{},
		Teams:           []string{},
		IsSystemAuditor: true,
	},
	"notifications_admin": {
		Username:        "notifications_admin",
		Password:        "redhat",
		FirstName:       "notifications",
		LastName:        "admin",
		IsSuperuser:     true,
		Email:           "notifications_admin@example.com",
		Organizations:   map[string]interface{}{},
		Teams:           []string{},
		IsSystemAuditor: true,
	},
	"jdoe": {
		Username:    "jdoe",
		Password:    "redhat",
		FirstName:   "John",
		LastName:    "Doe",
		IsSuperuser: false,
		Email:       "john.doe@example.com",
		Organizations: map[string]interface{}{
			"org1": "Organization 1",
			"org2": "Organization 2",
		},
		Teams:           []string{},
		IsSystemAuditor: false,
	},
}

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
			log.Printf("\theader \t%s: %s\n", name, value)
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
	var SharedSecretNotFound = errors.New("The setting ANSIBLE_BASE_SHARED_SECRET was not set, some functionality may be disabled")

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
	claims := UserClaims{
		Iss:         "ansible-issuer",
		Aud:         "ansible-services",
		Username:    user.Username,
		FirstName:   user.FirstName,
		LastName:    user.LastName,
		IsSuperuser: user.IsSuperuser,
		Email:       user.Email,
		Sub:         user.Username,
		Claims: map[string]interface{}{
			"organizations": user.Organizations,
			"teams":         user.Teams,
		},
		IsSystemAuditor: user.IsSystemAuditor,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			Issuer:    "ansible-issuer",
		},
	}
    log.Printf("\tMake claim for %s\n", user)
	log.Printf("\tClaim %s\n", claims)
    jsonData, _ := json.Marshal(claims)
    log.Printf("\t%s\n", jsonData)

	token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
	return token.SignedString(rsaPrivateKey)
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
			    var user User;
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
		req.Header.Add("X-Forwarded-Proto", "https")

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
		return nil
	}

	// serve /api/gateway/v1/jwt_key/ from this service so the client can
	// get the decryption keys for the jwts
	http.HandleFunc("/api/gateway/v1/jwt_key/", jwtKeyHandler)

	// allow direct logins
	http.HandleFunc("/api/gateway/v1/login/", LoginHandler)

	// send everything else downstream
	http.Handle("/", BasicAuth(proxy))

	fmt.Printf("Starting proxy server on :%s\n", proxyPort)
	if err := http.ListenAndServe(fmt.Sprintf(":%s", proxyPort), nil); err != nil {
		panic(err)
	}
}
