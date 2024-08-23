package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v4"
	"github.com/google/uuid"
)

func containsString(list []string, str string) bool {
	for _, v := range list {
		if v == str {
			return true
		}
	}
	return false
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
func GenerateUserClaims(argUser User) (UserClaims, error) {

	log.Printf("generateclaims %s\n", argUser.Username)

	/*
		orgsMutex.Lock()
		defer orgsMutex.Unlock()

		teamsMutex.Lock()
		defer teamsMutex.Unlock()

		usersMutex.Lock()
		defer usersMutex.Unlock()

		roleDefinitionsMutex.Lock()
		defer roleDefinitionsMutex.Unlock()

		roleUserAssignmentsMutex.Lock()
		defer roleUserAssignmentsMutex.Unlock()
	*/

	log.Printf("generateclaims %s\n", argUser.Username)
	log.Printf("teams %s\n", teams)

	/*
	   oData1, _ := json.MarshalIndent(orgs, "", "  ")
	   oString1 := string(oData1)
	   fmt.Println(oString1)
	*/

	user := users[argUser.Username]

	// make a list of org structs for this user ...
	//userOrgs := []Organization{}
	//userTeams := []TeamObject{}

	// what orgs is this user a direct member of? ...
	//localOrgMap := map[string]int{}

	/*
		counter := -1
		for _, orgName := range user.Organizations {
			counter += 1
			localOrgMap[orgName] = counter
			fmt.Println("# ADD ORG", orgName, "TO USERORGS ..")

			thisOrg, ok := orgs[orgName]
			if !ok {
				fmt.Println(orgName, "was not in the orgs map!!!")
				panic("FUDGE!!!")
			}

			userOrgs = append(userOrgs, thisOrg)

		}
	*/

	/*
		// what orgs is this user an indirect member of? ...
		for _, teamCodeName := range user.Teams {
			team := teams[teamCodeName]
			orgName := team.Org
			fmt.Println("# TEAM:", team, "ORG:", orgName)

			// check if related org is in the list+map ...
			found := false
			highestIndex := -1
			for orgName2, orgIndex2 := range localOrgMap {
				fmt.Println("\t#ORG2", fmt.Sprintf("ix: %d", orgIndex2), "name:", orgName2)
				if orgName2 == orgName {
					found = true
					break
				}
				if highestIndex < orgIndex2 {
					highestIndex = orgIndex2
				}
			}

			// add it to the list+map if not already there ...
			if found == false {
				newIndex := highestIndex + 1
				localOrgMap[orgName] = newIndex
				userOrgs = append(userOrgs, orgs[orgName])
			}
		}
	*/

	/*
		for _, team := range user.Teams {
			orgName := teams[team].Org
			orgIndex := localOrgMap[orgName]
			userTeams = append(userTeams, TeamObject{
				AnsibleId: teams[team].AnsibleId,
				Name:      team,
				Org:       orgIndex,
			})
		}
	*/

	// map out roledefintions by id:name ...
	roleMap := make(map[int]RoleDefinition)
	for _, role := range roleDefinitions {
		roleMap[role.Id] = role
	}

	orgIdMap := make(map[int]Organization)
	for _, org := range orgs {
		orgIdMap[org.Id] = org
	}
	log.Printf("orgmap %s\n", orgIdMap)

	orgNameMap := make(map[string]Organization)
	for _, org := range orgs {
		orgNameMap[org.Name] = org
	}
	log.Printf("orgmap %s\n", orgNameMap)

	teamMap := make(map[int]Team)
	for _, team := range teams {
		teamMap[team.Id] = team
	}
	log.Printf("teammap %s\n", teamMap)

	uniqueOrgMap := make(map[int]bool)
	memberOrgs := []Organization{}
	uniqueTeamMap := make(map[int]bool)
	memberTeams := []Team{}

	// iterate through role_user_assignments ...
	for _, assignment := range roleUserAssignments {

		log.Printf("processing assignment %s\n", assignment)

		if assignment.User != argUser.Id {
			log.Printf("\t ass-userid:%d != user-id:%d", assignment.User, argUser.Id)
			continue
		}
		roleId := assignment.RoleDefinition
		if roleMap[roleId].Name != "Team Member" {
			log.Printf("\tNOT A TEAM MEMBER ASSIGNMENT!\n")
			continue
		}

		if _, exists := teamMap[assignment.ObjectId]; !exists {
			log.Printf("\tDID NOT FIND TEAMID %d", assignment.ObjectId)
			continue
		}

		thisteam := teamMap[assignment.ObjectId]
		log.Printf("\tFOUND TEAM %s\n", thisteam)
		if !uniqueTeamMap[thisteam.Id] {
			uniqueTeamMap[thisteam.Id] = true
			memberTeams = append(memberTeams, thisteam)
		}

		thisorg := orgNameMap[thisteam.Org]
		log.Printf("\tFOUND ORG %s\n", thisorg)
		if !uniqueOrgMap[thisorg.Id] {
			uniqueOrgMap[thisorg.Id] = true
			memberOrgs = append(memberOrgs, thisorg)
		}

		// need to put the org in the orglist and the localorgmap

		// need to put the team in the teamlist and the localteammap

		/*
			for _, team := range teams {

				log.Printf("\tcheck team %s\n", team)

				log.Printf("teamid:%d == object_id:%d ???\n", team.Id, assignment.ObjectId)
				if team.Id != assignment.ObjectId {
					log.Printf("\t\tdoes not match objectID")
					continue
				}
				log.Printf("\t\tmatched objectID")

				//log.Printf("\tprocessing team %s\n", team)

				orgIdInt, _ := strconv.Atoi(team.Org)

				// find the org ..
				var foundOrg *Organization
				for _, org := range orgs {
					if org.Id == orgIdInt {
						foundOrg = &org
						break
					}
				}

				orgIndex := -1
				if _, exists := localOrgMap[foundOrg.Name]; !exists {
					userOrgs = append(userOrgs, *foundOrg)
					orgIndex = len(userOrgs) - 1
					localOrgMap[foundOrg.Name] = orgIndex
				} else {
					orgIndex = localOrgMap[foundOrg.Name]
				}

				userTeams = append(userTeams, TeamObject{
					AnsibleId: team.AnsibleId,
					Name:      team.Name,
					Org:       orgIndex,
				})
			}
		*/
	}

	// make a list of org structs for this user ...
	//userOrgs := []Organization{}
	//userTeamObjects := []TeamObject{}
	claimOrgObjectsIndex := map[string]int{}
	claimOrgObjects := []OrganizationObject{}
	claimTeamObjectsIndex := map[string]int{}
	claimTeamObjects := []TeamObject{}

	/*
		oData, _ := json.MarshalIndent(userOrgs, "", "  ")
		oString := string(oData)
		//fmt.Println(oString)
		log.Printf("orgstring: %s\n", oString)
	*/

	for ix, org := range memberOrgs {
		orgObj := OrganizationObject{
			AnsibleId: org.AnsibleId,
			Name:      org.Name,
		}
		claimOrgObjectsIndex[org.Name] = ix
		claimOrgObjects = append(claimOrgObjects, orgObj)
	}

	for ix, team := range memberTeams {
		orgIx := claimOrgObjectsIndex[team.Org]
		teamObj := TeamObject{
			AnsibleId: team.AnsibleId,
			Name:      team.Name,
			Org:       orgIx,
		}
		claimTeamObjectsIndex[team.Name] = ix
		claimTeamObjects = append(claimTeamObjects, teamObj)
	}

	objects := map[string]interface{}{
		"organization": claimOrgObjects,
		"team":         claimTeamObjects,
	}
	objectRoles := map[string]interface{}{}
	/*
		if len(claimTeamObjects) > 0 {
			objectRoles["Team Member"] = ObjectRole{
				ContentType: "team",
				Objects:     []int{0},
			}
		}
	*/
	if len(claimTeamObjects) > 0 {
		teamids := []int{}
		for ix, _ := range claimTeamObjects {
			teamids = append(teamids, ix)
		}
		objectRoles["Team Member"] = ObjectRole{
			ContentType: "team",
			Objects:     teamids,
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

	return claims, nil
}

// generateJWT generates a JWT for the user
func generateJWT(argUser User) (string, error) {

	claims, _ := GenerateUserClaims(argUser)

	jsonData, _ := json.MarshalIndent(claims, "", "  ")
	jsonString := string(jsonData)

	log.Printf("-------------------------------------\n")
	log.Printf("Created JWT for %s ...\n", argUser.Username)
	log.Println(jsonString)
	log.Printf("-------------------------------------\n")

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

func GetRequestUser(r *http.Request) (User, error) {
	// Get the Authorization header
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		return User{}, fmt.Errorf("Authorization header missing")
	}

	// The token normally comes in the format "Basic <base64encoded(username:password)>"
	if !strings.HasPrefix(authHeader, "Basic ") {
		return User{}, fmt.Errorf("Invalid authorization method")
	}

	// Decode the base64 encoded credentials
	encodedCredentials := strings.TrimPrefix(authHeader, "Basic ")
	decodedCredentials, err := base64.StdEncoding.DecodeString(encodedCredentials)
	if err != nil {
		return User{}, fmt.Errorf("Invalid base64 encoded credentials")
	}

	// Split the decoded string into username and password
	credentials := strings.SplitN(string(decodedCredentials), ":", 2)
	if len(credentials) != 2 {
		return User{}, fmt.Errorf("Invalid credentials format")
	}

	username := credentials[0]
	user := users[username]
	return user, nil
}

func GetOrganizationByName(orgname string) Organization {
	for _, org := range orgs {
		if org.Name == orgname || org.CodeName == orgname {
			return org
		}
	}
	return Organization{}
}
