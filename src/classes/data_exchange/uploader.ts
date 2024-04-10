

// const MAX_WAIT_TIME = 1000 * 60 * 40 // 4 minutes
// const WAIT_INTERVAL = 1000 * 5 // 5 seconds


  // Look for a project XML filepath and bail if we don't find one
  // DO some checking on the file names. make sure there's a project file


  // Fetch all files and filter out any hidden ones
  // Walk through the folder and find all files inside the project directory


  // If this is designated as a new project then remove the <Warehouse> tag for validation

  // THis is the final arbiter of whether we are doing an update or not

  // Check for a business logic file and make sure to filter that out. 

  // Calculate local Etags for all files

  // RUN THe validation and get the results. WE'll need some sort of output if there are errors. Popup and console for now

  // 2. requestUploadProject(projectId: String, files: [String!], etags: [String!]): UploadProjectRequest
  // This will give us the ID for the new project

  // Sort the files based on what we're going to do to them
  // const fileOpDict: { create: string[]; update: string[]; delete: string[]; ignore: string[] }
  // Summary of what we're going to do. The initial version will just be numbers

  // CONFIRMATION DIALOG: This is happening. Are you sure?
  // call requestUploadProjectFileUrls(projectId: String, files: [String!], etags: [String!]): UploadProjectRequest
  // Then map each file in the result to the file in the queue

  // KICK OFF THE UPLOADER. Wait for it to finish
  
  // CALL THE FINALIZE API ENDPOINT

  // Poll the CheckUpload Query until success comes back every 5 seconds
  // WHILE LOOP. Wait 5 minutes maximum

  // If we succeeded then we need to get the new Project XML file
  // DOWNLOAD THE NEW PROJECT XML