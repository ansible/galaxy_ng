package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"math/rand"
	"net"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strings"
	"syscall"
	"time"
)

var refreshTokens = map[string]string{
	"1234567890":                           "jdoe",
	"1234567891":                           "iqe_normal_user",
	"1234567892":                           "org-admin",
	"1234567893":                           "notifications_admin",
	"abcdefghijklmnopqrstuvwxyz1234567892": "jdoe",
	"abcdefghijklmnopqrstuvwxyz1234567891": "iqe_normal_user",
	"abcdefghijklmnopqrstuvwxyz1234567893": "org-admin",
	"abcdefghijklmnopqrstuvwxyz1234567894": "notifications_admin",
}

// Access tokens will be stored here, and they can be generated using the refresh
// tokens listed above using the:
// curl -X POST localhost:8080/auth/realms/redhat-external/protocol/openid-connect/token -d refresh_token=1234567890
// API endpoint.
var accessTokens = map[string]string{
	// use this if you want to bypass the access token step
	"TESTINGTOKEN": "jdoe",
}

type User struct {
	Username   string `json:"username"`
	FirstName  string `json:"first_name"`
	LastName   string `json:"last_name"`
	Email      string `json:"email"`
	IsOrgAdmin bool   `json:"is_org_admin"`
}

type ServiceAccount struct {
	ClientId string `json:"client_id"`
	Username string `json:"username"`
}

type Account struct {
	AccountNumber int  `json:"account_number"`
	User          User `json:"user"`
}

type Entitlement struct {
	Insights map[string]bool `json:"insights"`
}

type XRHItentity struct {
	Identity     Account     `json:"identity"`
	Entitlements Entitlement `json:"entitlements"`
}

type XRHSVCItentity struct {
	Entitlements Entitlement `json:"entitlements"`
	Identity     struct {
		AuthType       string `json:"auth_type"`
		Internal       struct {
			AuthTime    int    `json:"auth_time"`
			CrossAccess bool   `json:"cross_access"`
			OrgID       string `json:"org_id"`
		} `json:"internal"`
		OrgID          string `json:"org_id"`
		Type           string `json:"type"`
		ServiceAccount struct {
			ClientID string `json:"client_id"`
			Username string `json:"username"`
		} `json:"service_account"`
	} `json:"identity"`
}

var accounts = map[string]Account{
	"jdoe": {
		AccountNumber: 6089719,
		User: User{
			Username:   "jdoe",
			Email:      "jdoe@redhat.com",
			FirstName:  "john",
			LastName:   "doe",
			IsOrgAdmin: false,
		},
	},
	"iqe_normal_user": {
		AccountNumber: 6089723,
		User: User{
			Username:   "iqe_normal_user",
			Email:      "iqe_normal_user@redhat.com",
			FirstName:  "",
			LastName:   "",
			IsOrgAdmin: false,
		},
	},
	"org-admin": {
		AccountNumber: 6089720,
		User: User{
			Username:   "org-admin",
			Email:      "org-admin@redhat.com",
			FirstName:  "org",
			LastName:   "admin",
			IsOrgAdmin: true,
		},
	},
	"notifications_admin": {
		AccountNumber: 6089726,
		User: User{
			Username:   "notifications_admin",
			Email:      "notifications_admin@redhat.com",
			FirstName:  "notifications",
			LastName:   "admin",
			IsOrgAdmin: false,
		},
	},
}

var serviceAccounts = map[string]ServiceAccount {
	"service-account-b69eaf9e-e6a6-4f9e-805e-02987daddfbd": {
		Username:   "service-account-b69eaf9e-e6a6-4f9e-805e-02987daddfbd",
		ClientId:	"b69eaf9e-e6a6-4f9e-805e-02987daddfbd",
	},
}

func randomString(length int) string {
	rand.Seed(time.Now().UnixNano())
	b := make([]byte, length)
	rand.Read(b)
	return fmt.Sprintf("%x", b)[:length]
}

func getAccessToken(rw http.ResponseWriter, req *http.Request) {
	req.ParseForm()
	refresh_token := req.FormValue("refresh_token")

	if accountID, ok := refreshTokens[refresh_token]; ok {
		fmt.Printf("xxx Creating refresh token for: %s", accountID)

		acces_token := randomString(32)
		accessTokens[acces_token] = accountID

		rw.Header().Set("Content-Type", "application/json")
		resp := map[string]string{
			"access_token": acces_token,
		}

		rw.WriteHeader(http.StatusAccepted)
		json.NewEncoder(rw).Encode(resp)
	} else {
		rw.WriteHeader(http.StatusUnauthorized)
	}
}

func userToIentityHeader(account Account) string {

	data, _ := json.Marshal(XRHItentity{
		Entitlements: Entitlement{
			Insights: map[string]bool{
				"is_entitled": true,
				"is_trial":    false,
			},
		},
		Identity: account,
	})

	fmt.Printf("Setting X-RH-IDENTITY: %s\n", string(data))

	return base64.StdEncoding.EncodeToString([]byte(data))
}

func serviceAccountToIentityHeader(svc_account ServiceAccount) string {
	/*
	{
	  "entitlements": {},
	  "identity": {
		"auth_type": "jwt-auth",
		"internal": {
		  "auth_time": 500,
		  "cross_access": false,
		  "org_id": "456"
		},
		"org_id": "456",
		"type": "ServiceAccount",
		"service_account": {
		  "client_id": "b69eaf9e-e6a6-4f9e-805e-02987daddfbd",
		  "username": "service-account-b69eaf9e-e6a6-4f9e-805e-02987daddfbd"
		}
	  }
	}
	*/

	data := XRHSVCItentity{
		Entitlements: Entitlement{
			Insights: map[string]bool{
				"is_entitled": true,
				"is_trial":    false,
			},
		},
		Identity: struct {
			AuthType string `json:"auth_type"`
			Internal struct {
				AuthTime    int    `json:"auth_time"`
				CrossAccess bool   `json:"cross_access"`
				OrgID       string `json:"org_id"`
			} `json:"internal"`
			OrgID          string `json:"org_id"`
			Type           string `json:"type"`
			ServiceAccount struct {
				ClientID string `json:"client_id"`
				Username string `json:"username"`
			} `json:"service_account"`
		}{
			AuthType: "jwt-auth",
			Internal: struct {
				AuthTime    int    `json:"auth_time"`
				CrossAccess bool   `json:"cross_access"`
				OrgID       string `json:"org_id"`
			}{
				AuthTime:    500,
				CrossAccess: false,
				OrgID:       "456",
			},
			OrgID: "456",
			Type:  "ServiceAccount",
			ServiceAccount: struct {
				ClientID string `json:"client_id"`
				Username string `json:"username"`
			}{
				ClientID: svc_account.ClientId,
				Username: svc_account.Username,
			},
		},
	}
	jsonData, _ := json.MarshalIndent(data, "", "  ")

	fmt.Printf("Setting X-RH-IDENTITY: %s\n", string(jsonData))
	return base64.StdEncoding.EncodeToString([]byte(jsonData))

}

func setRHIdentityHeader(req *http.Request) {
	auth_header := req.Header.Get("Authorization")

	if auth_header != "" {
		if strings.Contains(auth_header, "Basic") {

			user, pass, _ := req.BasicAuth()

			fmt.Printf("Authenticating with basic auth: %s:%s\n", user, pass)

			if svc_account, ok := serviceAccounts[user]; ok {
				req.Header.Set("X-RH-IDENTITY", serviceAccountToIentityHeader(svc_account))
			} else {	

				if account, ok := accounts[user]; ok {
					req.Header.Set("X-RH-IDENTITY", userToIentityHeader(account))
				} else {
					fmt.Printf("User not found: %s", user)
				}
			}

		} else if strings.Contains(auth_header, "Bearer") {
			reqToken := req.Header.Get("Authorization")
			splitToken := strings.Split(reqToken, "Bearer ")
			reqToken = splitToken[1]

			fmt.Printf("Authenticating with refresh token: %s\n", reqToken)

			if userID, ok := accessTokens[reqToken]; ok {
				req.Header.Set("X-RH-IDENTITY", userToIentityHeader(accounts[userID]))
			} else {
				fmt.Printf("Token not found: %s", reqToken)
			}
		}
	} else {
		fmt.Println("No auth header found.")
	}
}

func getEnv(key string, fallback string) string {
	if key, ok := os.LookupEnv(key); ok {
		return key
	}
	return fallback
}

func createHTTPClient(url string) *http.Client {
	// if fetching a tarball, do not follow redirects
	if strings.Contains(url, ".tar.gz") {
		return &http.Client{
			CheckRedirect: func(req *http.Request, via []*http.Request) error {
				return http.ErrUseLastResponse
			},
		}

	}
	return &http.Client{}
}

func isBrokenPipeError(err error) bool {
	if netErr, ok := err.(*net.OpError); ok {
		if sysErr, ok := netErr.Err.(*os.SyscallError); ok {
			if sysErr.Err == syscall.EPIPE {
				return true
			}
		}
	}
	return false
}

func isConnectionResetByPeer(err error) bool {
	if netErr, ok := err.(*net.OpError); ok {
		if sysErr, ok := netErr.Err.(*os.SyscallError); ok {
			if sysErr.Err == syscall.ECONNRESET {
				return true
			}
		}
	}
	return false
}

func isUseOfClosedNetworkConnection(err error) bool {
	return strings.Contains(err.Error(), "use of closed network connection")
}

func isWriteBrokenPipe(err error) bool {
	return strings.Contains(err.Error(), "write: broken pipe")
}

func isInvalidReadOnClosedBody(err error) bool {
	return strings.Contains(err.Error(), "invalid Read on closed Body")
}

func isEOFerror(err error) bool {
	if err == io.EOF {
		return true
	}
	return false
}

func retryHTTPRequest(client *http.Client, req *http.Request, maxRetries int) (*http.Response, error) {

    for name, values := range req.Header {
        // Each header can have multiple values, so we iterate through them.
        for _, value := range values {
            fmt.Printf("REQUEST_HEADER: %s: %s\n", name, value)
        }
    }

	for retry := 0; retry < maxRetries; retry++ {
		resp, err := client.Do(req)
		if err != nil {
			if isBrokenPipeError(err) {
				fmt.Printf("Retry attempt %d: Broken Pipe Error\n", retry+1)
				time.Sleep(1 * time.Second) // Wait before retrying
				continue
			}
			if isConnectionResetByPeer(err) {
				fmt.Printf("Retry attempt %d: Connection Reest by Peer Error\n", retry+1)
				time.Sleep(1 * time.Second) // Wait before retrying
				continue
			}
			if isUseOfClosedNetworkConnection(err) {
				fmt.Printf("Retry attempt %d: use of closed network connection\n", retry+1)
				time.Sleep(1 * time.Second) // Wait before retrying
				continue
			}
			if isWriteBrokenPipe(err) {
				fmt.Printf("Retry attempt %d: write broken pipe\n", retry+1)
				time.Sleep(1 * time.Second) // Wait before retrying
				continue
			}
			if isInvalidReadOnClosedBody(err) {
				fmt.Printf("Retry attempt %d: invalid read on closed body\n", retry+1)
				time.Sleep(1 * time.Second) // Wait before retrying
				continue
			}
			if isEOFerror(err) {
				fmt.Printf("Retry attempt %d: EOF error\n", retry+1)
				time.Sleep(1 * time.Second) // Wait before retrying
				continue
			}
			return nil, err
		}

		return resp, nil
	}

	return nil, fmt.Errorf("Exhausted all retry attempts")
}

func main() {
	fmt.Println("Starting insights proxy.")

	// define origin server URL
	urlToProxyTo, err := url.Parse(getEnv("UPSTREAM_URL", "http://localhost:5001"))
	proxyHost := getEnv("PROXY_HOST", "localhost")
	proxyPort := getEnv("PROXY_PORT", "8080")

	fmt.Printf("Listening on: %s\n", proxyPort)
	fmt.Printf("Proxying to: %s\n", urlToProxyTo)

	downloadUrlReg := regexp.MustCompile("\"download_url\":\"(http|https)://[^/]+")
	replacementURL := []byte(fmt.Sprintf("\"download_url\":\"http://%s:%s", proxyHost, proxyPort))

	if err != nil {
		log.Fatal("invalid origin server URL")
	}

	fmt.Println("")
	// taken from https://dev.to/b0r/implement-reverse-proxy-in-gogolang-2cp4
	reverseProxy := http.HandlerFunc(func(rw http.ResponseWriter, req *http.Request) {

        fmt.Printf("***********************************************************\n")
        fmt.Printf("STARTING NEW PROXY REQUEST ...\n")
        fmt.Printf("***********************************************************\n")

		// Handle the keycloak auth url
		if req.URL.Path == "/auth/realms/redhat-external/protocol/openid-connect/token" {
			getAccessToken(rw, req)
			fmt.Println("")
			return
		}

		// Set X-RH-IDENTITY header
		setRHIdentityHeader(req)

		fmt.Printf("req.Host: %s\n", req.Host)
		fmt.Printf("req.URL.Host: %s\n", req.URL.Host)
		fmt.Printf("req.URL.Scheme: %s\n", req.URL.Scheme)
		fmt.Printf("req.URL.Path: %s\n", req.URL.Path)
		fmt.Printf("urlToProxyTo.Host: %s\n", urlToProxyTo.Host)
		fmt.Printf("urlToProxyTo.Scheme: %s\n", urlToProxyTo.Scheme)

		// Rewrite the url on the incoming request and resend it
		req.Host = urlToProxyTo.Host
		req.URL.Host = urlToProxyTo.Host
		req.URL.Scheme = urlToProxyTo.Scheme
		req.RequestURI = ""
		req.URL.Path = strings.ReplaceAll(req.URL.Path, "//", "/")

		fmt.Printf("Proxying request to: %s\n", req.URL.RequestURI())

		client := createHTTPClient(req.URL.Path)
		maxRetries := 3
		upstreamServerResponse, err := retryHTTPRequest(client, req, maxRetries)

		if err != nil {
			fmt.Println("error ...")
			fmt.Println(err)
			rw.WriteHeader(http.StatusInternalServerError)
			_, _ = fmt.Fprint(rw, err)
			fmt.Println("")

			return
		}

		// if it's a 302 redirect, write the new url into the response headers ...
		headers := upstreamServerResponse.Header
		for key, values := range headers {
			for _, value := range values {
				fmt.Printf("RESPONSE HEADER %s: %s\n", key, value)
			}
		}
		fmt.Printf("STATUS CODE: %d\n", upstreamServerResponse.StatusCode)

		location := upstreamServerResponse.Header.Get("Location")
		if location != "" {
			rw.Header().Set("Location", location)
		}

		// replace any download urls that are found on the response so that they
		// get redirected through the proxy
		data, _ := ioutil.ReadAll(upstreamServerResponse.Body)
		modified := downloadUrlReg.ReplaceAll(data, replacementURL)

		fmt.Printf("MODIFIED DATA: %s\n", modified)

		// Write the response
		rw.WriteHeader(upstreamServerResponse.StatusCode)
		rw.Write(modified)

		fmt.Println("request complete")
		fmt.Println()
	})

	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%s", proxyPort), reverseProxy))
}
