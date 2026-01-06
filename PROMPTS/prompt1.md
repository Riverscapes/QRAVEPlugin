This is a QGIS plugin that renders a project.rs.xml file into a tree and allows the user to add it to the map

I need a new feature that should get its own button in the toolbar next to "Open Riverscapes Project" Called "Open Remote Project" and use the same icon.

When clicked it should open a dialog that allows the user to enter a URL or a project id (the ).

The GraphQL query necessary along with a sample output response is here:
/Users/matt/Work/Git/Riverscapes/QRAVEPlugin/PROMPTS/webRaveQuery.md

The difference is that instead of building the tree from the XML file we parse it from the flat GQL response using the "tree" field where there are leaves and branches and pid means parent id.

I want to render exactly the same tree as the current QGIS plugin does but I want to distinguish it with a different icon so I can tell the remote project from the local project. The tree structure should be identical though. 

so here's the workflow I want:

1. User clicks "Open Remote Project" button
2. User enters a project id or URL (the project id can be stripped from the URL since it's just the guid at the end of https://data.riverscapes.net/p/4dd028c6-3e9f-4b14-a317-fe74903ed279/)
3. Plugin makes a GraphQL query to the Riverscapes API using webRaveQuery.md as an example. You will need to authenticate but the upload workflow in this plugin shows you how to do that.
4. Plugin parses the response and builds a tree next to existing projects in the QRave dock widget so it shows up as just another project.

For now do not worry about context menus or actions. we will tackle that later.


--------------

Ok, now I need to wire up the "View Layer Metadata" actions. We should be able to get these from the webRaveProject query and just reformat it to be whatever the project currently expects.

Also the "Browse Folder" action for remote projects should say "Browse Remote Data Exchange" and should open the Data Exchange page for that project to the datasets subpage like this: https://data.riverscapes.net/p/ac104f27-93b7-4e47-b279-7a7dad8ccf1d/datasets