Removal of existing permission system
- Viewsets no longer check to see if the user is in the system:partner-engineers group to determine if the user is an admin.
- Red Hat entitlements checks have been moved to DRF Access Policy
- Existing permission classes have been removed and replaced with DRF Access Policy permission classes.
