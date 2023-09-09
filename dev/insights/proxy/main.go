package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"math/rand"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strings"
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

func setRHIdentityHeader(req *http.Request) {
	auth_header := req.Header.Get("Authorization")

	if auth_header != "" {
		if strings.Contains(auth_header, "Basic") {
			user, pass, _ := req.BasicAuth()

			fmt.Printf("Authenticating with basic auth: %s:%s\n", user, pass)

			if account, ok := accounts[user]; ok {
				req.Header.Set("X-RH-IDENTITY", userToIentityHeader(account))
			} else {
				fmt.Printf("User not found: %s", user)
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

    if strings.Contains(url, ".tar.gz") {
        return &http.Client{
            CheckRedirect: func(req *http.Request, via []*http.Request) error {
                return http.ErrUseLastResponse
            },
        }

    }

    //return &http.Client{}
    //return &http.DefaultClient
    return &http.Client{}
}

func main() {
	fmt.Println("Staring insights proxy.")

	// define origin server URL
	urlToProxyTo, err := url.Parse(getEnv("UPSTREAM_URL", "http://localhost:5001"))
	proxyPort := getEnv("PROXY_PORT", "8080")

	fmt.Printf("Listening on: %s\n", proxyPort)
	fmt.Printf("Proxying to: %s\n", urlToProxyTo)

	downloadUrlReg := regexp.MustCompile("\"download_url\":\"(http|https)://[^/]+")
	replacementURL := []byte(fmt.Sprintf("\"download_url\":\"http://localhost:%s", proxyPort))

	if err != nil {
		log.Fatal("invalid origin server URL")
	}

	fmt.Println("")
	// taken from https://dev.to/b0r/implement-reverse-proxy-in-gogolang-2cp4
	reverseProxy := http.HandlerFunc(func(rw http.ResponseWriter, req *http.Request) {

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

        // fixme ...
        // change http://localhost:11651 to http://pminio:8000

        fmt.Printf("Proxying request to: %s\n", req.URL.RequestURI())

        /*
        client := &http.Client{
            CheckRedirect: func(req *http.Request, via []*http.Request) error {
                return http.ErrUseLastResponse
            },
        }
        */

        client := createHTTPClient(req.URL.Path)

		//upstreamServerResponse, err := http.DefaultClient.Do(req)
		upstreamServerResponse, err := client.Do(req)

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
                fmt.Printf("HEADER %s: %s\n", key, value)
            }
        }

        location := upstreamServerResponse.Header.Get("Location")
        if location != "" {
            rw.Header().Set("Location", location)
        }

		// replace any download urls that are found on the response so that they
		// get redirected through the proxy
		data, _ := ioutil.ReadAll(upstreamServerResponse.Body)
		modified := downloadUrlReg.ReplaceAll(data, replacementURL)

		// Write the response
		rw.WriteHeader(upstreamServerResponse.StatusCode)
		rw.Write(modified)

        fmt.Println("request complete")
		fmt.Println()
	})

	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%s", proxyPort), reverseProxy))
}