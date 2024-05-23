// a JWT proxy for hub  1234

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


// BasicAuth middleware
func BasicAuth(next http.Handler, users map[string]User) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		auth := r.Header.Get("Authorization")
		if auth == "" {
			w.Header().Set("WWW-Authenticate", `Basic realm="Restricted"`)
			http.Error(w, "Unauthorized1", http.StatusUnauthorized)
			return
		}

        lowerAuth := strings.ToLower(auth)
        if strings.HasPrefix(lowerAuth, "token") { 
            // token auth should go straight to the downstream ...
        } else {
            const basicPrefix = "Basic "
            if !strings.HasPrefix(auth, basicPrefix) {
                http.Error(w, "Unauthorized2", http.StatusUnauthorized)
                return
            }

            decoded, err := base64.StdEncoding.DecodeString(auth[len(basicPrefix):])
            if err != nil {
                http.Error(w, "Unauthorized3", http.StatusUnauthorized)
                return
            }

            credentials := strings.SplitN(string(decoded), ":", 2)
            fmt.Printf("credentials %s\n", credentials)
            if len(credentials) != 2 {
                http.Error(w, "Unauthorized4", http.StatusUnauthorized)
                return
            }

            user, exists := users[credentials[0]]
            if !exists || user.Password != credentials[1] {
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
    proxyPort := getEnv("PROXY_PORT", "8080")
	//target := "http://localhost:5001" // Downstream host is localhost on port 5001
    target := getEnv("UPSTREAM_URL", "http://localhost:5001")
	url, err := url.Parse(target)
	if err != nil {
		panic(err)
	}

	proxy := httputil.NewSingleHostReverseProxy(url)

	originalDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
        log.Printf("Request: %s %s", req.Method, req.URL.String())
		// Alter the request headers here
		req.Header.Add("X-Proxy-Header", "Header-Value")
		originalDirector(req)
	}

	proxy.ModifyResponse = func(resp *http.Response) error {
		// Alter the response headers here
		resp.Header.Add("X-Proxy-Response-Header", "Header-Value")
		return nil
	}

	// Define users
	users := map[string]User{
		"admin": {
			Username:    "admin",
			Password:    "admin",
			FirstName:   "ad",
			LastName:    "min",
			IsSuperuser: true,
			Email:       "admin@example.com",
			Organizations: map[string]interface{}{
			},
			Teams:         []string{},
			IsSystemAuditor: true,
		},
		"john_doe": {
			Username:    "john_doe",
			Password:    "password123",
			FirstName:   "John",
			LastName:    "Doe",
			IsSuperuser: false,
			Email:       "john.doe@example.com",
			Organizations: map[string]interface{}{
				"org1": "Organization 1",
				"org2": "Organization 2",
			},
			Teams:         []string{},
			IsSystemAuditor: false,
		},
		"jane_smith": {
			Username:    "jane_smith",
			Password:    "password456",
			FirstName:   "Jane",
			LastName:    "Smith",
			IsSuperuser: false,
			Email:       "jane.smith@example.com",
			Organizations: map[string]interface{}{
				"org1": "Organization 1",
			},
			Teams:         []string{},
			IsSystemAuditor: false,
		},
	}

	http.HandleFunc("/api/gateway/v1/jwt_key/", jwtKeyHandler)
	http.Handle("/", BasicAuth(proxy, users))

	fmt.Printf("Starting proxy server on :%s\n", proxyPort)
	if err := http.ListenAndServe(fmt.Sprintf(":%s", proxyPort), nil); err != nil {
		panic(err)
	}
}

