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
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"sync"

	"github.com/google/uuid"
)

/************************************************************
	GLOBALS & SETTINGS
************************************************************/

var ANSIBLE_BASE_SHARED_SECRET = "redhat1234"
var SERVICE_ID = uuid.New().String()

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

var (
	users      = map[int]User{}
	usersMutex = &sync.Mutex{}
)

var (
	teams      = map[int]Team{}
	teamsMutex = &sync.Mutex{}
)

var (
	orgs      = map[int]Organization{}
	orgsMutex = &sync.Mutex{}
)

var (
	roleDefinitions      = map[int]RoleDefinition{}
	roleDefinitionsMutex = &sync.Mutex{}
)

var (
	roleUserAssignments      = map[int]RoleUserAssignment{}
	roleUserAssignmentsMutex = &sync.Mutex{}
)

var (
	roleTeamAssignments      = map[int]RoleTeamAssignment{}
	roleTeamAssignmentsMutex = &sync.Mutex{}
)

var (
	deletedEntities      = map[DeletedEntityKey]bool{}
	deletedEntitiesMutex = &sync.Mutex{}
)

/************************************************************
	PREPOPULATED DATA LOADER
************************************************************/

func init() {
	// Generate RSA keys
	log.Printf("# Making RSA keys\n")
	var err error
	rsaPrivateKey, err = rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		panic(err)
	}
	rsaPublicKey = &rsaPrivateKey.PublicKey

	// build orgs ...
	log.Printf("# Making Orgs\n")
	orgsMutex.Lock()
	defer orgsMutex.Unlock()
	for _, org := range prepopulatedOrgs {
		orgs[org.Id] = org
	}

	// build teams ...
	log.Printf("# Making Teams\n")
	teamsMutex.Lock()
	defer teamsMutex.Unlock()
	for _, team := range prepopulatedTeams {
		teams[team.Id] = team
	}

	// build users ...
	log.Printf("# Making Users\n")
	usersMutex.Lock()
	defer usersMutex.Unlock()
	for _, user := range prepopulatedUsers {
		users[user.Id] = user
	}

	// build roledefs ..
	log.Printf("# Making roledefs\n")
	roleDefinitionsMutex.Lock()
	defer roleDefinitionsMutex.Unlock()
	//roleDefinitions = append(roleDefinitions, prepopulatedRoleDefinitions...)
	for _, roledef := range prepopulatedRoleDefinitions {
		roleDefinitions[roledef.Id] = roledef
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
	http.HandleFunc("/api/gateway/v1/my_jwt/", MyJWTHandler)

	// allow direct logins
	http.HandleFunc("/api/gateway/v1/login/", LoginHandler)
	http.HandleFunc("/api/gateway/v1/logout/", LogoutHandler)
	http.HandleFunc("/api/gateway/v1/users/", UserHandler)
	/*
		http.HandleFunc("/api/gateway/v1/teams/", func(w http.ResponseWriter, r *http.Request) {
			if r.Method == http.MethodPost && strings.HasPrefix(r.URL.Path, "/api/gateway/v1/teams/") && strings.Contains(r.URL.Path, "/users/associate/") {
				AssociateTeamUsersHandler(w, r)
			} else {
				TeamHandler(w, r)
			}
		})
	*/
	http.HandleFunc("/api/gateway/v1/teams/", TeamHandler)
	http.HandleFunc("/api/gateway/v1/organizations/", OrganizationHandler)
	http.HandleFunc("/api/gateway/v1/role_definitions/", RoleDefinitionsHandler)
	http.HandleFunc("/api/gateway/v1/role_user_assignments/", RoleUserAssignmentsHandler)

	// send everything else downstream
	http.Handle("/", BasicAuth(proxy))

	fmt.Printf("Starting proxy server on :%s\n", proxyPort)
	if err := http.ListenAndServe(fmt.Sprintf(":%s", proxyPort), nil); err != nil {
		panic(err)
	}
}
