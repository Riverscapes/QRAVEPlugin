// import fs from 'fs'
// import config from '../config'
// import path from 'path'
// import colors from 'colors'
// import { CLIActionProps, FileQueueItemInterface } from '../types'
// import { confirm, sleep, walkSync } from '../lib/cliUtils'
// import { calculateEtag } from '../lib/etag'
// import { getLogger } from '../lib/logging'
// import {
//   UPLOADS,
//   OwnerInput,
//   OwnerInputTypesEnum,
//   ProjectXML,
//   UploadProjectFileUrls,
//   JobStatusObj,
//   RequestUploadProject,
//   RequestUploadProjectFilesUrl,
//   FinalizeProjectUpload,
//   ProjectVisibilityEnum,
//   RequestUploadProjectQuery,
//   CheckUpload,
//   CheckUploadQuery,
//   JobStatusEnum,
//   DownloadFile,
//   DownloadFileQuery,
//   PROJECT_FILE,
// } from '@riverscapes/common'
// import { downloadFile as downloadFileFunc } from '../lib/streamHelpers'
// import { validation } from '../lib/validation'
// import FileQueue from '../lib/FileQueue'
// import { uploadFile, uploadMultiPartFile } from '../lib/fileUpload'
// import log from 'loglevel'
// import { GQLApi } from '../api'

// const MAX_WAIT_TIME = 1000 * 60 * 40 // 4 minutes
// const WAIT_INTERVAL = 1000 * 5 // 5 seconds

// async function upload(props: CLIActionProps, api: GQLApi): Promise<void> {
//   const logger = getLogger()
//   const { opts, args } = props

//   const projectPath = path.resolve(args.project as string)
//   const whProjFileName = api.warehouseInfo?.projectFile || 'project.rs.xml'

//   if (opts.user && opts.org) throw new Error('You cannot use both --org and --user. Choose which one to upload as.')
//   if (opts.user && (!api.machineAuth || !api.machineAuth.clientId || !api.machineAuth.secretId))
//     throw new Error('You must be authenticated as a machine user delegate an upload to another user')

//   // Make sure the tags are ok
//   let tags: string[] = null
//   const optsTags = ((opts.tags as string) || '').split(',') as string[]
//   if (optsTags && Array.isArray(optsTags)) {
//     try {
//       tags = optsTags.filter((t) => !!t && t.length > 0).map((t) => t.trim())
//     } catch {
//       throw new Error('Tags were specified but not in the right format')
//     }
//   }

//   // Is this a valid project folder
//   logger.title(`RSCli Upload: ${new Date().toString()}`)

//   // Look for a project XML filepath and bail if we don't find one
//   let projFileXMLPath = projectPath
//   let projDir = path.dirname(projectPath)
//   if (projFileXMLPath.endsWith(whProjFileName)) {
//     if (!fs.existsSync(projFileXMLPath)) throw new Error(`Could not find a project file at: ${projFileXMLPath}`)
//   } else {
//     projFileXMLPath = path.join(projectPath, whProjFileName)
//     projDir = projectPath
//     if (!fs.existsSync(projFileXMLPath)) throw new Error(`Could not find a project file at: ${projFileXMLPath}`)
//   }
//   const projFileXMLraw = fs.readFileSync(projFileXMLPath, { encoding: 'utf8' }).toString()
//   const parsedXML = new ProjectXML(projFileXMLraw)
//   log.debug('Successfully parsed XML')

//   // Fetch all files and filter out any hidden ones
//   const absFilePaths = walkSync(projDir, config.fileIgnore, config.fileWarn)

//   // Detect the project type
//   const projType = parsedXML.getProjectType()
//   log.debug('Project Type', projType)

//   // If this is designated as a new project then remove the <Warehouse> tag for validation
//   if (opts.new) {
//     logger.info('Removing Warehouse tag for validation')
//     parsedXML.removeWarehouseEl()
//   }

//   const oldWHTag = parsedXML.getWarehouseEl()
//   const projectMeta = parsedXML.getProjectMeta()

//   if ((opts.org || opts.user) && oldWHTag) {
//     throw new Error(
//       'You cannot use the --org or --user flags when updating a project that has already been uploaded. Use the --new flag to force creation of a new project.'
//     )
//   }

//   // THis is the final arbiter of whether we are doing an update or not
//   const isNew = opts.new || !oldWHTag

//   // Check for a business logic file
//   const businessLogicFile = `${projType}.xml`
//   const businessLogicAbsPath = path.join(projDir, businessLogicFile)
//   const businessLogicFileIndex = absFilePaths.indexOf(businessLogicAbsPath)
//   if (businessLogicFileIndex > -1) {
//     const includeBLogic = await confirm(
//       `Businesslogic file found: ${businessLogicFile}. Include in upload?`,
//       !args.input,
//       false
//     )

//     if (!includeBLogic) {
//       logger.info(`Skipping file: ${businessLogicAbsPath}`)
//       absFilePaths.splice(businessLogicFileIndex, 1)
//     }
//   }

//   // Create our relative paths and etags for validation
//   // Compare the two folders and get a coherent diff
//   logger.info('Calculating local ETAG hashes', config)
//   const relFilePaths = absFilePaths.map((absPath) => path.relative(projDir, absPath))
//   const etagArr = await Promise.all(
//     absFilePaths.map((fpath) =>
//       calculateEtag(fpath, UPLOADS.MULTIPART_CHUNK_SIZE, UPLOADS.MULTIPART_THRESHOLD).then((data) => {
//         log.debug('Calculated Etag', fpath)
//         return data
//       })
//     )
//   )
//   const etags = etagArr.map(({ etag }) => etag)
//   const sizes = etagArr.map(({ size }) => size)

//   let owner: OwnerInput | null = null
//   if (opts.org) owner = { id: opts.org as string, type: OwnerInputTypesEnum.Organization }
//   else if (opts.user) owner = { id: opts.user as string, type: OwnerInputTypesEnum.User }
//   const prettyOldXML = await parsedXML._toString()
//   const valid = await validation(api, opts, prettyOldXML, relFilePaths, owner)
//   if (!valid) {
//     logger.info('Exiting...')
//     throw new Error('Project validation failed')
//   }
//   logger.success('Project Validated Successfully')

//   // 2. requestUploadProject(projectId: String, files: [String!], etags: [String!]): UploadProjectRequest
//   logger.info(`Project is ${isNew ? 'NEW' : 'UPDATE'}. Requesting upload...`)
//   const {
//     data: {
//       requestUploadProject: { newId, create, delete: deletions, token, update },
//     },
//   } = await api
//     .query<RequestUploadProjectQuery>({
//       query: RequestUploadProject,
//       variables: {
//         projectId: isNew ? null : oldWHTag.id,
//         // token, // Only useful if we want to retrieve this same download again later
//         files: relFilePaths,
//         etags,
//         sizes,
//         noDelete: !opts.delete,
//         tags: tags ? tags.map((t) => t.trim()) : [],
//         owner,
//         visibility: opts.visibility as ProjectVisibilityEnum,
//       },
//     })
//     .catch((err) => {
//       throw new Error('API request for project failed')
//     })
//   logger.success(`API request for ${isNew ? 'NEW' : 'UPDATE'} project succeeded`)

//   // Set the Project ID:
//   if (newId) {
//     logger.info(`${isNew ? 'New' : 'Existing'} Project ID: ${newId}`)
//   }
//   if (!newId) throw new Error('Project ID not set. Something went wrong.')

//   // Sort the files based on what we're going to do to them
//   const fileOpDict: { create: string[]; update: string[]; delete: string[]; ignore: string[] } = relFilePaths.reduce(
//     (acc, relFilePath) => {
//       if (create.indexOf(relFilePath) > -1) acc.create.push(relFilePath)
//       else if (update.indexOf(relFilePath) > -1) acc.update.push(relFilePath)
//       else acc.ignore.push(relFilePath)
//       return acc
//     },
//     { create: [], update: [], delete: deletions, ignore: [] }
//   )

//   const files2Upload = fileOpDict.create.concat(fileOpDict.update)

//   /**
//    * Here's our confirm dialog
//    */
//   if (!isNew && files2Upload.length === 0 && fileOpDict.delete.length === 0 && fileOpDict.ignore) {
//     logger.info('Project is the same as the one online. Nothing to do. Exiting')
//     return
//   }
//   const titleStr = `[RSCLI] Upload ${isNew ? colors.green('NEW') : colors.yellow('EXISTING')} ${colors.bold(
//     projType
//   )} project with id: ${colors.blue(newId)} `
//   const tagStr = '\n     Tags: ' + (tags ? colors.white.bgGreen(tags.join(',')) : '<none>')
//   logger.title(titleStr + tagStr)
//   const metaStr = opts.verbose
//     ? `\n     Project Meta: ${projectMeta.map(({ key, value }) => `${colors.yellow(key)}: ${colors.white(value)}`)
//         .join('\n        ')}`
//     : `(${projectMeta.length} metadata key/value pairs)`
//   logger.info(metaStr)
//   logger.info(`  - Local files to upload: ${files2Upload.length}  (new or changed)`)
//   if (opts.verbose) {
//     files2Upload.forEach((origPath) => logger.info(colors.green(`        ${origPath}`)))
//   }
//   logger.info(`  - Remote files to delete: ${fileOpDict.delete.length}`)
//   if (opts.verbose) {
//     fileOpDict.delete.forEach((pathStr) => logger.info(colors.red(`        ${pathStr}`)))
//   }
//   logger.info(`  - Files to skip:   ${fileOpDict.ignore.length} (unchanged)`)
//   if (opts.verbose) {
//     fileOpDict.ignore.forEach((pathStr) => logger.info(colors.yellow(`        ${pathStr}`)))
//   }

//   const startUpload = await confirm('Start uploading?', !opts.input, true)
//   if (!startUpload) return Promise.reject('Exiting without uploading')

//   // 3. requestUploadProjectFileUrls(projectId: String, files: [String!], etags: [String!]): UploadProjectRequest
//   const {
//     data: { requestUploadProjectFilesUrl },
//   } = (await api.query({
//     query: RequestUploadProjectFilesUrl,
//     variables: {
//       token,
//       files: files2Upload, // TODO: Paginate here if there are too many
//     },
//   })) as { data: { requestUploadProjectFilesUrl: UploadProjectFileUrls[] } }

//   logger.debug('API request for signed file urls succeeded')

//   // transform  our requestUploadProjectFilesUrl into FileQueueItemInterface
//   const uploadfiles = requestUploadProjectFilesUrl.map<FileQueueItemInterface>(({ relPath, urls }) => {
//     const absFilePath = absFilePaths.find((f) => f.endsWith(relPath))
//     if (!absFilePath) throw new Error(`Could not find file: ${relPath}`)
//     return {
//       urls,
//       pathAbs: absFilePath,
//       update: fileOpDict.update.indexOf(relPath) > -1,
//       origPath: relPath,
//       size: sizes[relFilePaths.indexOf(relPath)],
//     }
//   })

//   logger.info('Uploading files...')
//   // Now upload everything. First we instantiate a filequeue with a bunch of files we need to upload
//   const fq = new FileQueue(
//     uploadfiles,
//     // This is the upload promise
//     ({ urls, pathAbs, update }) =>
//       urls.length === 1 ? uploadFile(pathAbs, urls[0], update) : uploadMultiPartFile(pathAbs, urls, update),
//     !opts.ui
//   )
//   // Now kick it off
//   const result = await fq.startPromise().then(() => Promise.resolve('Done uploading all files'))
//   // const result = await fq.startPromise()

//   const {
//     data: { finalizeProjectUpload },
//   } = (await api.query({
//     query: FinalizeProjectUpload,
//     variables: {
//       token,
//     },
//   })) as { data: { finalizeProjectUpload: JobStatusObj } }

//   // Poll the CheckUpload Query until success comes back every 5 seconds
//   let checkStatus: CheckUploadQuery['checkUpload']
//   if (opts && opts.wait) {
//     let counter = 0
//     // While the status is not failed or success and we haven't waited too long
//     const completeStatuses: JobStatusEnum[] = [JobStatusEnum.Failed, JobStatusEnum.Success]
//     while (
//       counter < MAX_WAIT_TIME / WAIT_INTERVAL &&
//       (!checkStatus || !completeStatuses.includes(checkStatus.status))
//     ) {
//       logger.warning(
//         `Upload status: ${!checkStatus ? JobStatusEnum.Unknown : checkStatus.status} (waiting ${WAIT_INTERVAL}ms)`
//       )
//       await sleep(WAIT_INTERVAL)
//       counter++
//       const {
//         data: { checkUpload },
//       } = await api.query<CheckUploadQuery>({
//         query: CheckUpload,
//         variables: {
//           token,
//         },
//       })
//       checkStatus = checkUpload
//     }
//     if (checkStatus.status === JobStatusEnum.Failed) {
//       throw new Error('Upload failed' + JSON.stringify(checkStatus.errors))
//     } else if (checkStatus.status === JobStatusEnum.Success) {
//       logger.success('Upload complete')
//     } else if (counter >= MAX_WAIT_TIME / WAIT_INTERVAL) {
//       logger.error('Upload timed out')
//       logger.warning('Upload status:', JSON.stringify(checkStatus))
//       throw new Error('Upload timed out')
//     }
//   }

//   // If we succeeded then we need to get the new Project XML file
//   const downloadedFile = await api
//     .query<DownloadFileQuery>({
//       query: DownloadFile,
//       variables: {
//         projectId: newId,
//         filePath: PROJECT_FILE,
//       },
//     })
//     .then(({ data: { downloadFile } }) => {
//       const { contentType, downloadUrl, etag, localPath, size } = downloadFile
//       // dowload the file using the downloadUrl and axios
//       return downloadFileFunc(downloadUrl, projFileXMLPath).catch((err) => {
//         logger.error('Error downloading project file:', err)
//         throw err
//       })
//     })
//     .catch(async (err) => {
//       // NOTE: THIS IS NOT IDEAL BUT WE NEED TO GET THE PROJECT XML FILE UPDATES SOMEHOW
//       // Update the project XML file with the new warehouse tag but we will be missing the ref="" tag
//       parsedXML.addWarehouseEl({
//         id: newId,
//         apiUrl: api.warehouseInfo.api,
//       })
//       // This is the ugly toString method.
//       const prettyNewXML = await parsedXML._toString()
//       fs.writeFileSync(projFileXMLPath, prettyNewXML)
//     })

//   logger.success(`RSCLI Upload to: ${api.uri} with id: ${newId}`)

//   if (api.uri === `https://api.data.riverscapes.net`) {
//     logger.success(`Find it at https://data.riverscapes.net/p/${newId}/`)
//   } else if (api.uri === `https://api.data.riverscapes.net/staging`) {
//     logger.success(`Find it at https://staging.data.riverscapes.net/p/${newId}/`)
//   } else {
//     logger.success(`Find it at http://WAREHOUSE_URL/p/${newId}/`)
//   }
//   logger.success(`COMPLETE`)
//   return
// }

// export default upload
