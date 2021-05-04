# Deployment Checklist

There are a number of steps that have to be performed in the correct order for this plugin to deploy correctly. 

NEVER WORK DIRECTLY ON THE MASTER BRANCH

1. Commit and push everything to git
2. increment the version number in `__version__.py`
2. Do a compile of all the UI and resources and commit that
3. Do a code review and a pull request to get this onto the master branch
4. Tag the commit in git with the version number