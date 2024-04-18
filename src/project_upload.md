### All of these should be tested on windows and OSX:

### Form load and Authentication

- [X] Pre-authed used opens form
- [X] Unauthed users opens form
- [X] Authentication fails
- [X] Authentication times-out (1 minute)
- [X] When multiple projects open in viewer dialog shows the correct one.
- [X] When multiple projects open in viewer cancelling and re-opening another shows the right one
- [X] Authed user resets auth with "reset" button

###  New Project Upload

- [X] SUCCESS: New Project (No Warehouse tag) is uploaded to ORG as PUBLIC
- [X] SUCCESS: Uploaded project can be viewed in Data exchange
- [X] SUCCESS: Exisiting project (with Warehouse tag) is uploaded as new
- [X] SUCCESS: New Project is uploaded to USER 
- [X] SUCCESS: New Project is uploaded PRIVATE
- [X] SUCCESS: New Project is uploaded SECRET
- [ ] SUCCESS: New Project is uploaded with TAGS
- [X] SUCCESS: Uploading files > 50Mb
- [ ] SHOULD_FAIL: Project fails validation
  - [X] Broken XML, Malformed XML
  - [X] Missing files
  - [ ] Permissions issues


### Modify Project

- [X] Existing project can be visited in Data Exchange
- [ ] SHOULD_FAIL: Project has been deleted remotely
- [ ] SHOULD_FAIL: Project has been modified remotely since this change
- [X] SUCESS: Existing ORG project is modified
  - [X] Only new files uploaded
  - [ ] Deleted files are deleted
  - [ ] Deleted files are not deleted when NoDelete is set
- [X] SUCCESS: Existing USER project is modified
- [ ] SUCCESS: Uploading files > 50Mb
- [X] SUCCESS: Unchanged Files < 50Mb are detected as existing and skipped
- [ ] SUCCESS: Unchanged Files > 50Mb are detected as existing and skipped
- [ ] SUCCESS: Tags are changed during upload

### Misc and Edge cases:

- [X] View log button works
- [X] SUCCESS: New project is canceled mid-upload
- [X] SUCCESS: Cancelled project can be restarted successfully
- [X] SHOULD_FAIL: Refuse to upload project from different api
- [X] SHOULD_FAIL: Refuse to upload project with bad project id
- [X] Form can be closed and opened again without losing functionality
