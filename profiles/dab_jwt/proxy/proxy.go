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
	"time"

	"github.com/golang-jwt/jwt/v4"
)

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

var (
	rsaPrivateKey *rsa.PrivateKey
	rsaPublicKey  *rsa.PublicKey
)

func init() {
	// Generate RSA keys
	var err error
	rsaPrivateKey, err = rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		panic(err)
	}
	rsaPublicKey = &rsaPrivateKey.PublicKey
}

func getEnv(key string, fallback string) string {
	if key, ok := os.LookupEnv(key); ok {
		return key
	}
	return fallback
}

func pathHasPrefix(path string, prefixes []string) bool {
	for _, prefix := range prefixes {
		if strings.HasPrefix(path, prefix) {
			return true
		}
	}
	return false
}

// BasicAuth middleware
func BasicAuth(next http.Handler, users map[string]User) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		prefixes := []string{"/v2", "/token"}

		path := r.URL.Path
		auth := r.Header.Get("Authorization")
		log.Printf("Authorization: %s", auth)

		lowerAuth := strings.ToLower(auth)
		/*
			if auth == "" || strings.HasPrefix(lowerAuth, "token") || strings.HasPrefix(lowerAuth, "bearer"){
				// no auth OR token auth should go straight to the downstream ...
			    log.Printf("skip jwt generation")
			} else {
		*/

		if strings.HasPrefix(lowerAuth, "basic") && !pathHasPrefix(path, prefixes) {

			const basicPrefix = "Basic "
			if !strings.HasPrefix(auth, basicPrefix) {
				log.Printf("Unauthorized2")
				http.Error(w, "Unauthorized2", http.StatusUnauthorized)
				return
			}

			decoded, err := base64.StdEncoding.DecodeString(auth[len(basicPrefix):])
			if err != nil {
				log.Printf("Unauthorized3")
				http.Error(w, "Unauthorized3", http.StatusUnauthorized)
				return
			}

			credentials := strings.SplitN(string(decoded), ":", 2)
			fmt.Printf("credentials %s\n", credentials)
			if len(credentials) != 2 {
				log.Printf("Unauthorized4")
				http.Error(w, "Unauthorized4", http.StatusUnauthorized)
				return
			}

			user, exists := users[credentials[0]]
			if !exists || user.Password != credentials[1] {
				log.Printf("Unauthorized5")
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

		next.ServeHTTP(w, r)
	})
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

	token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
	return token.SignedString(rsaPrivateKey)
}

// jwtKeyHandler handles requests to /api/gateway/v1/jwt_key/
func jwtKeyHandler(w http.ResponseWriter, r *http.Request) {
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

func main() {

	// Define users
	users := map[string]User{
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

		// TODO: add any relevant headers to the downstream request
		// req.Header.Add("X-Proxy-Header", "Header-Value")
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

	// send everything else downstream
	http.Handle("/", BasicAuth(proxy, users))

	fmt.Printf("Starting proxy server on :%s\n", proxyPort)
	if err := http.ListenAndServe(fmt.Sprintf(":%s", proxyPort), nil); err != nil {
		panic(err)
	}
}
