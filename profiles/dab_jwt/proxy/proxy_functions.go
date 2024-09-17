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
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v4"
	"github.com/google/uuid"
)

/*
	func containsString(list []string, str string) bool {
		for _, v := range list {
			if v == str {
				return true
			}
		}
		return false
	}
*/
func uniqueSortedStrings(input []string) []string {
	// First, sort the slice
	sort.Strings(input)

	// Then, create a new slice to hold unique values
	unique := []string{}

	// Loop through the sorted slice and add only unique values to the new slice
	for i, str := range input {
		if i == 0 || str != input[i-1] {
			unique = append(unique, str)
		}
	}

	return unique
}

func uniqueInts(nums []int) []int {
	if len(nums) == 0 {
		return nums
	}

	// Create a map to track unique integers
	uniqueMap := make(map[int]bool)
	for _, num := range nums {
		uniqueMap[num] = true
	}

	// Convert the map keys back to a slice
	uniqueList := make([]int, 0, len(uniqueMap))
	for num := range uniqueMap {
		uniqueList = append(uniqueList, num)
	}

	// Sort the slice
	sort.Ints(uniqueList)

	return uniqueList
}

func MaxOrDefault(nums []int) int {
	if len(nums) == 0 {
		return 1
	}

	maxVal := nums[0] // Assume the first element is the max initially
	for _, num := range nums {
		if num > maxVal {
			maxVal = num
		}
	}
	return maxVal
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

func GetTeamByName(teamname string) Team {
	for _, team := range teams {
		if team.Name == teamname {
			return team
		}
	}
	return Team{}
}

func GetUserByUserName(username string) User {
	//usersMutex.Lock()
	//defer usersMutex.Unlock()

	for _, user := range users {
		log.Printf("getuserbyusername %d,%s == %s ?", user.Id, user.Username, username)
		if user.Username == username {
			return user
		}
	}
	return User{}
}

// generateJWT generates a JWT for the user
func GenerateUserClaims(user User) (UserClaims, error) {

	log.Printf("generateclaims %s\n", user.Username)

	log.Printf("generateclaims %s\n", user.Username)
	//log.Printf("teams %s\n", teams)

	orgNameMap := make(map[string]Organization)
	for _, org := range orgs {
		orgNameMap[org.Name] = org
	}
	//log.Printf("orgmap %s\n", orgNameMap)

	// orgs that a team is part of but the user is not a member of
	nonMemberOrgs := []string{}

	uniqueOrgMap := make(map[int]bool)
	memberOrgs := []Organization{}
	adminOrgs := []Organization{}
	uniqueTeamMap := make(map[int]bool)
	memberTeams := []Team{}
	adminTeams := []Team{}
	globalRoles := []string{}

	// iterate through role_user_assignments ...
	for _, assignment := range roleUserAssignments {

		log.Printf("processing assignment %d\n", assignment.Id)

		if assignment.User != user.Id {
			log.Printf("\t ass-userid:%d != user-id:%d", assignment.User, user.Id)
			continue
		}
		roleId := assignment.RoleDefinition
		if roleDefinitions[roleId].Name == "Platform Auditor" {
			log.Printf("\tfound user assignment for platform auditor")
			globalRoles = append(globalRoles, "Platform Auditor")
			continue
		}

		if roleDefinitions[roleId].Name == "Team Member" || roleDefinitions[roleId].Name != "Team Admin" {

			thisteam := teams[assignment.ObjectId]
			log.Printf("\tFOUND TEAM %s\n", thisteam.Name)
			if !uniqueTeamMap[thisteam.Id] {
				uniqueTeamMap[thisteam.Id] = true
			}

			if roleDefinitions[roleId].Name == "Team Member" {
				memberTeams = append(memberTeams, thisteam)
			}

			if roleDefinitions[roleId].Name == "Team Admin" {
				adminTeams = append(adminTeams, thisteam)
			}

			thisorg := orgs[thisteam.Org]
			log.Printf("\tFOUND ORG %s\n", thisorg.Name)
			if !uniqueOrgMap[thisorg.Id] {
				uniqueOrgMap[thisorg.Id] = true
				memberOrgs = append(memberOrgs, thisorg)
			}

		}

		if roleDefinitions[roleId].Name == "Organization Member" || roleDefinitions[roleId].Name != "Organization Admin" {
			thisorg := orgs[assignment.ObjectId]
			log.Printf("\tFOUND ORG %s\n", thisorg.Name)
			if !uniqueOrgMap[thisorg.Id] {
				uniqueOrgMap[thisorg.Id] = true
				//memberOrgs = append(memberOrgs, thisorg)
			}

			if roleDefinitions[roleId].Name == "Organization Member" {
				memberOrgs = append(memberOrgs, thisorg)
			}

			if roleDefinitions[roleId].Name == "Organization Admin" {
				adminOrgs = append(adminOrgs, thisorg)
			}

		}

	}

	for _, assignment := range roleTeamAssignments {

		// is this for a team the user is a member of?
		thisteam := teams[assignment.Team]
		if !uniqueTeamMap[thisteam.Id] {
			continue
		}

		roleId := assignment.RoleDefinition
		if roleDefinitions[roleId].Name == "Platform Auditor" {
			log.Printf("\tfound user assignment for platform auditor")
			globalRoles = append(globalRoles, "Platform Auditor")
			continue
		}
	}

	// make a list of org structs for this user ...
	claimOrgObjectsIndex := map[string]int{}
	claimOrgObjects := []OrganizationObject{}
	claimTeamObjectsIndex := map[string]int{}
	claimTeamObjects := []TeamObject{}

	// iterate admin orgs
	for _, org := range adminOrgs {
		orgObj := OrganizationObject{
			AnsibleId: org.AnsibleId,
			Name:      org.Name,
		}
		exists := false
		for _, iorg := range claimOrgObjects {
			if iorg.Name == org.Name {
				exists = true
				break
			}
		}
		if !exists {
			claimOrgObjects = append(claimOrgObjects, orgObj)
			claimOrgObjectsIndex[org.Name] = len(claimOrgObjects) - 1
		}
	}

	// iterate member orgs
	for _, org := range memberOrgs {
		orgObj := OrganizationObject{
			AnsibleId: org.AnsibleId,
			Name:      org.Name,
		}
		exists := false
		for _, iorg := range claimOrgObjects {
			if iorg.Name == org.Name {
				exists = true
				break
			}
		}
		if !exists {
			claimOrgObjects = append(claimOrgObjects, orgObj)
			claimOrgObjectsIndex[org.Name] = len(claimOrgObjects) - 1
		}
	}

	// iterate admin teams
	for _, team := range adminTeams {
		orgName := orgs[team.Org].Name
		orgIx := claimOrgObjectsIndex[orgName]
		teamObj := TeamObject{
			AnsibleId: team.AnsibleId,
			Name:      team.Name,
			Org:       orgIx,
		}
		nonMemberOrgs = append(nonMemberOrgs, orgName)
		exists := false
		for _, iteam := range claimTeamObjects {
			if iteam.Name == team.Name {
				exists = true
				break
			}
		}
		if !exists {
			claimTeamObjects = append(claimTeamObjects, teamObj)
			claimTeamObjectsIndex[team.Name] = len(claimTeamObjects) - 1
		}
	}
	// iterate memberteams
	for _, team := range memberTeams {
		orgName := orgs[team.Org].Name
		orgIx := claimOrgObjectsIndex[orgName]
		teamObj := TeamObject{
			AnsibleId: team.AnsibleId,
			Name:      team.Name,
			Org:       orgIx,
		}
		nonMemberOrgs = append(nonMemberOrgs, orgName)
		exists := false
		for _, iteam := range claimTeamObjects {
			if iteam.Name == team.Name {
				exists = true
				break
			}
		}
		if !exists {
			claimTeamObjects = append(claimTeamObjects, teamObj)
			claimTeamObjectsIndex[team.Name] = len(claimTeamObjects) - 1
		}
	}

	objects := map[string]interface{}{
		"organization": claimOrgObjects,
		"team":         claimTeamObjects,
	}
	objectRoles := map[string]interface{}{}

	if len(claimOrgObjects) > 0 {
		if len(adminOrgs) > 0 {
			adminorgids := []int{}
			for _, org := range adminOrgs {
				ix := claimTeamObjectsIndex[org.Name]
				adminorgids = append(adminorgids, ix)
			}
			objectRoles["Organization Admin"] = ObjectRole{
				ContentType: "organization",
				Objects:     adminorgids,
			}
		}

		if len(memberOrgs) > 0 {
			memberorgids := []int{}
			for _, org := range memberOrgs {

				// was this inherited from a team?
				inherited := false
				for _, orgname := range nonMemberOrgs {
					if orgname == org.Name {
						inherited = true
						break
					}
				}
				if inherited {
					continue
				}

				ix := claimTeamObjectsIndex[org.Name]
				memberorgids = append(memberorgids, ix)
			}
			if len(memberorgids) > 0 {
				objectRoles["Organization Member"] = ObjectRole{
					ContentType: "organization",
					Objects:     memberorgids,
				}
			}
		}
	}

	if len(claimTeamObjects) > 0 {
		if len(adminTeams) > 0 {
			adminteamids := []int{}
			for _, team := range adminTeams {
				ix := claimTeamObjectsIndex[team.Name]
				adminteamids = append(adminteamids, ix)
			}
			objectRoles["Team Admin"] = ObjectRole{
				ContentType: "team",
				Objects:     adminteamids,
			}
		}

		if len(memberTeams) > 0 {
			memberteamids := []int{}
			for _, team := range memberTeams {
				ix := claimTeamObjectsIndex[team.Name]
				memberteamids = append(memberteamids, ix)
			}
			objectRoles["Team Member"] = ObjectRole{
				ContentType: "team",
				Objects:     memberteamids,
			}
		}
	}

	// finalize the global roles
	finalGlobalRoles := uniqueSortedStrings(globalRoles)

	// make the expiration time
	numericDate := jwt.NewNumericDate(time.Now().Add(time.Hour))
	unixTime := numericDate.Unix()

	claims := UserClaims{
		Version:     1,
		Iss:         "ansible-issuer",
		Aud:         "ansible-services",
		Expires:     unixTime,
		GlobalRoles: finalGlobalRoles,
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
		return User{}, fmt.Errorf("authorization header missing")
	}

	// The token normally comes in the format "Basic <base64encoded(username:password)>"
	if !strings.HasPrefix(authHeader, "Basic ") {
		return User{}, fmt.Errorf("invalid authorization method")
	}

	// Decode the base64 encoded credentials
	encodedCredentials := strings.TrimPrefix(authHeader, "Basic ")
	decodedCredentials, err := base64.StdEncoding.DecodeString(encodedCredentials)
	if err != nil {
		return User{}, fmt.Errorf("invalid base64 encoded credentials")
	}

	// Split the decoded string into username and password
	credentials := strings.SplitN(string(decodedCredentials), ":", 2)
	if len(credentials) != 2 {
		return User{}, fmt.Errorf("invalid credentials format")
	}

	username := credentials[0]
	user := GetUserByUserName(username)
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

func GetOrganizationById(orgid int) Organization {
	for _, org := range orgs {
		if org.Id == orgid {
			return org
		}
	}
	return Organization{}
}

func GetLastNumericPathElement(path string) int {
	// Split the path into components
	parts := strings.Split(strings.Trim(path, "/"), "/")

	// Get the last part of the path
	if len(parts) == 0 {
		return -1
	}
	lastPart := parts[len(parts)-1]

	// Check if the last part is numeric
	if num, err := strconv.Atoi(lastPart); err == nil {
		return num
	}

	// If not numeric, return nil
	return -1
}

func DeleteOrganization(org Organization) {
	DeleteUserAssignmentByObjectIdAndRoleNameSubstring(org.Id, "org")
	// delete all teams under this org
	for _, team := range teams {
		if team.Org == org.Id {
			DeleteTeam(team)
		}
	}
	// put it in the deleted entities map
	entity := DeletedEntityKey{
		ID:          org.Id,
		ContentType: "org",
	}
	deletedEntities[entity] = true
	delete(orgs, org.Id)
}

func DeleteTeam(team Team) {
	DeleteUserAssignmentByObjectIdAndRoleNameSubstring(team.Id, "team")
	entity := DeletedEntityKey{
		ID:          team.Id,
		ContentType: "team",
	}
	deletedEntities[entity] = true
	delete(teams, team.Id)
}

func DeleteUser(user User) {
	DeleteUserAssignmentsByUserid(user.Id)
	entity := DeletedEntityKey{
		ID:          user.Id,
		ContentType: "user",
	}
	deletedEntities[entity] = true
	delete(users, user.Id)
}

func GetRoleDefinitionById(id int) RoleDefinition {
	for _, roledef := range roleDefinitions {
		if roledef.Id == id {
			return roledef
		}
	}
	return RoleDefinition{}
}

func DeleteUserAssignmentsByUserid(userid int) {
	idsToDelete := []int{}

	for _, assignment := range roleUserAssignments {
		if assignment.User != userid {
			continue
		}
		idsToDelete = append(idsToDelete, assignment.Id)
	}

	uniqueIds := uniqueInts(idsToDelete)

	for _, idToDelete := range uniqueIds {
		log.Printf("FIXME delete %d", idToDelete)
		entity := DeletedEntityKey{
			ID:          idToDelete,
			ContentType: "role_user_assignment",
		}
		deletedEntities[entity] = true
		delete(roleUserAssignments, idToDelete)
	}
}

func DeleteUserAssignmentByObjectIdAndRoleNameSubstring(object_id int, substring string) {

	idsToDelete := []int{}

	for _, assignment := range roleUserAssignments {
		if assignment.ObjectId != object_id {
			continue
		}
		roledef := GetRoleDefinitionById(assignment.RoleDefinition)
		if !strings.Contains(strings.ToLower(roledef.Name), strings.ToLower(substring)) {
			continue
		}
		idsToDelete = append(idsToDelete, assignment.Id)
	}

	uniqueIds := uniqueInts(idsToDelete)

	for _, idToDelete := range uniqueIds {
		log.Printf("FIXME delete %d", idToDelete)
		entity := DeletedEntityKey{
			ID:          idToDelete,
			ContentType: "role_user_assignment",
		}
		deletedEntities[entity] = true
		delete(roleUserAssignments, idToDelete)
	}
}
