### All of these should be tested on windows and OSX:

### Authentication

- [X] Pre-authed used opens form
- [X] Unauthed users opens form
- [X] Authentication fails
- [X] Authentication times-out (1 minute)
- [X] Authed user resets auth with "reset" button

###  New Project Upload

- [X] SUCCESS: New Project is uploaded to ORG as PUBLIC
  - [X] Uploaded project can be viewed in Data exchange
- [X] SUCCESS: Exisiting project is uploaded as new
- [ ] SUCCESS: New Project is uploaded to USER 
- [X] SUCCESS: New Project is uploaded PRIVATE
- [X] SUCCESS: New Project is uploaded SECRET
- [ ] SUCCESS: New Project is uploaded with TAGS
- [ ] FAIL: Project fails validation
  - [X] Broken XML, Malformed XML
  - [ ] Missing files
  - [ ] Permissions issues

### Modify Project

- [ ] Existing project can be visited in Data Exchange
- [ ] FAIL: Project has been deleted remotely
- [ ] FAIL: Project has been modified remotely since this change
- [ ] SUCESS: Existing ORG project is modified
  - [ ] Only new files uploaded
  - [ ] Deleted files are deleted
  - [ ] Deleted files are not deleted when NoDelete is set
- [ ] SUCCESS: Existing USER project is modified
- [ ] SUCCESS: Tags are changed during upload

### Misc and Edge cases:

- [ ] SUCCESS: Upload multiple projects open in the Viewer. Can the dialog switch between them?
- [X] View log button works
- [ ] SUCCESS: New project is canceled mid-upload and can be started again
- [ ] Form can be closed and opened again without losing functionality
