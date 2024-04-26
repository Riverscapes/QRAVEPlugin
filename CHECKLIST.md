# Deployment Checklist

There are a number of steps that have to be performed in the correct order for this plugin to deploy correctly. 

NEVER WORK DIRECTLY ON THE MASTER BRANCH

1. Commit and push everything to git
2. increment the version number in `__version__.py`
3. Do a compile of all the UI and resources and commit that `pb_tool compile`
4. Make sure all dependencies are in place by running `sh ./scripts/installDeps.sh`
5. Run the `deploy.py` script once and test the local version of the plugin
6. Do a code review and a pull request to get this onto the master branch
7. Tag the commit in git with the version number
8. Run `deploy.py` again. This will produce the zip file to upload
9. Test again
10. Go to https://plugins.qgis.org/plugins/riverscapes_viewer/ and log in. You should be able to manage and add a new version from there.
11. Go make a release on github. This might be redundant but....  TBA