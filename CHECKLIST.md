# Deployment Checklist

There are a number of steps that have to be performed in the correct order for this plugin to deploy correctly. 

NEVER WORK DIRECTLY ON THE MASTER BRANCH

1. Commit and push everything to git
2. increment the version number in `__version__.py`
3. Do a compile of all the UI and resources and commit that `pb_tool compile`
4. Run the `deploy.py` script once and test the local version of the plugin
5. Do a code review and a pull request to get this onto the master branch
6. Tag the commit in git with the version number
7. Run `deploy.py` again. This will produce the zip file to upload