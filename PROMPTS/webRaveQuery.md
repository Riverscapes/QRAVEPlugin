Operation:
```gql
query webRaveProject($id: ID!, $dsLimit: Int!, $dsOffset: Int!) {
  project(id: $id) {
    id
    name
    summary
    deleted
    archived
    createdOn
    updatedOn
    tags
    visibility
    projectType {
      id
      name
    }
    meta {
      key
      value
      type
      locked
      ext
    }
    ownedBy {
      ... on User {
        id
        name
        avatar
      }
      ... on Organization {
        id
        name
        logo
      }
      __typename
    }
    bounds {
      id
      bbox
      centroid
      polygonUrl
      __typename
    }
    datasets(limit: $dsLimit, offset: $dsOffset) {
      items {
        id
        rsXPath
        refProject {
          ...DatasetProjectSource
        }
        layers {
          lyrName
          refProject {
            ...DatasetProjectSource
          }
        }
        meta {
          key
          value
          type
          locked
          ext
        }
      }
      limit
      offset
      total
    }
    tree {
      defaultView
      description
      leaves {
        id
        pid
        label
        labelxpath
        nodeId
        filePath
        layerType
        blLayerId
        symbology
        transparency
        rsXPath
        lyrName
      }
      branches {
        bid
        collapsed
        label
        pid
      }
      defaultView
      views {
        id
        name
        description
        layers {
          id
          visible
        }
      }
    }
  }
}
    
    fragment DatasetProjectSource on Project {
  id
  name
  projectType {
    id
    name
  }
}
```
```json
{
  "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d",
  "dsLimit": 50,
  "dsOffset": 0
}
```
Returns:
```json
{
  "data": {
    "project": {
      "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d",
      "name": "Riverscapes Context for Lake Champlain",
      "summary": "",
      "deleted": false,
      "archived": false,
      "createdOn": "2025-09-17T16:41:45.275Z",
      "updatedOn": "2025-09-17T16:41:45.275Z",
      "tags": [
        "2025CONUS",
        "NEWWBD"
      ],
      "visibility": "PUBLIC",
      "projectType": {
        "id": "rscontext",
        "name": "Riverscapes Context",
        "__typename": "ProjectType"
      },
      "meta": [
        {
          "key": "Model Version",
          "value": "2.1.0",
          "type": null,
          "locked": true,
          "ext": null,
          "__typename": "MetaData"
        },
        {
          "key": "Date Created",
          "value": "2025-09-17T16:24:58.830711",
          "type": "ISODATE",
          "locked": true,
          "ext": null,
          "__typename": "MetaData"
        },
        {
          "key": "Model Documentation",
          "value": "https://tools.riverscapes.net/rscontext",
          "type": "URL",
          "locked": true,
          "ext": null,
          "__typename": "MetaData"
        },
        {
          "key": "HUC",
          "value": "0430010816",
          "type": "HIDDEN",
          "locked": true,
          "ext": null,
          "__typename": "MetaData"
        },
        {
          "key": "Hydrologic Unit Code",
          "value": "0430010816",
          "type": null,
          "locked": true,
          "ext": null,
          "__typename": "MetaData"
        },
        {
          "key": "Runner",
          "value": "Cybercastor",
          "type": "HIDDEN",
          "locked": true,
          "ext": null,
          "__typename": "MetaData"
        },
        {
          "key": "Watershed",
          "value": "Lake Champlain",
          "type": null,
          "locked": false,
          "ext": null,
          "__typename": "MetaData"
        },
        {
          "key": "ProcTimeS",
          "value": "989.23",
          "type": "HIDDEN",
          "locked": true,
          "ext": null,
          "__typename": "MetaData"
        },
        {
          "key": "Processing Time",
          "value": "16:29 minutes",
          "type": null,
          "locked": true,
          "ext": null,
          "__typename": "MetaData"
        }
      ],
      "ownedBy": {
        "id": "a52b8094-7a1d-4171-955c-ad30ae935296",
        "name": "USU RAM",
        "logo": "https://data.riverscapes.net/images/O/a52b8094-7a1d-4171-955c-ad30ae935296_1747668286584.png",
        "__typename": "Organization"
      },
      "bounds": {
        "id": "b31748f0-f3ad-4305-9c62-d54a73dfb43e",
        "bbox": [
          -73.658763,
          44.246325,
          -73.193506,
          45.011944
        ],
        "centroid": [
          -73.42613449999999,
          44.6291345
        ],
        "polygonUrl": "https://data.riverscapes.net/bounds/P/b31748f0-f3ad-4305-9c62-d54a73dfb43e.geojson",
        "__typename": "ProjectBounds"
      },
      "datasets": {
        "items": [
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Logs/LogFile#LOGFILE",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Logs/LogFile#LOGFILE",
            "refProject": null,
            "layers": [],
            "meta": [],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#DEM",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#DEM",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://gdg.sc.egov.usda.gov/Catalog/ProductDescription/NED.html",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": null,
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#DEM",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "NumRasters",
                "value": "2",
                "type": "INT",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "OriginUrls",
                "value": "[\"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n45w074/USGS_13_n45w074_20190416.tif\", \"https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/historical/n46w074/USGS_13_n46w074_20181204.tif\"]",
                "type": "JSON",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "7.2872056213495",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "10.29026434286011",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#HILLSHADE",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#HILLSHADE",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://gdal.org/programs/gdaldem.html",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": null,
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#HILLSHADE",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "7.2872056213495",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "10.29026434286011",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#SLOPE",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#SLOPE",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://gdal.org/programs/gdaldem.html",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": null,
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#SLOPE",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "7.2872056213495",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "10.29026434286011",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#EXVEG",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#EXVEG",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://landfire.gov/data_overviews.php",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2.4.0",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#EXVEG",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "25.410032926775138",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "35.88960992414739",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#HISTVEG",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#HISTVEG",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://landfire.gov/data_overviews.php",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2.2.0",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#HISTVEG",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "25.410032926775138",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "35.88960992414739",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#VEGCOVER",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#VEGCOVER",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://landfire.gov/data_overviews.php",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2.4.0",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#VEGCOVER",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "25.410032926775138",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "35.88960992414739",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#VEGHEIGHT",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#VEGHEIGHT",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://landfire.gov/data_overviews.php",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2.4.0",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#VEGHEIGHT",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "25.410032926775138",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "35.88960992414739",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#HDIST",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#HDIST",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://landfire.gov/data_overviews.php",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2.4.0",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#HDIST",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "25.410032926775138",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "35.88960992414739",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#FDIST",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#FDIST",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://landfire.gov/data_overviews.php",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2.4.0",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#FDIST",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "25.410032926775138",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "35.88960992414739",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#FCCS",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#FCCS",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://landfire.gov/data_overviews.php",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2.4.0",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#FCCS",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "25.410032926775138",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "35.88960992414739",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#VEGCONDITION",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#VEGCONDITION",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://landfire.gov/data_overviews.php",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2.4.0",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#VEGCONDITION",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "25.410032926775138",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "35.88960992414739",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#VEGDEPARTURE",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#VEGDEPARTURE",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://landfire.gov/data_overviews.php",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2.4.0",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#VEGDEPARTURE",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "25.410032926775138",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "35.88960992414739",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#SCLASS",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#SCLASS",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://landfire.gov/data_overviews.php",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2.4.0",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#SCLASS",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "25.410032926775138",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "35.88960992414739",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#FAIRMARKETVALUE",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#FAIRMARKETVALUE",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://placeslab.org/fmv-usa/",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "October 2020",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#FAIRMARKETVALUE",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "ORCID",
                "value": "https://orcid.org/0000-0001-7827-689X",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "437.4063044203034",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "617.8970452965716",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSV2",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSV2",
            "refProject": null,
            "layers": [
              {
                "lyrName": "nhdarea",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "nhdflowline_network",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "nhdwaterbody",
                "refProject": null,
                "__typename": "DatasetLayer"
              }
            ],
            "meta": [],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NATIONAL_DAMS",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NATIONAL_DAMS",
            "refProject": null,
            "layers": [
              {
                "lyrName": "NationalDams",
                "refProject": null,
                "__typename": "DatasetLayer"
              }
            ],
            "meta": [],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NATIONAL_WETLANDS",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NATIONAL_WETLANDS",
            "refProject": null,
            "layers": [
              {
                "lyrName": "Riparian",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "Wetlands",
                "refProject": null,
                "__typename": "DatasetLayer"
              }
            ],
            "meta": [],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#Precip",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#Precip",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://prism.oregonstate.edu/normals/",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "1991-2020",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#Precip",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "655.661703913876",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "922.132575897196",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MeanTemp",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MeanTemp",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://prism.oregonstate.edu/normals/",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "1991-2020",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#MeanTemp",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "655.661703913876",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "922.132575897196",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MinTemp",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MinTemp",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://prism.oregonstate.edu/normals/",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "1991-2020",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#MinTemp",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "655.661703913876",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "922.132575897196",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MaxTemp",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MaxTemp",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://prism.oregonstate.edu/normals/",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "1991-2020",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#MaxTemp",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "655.661703913876",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "922.132575897196",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MeanDew",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MeanDew",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://prism.oregonstate.edu/normals/",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "1991-2020",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#MeanDew",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "655.661703913876",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "922.132575897196",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MinVap",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MinVap",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://prism.oregonstate.edu/normals/",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "1991-2020",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#MinVap",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "655.661703913876",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "922.132575897196",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MaxVap",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MaxVap",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://prism.oregonstate.edu/normals/",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "1991-2020",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#MaxVap",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeX",
                "value": "655.661703913876",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "CellSizeY",
                "value": "922.132575897196",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Roads",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Roads",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://data.usgs.gov/datacatalog/data/USGS:ad3d631d-f51f-4b6a-91a3-e617d6a58b4e",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2020",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#Roads",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "New York",
                "value": "https://prd-tnm.s3.amazonaws.com/StagedProducts/Tran/Shape/TRAN_New_York_State_Shape.zip",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "Vermont",
                "value": "https://prd-tnm.s3.amazonaws.com/StagedProducts/Tran/Shape/TRAN_Vermont_State_Shape.zip",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Rail",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Rail",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://data.usgs.gov/datacatalog/data/USGS:ad3d631d-f51f-4b6a-91a3-e617d6a58b4e",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2020",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#Rail",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "New York",
                "value": "https://prd-tnm.s3.amazonaws.com/StagedProducts/Tran/Shape/TRAN_New_York_State_Shape.zip",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "Vermont",
                "value": "https://prd-tnm.s3.amazonaws.com/StagedProducts/Tran/Shape/TRAN_Vermont_State_Shape.zip",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Canals",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Canals",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://data.usgs.gov/datacatalog/data/USGS:ad3d631d-f51f-4b6a-91a3-e617d6a58b4e",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2020",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#Canals",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "New York",
                "value": "https://prd-tnm.s3.amazonaws.com/StagedProducts/Tran/Shape/TRAN_New_York_State_Shape.zip",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "Vermont",
                "value": "https://prd-tnm.s3.amazonaws.com/StagedProducts/Tran/Shape/TRAN_Vermont_State_Shape.zip",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Ownership",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Ownership",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://landscape.blm.gov/geoportal/catalog/search/resource/details.page?uuid=%7B2A8B8906-7711-4AF7-9510-C6C7FD991177%7D",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": null,
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#Ownership",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Vector#States",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#States",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2021",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#States",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Counties",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Counties",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2021",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#Counties",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Vector#GEOLOGY",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#GEOLOGY",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://www.sciencebase.gov/catalog/item/5888bf4fe4b05ccb964bab9d",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "1.1",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#GEOLOGY",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Ecoregions",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Ecoregions",
            "refProject": null,
            "layers": [],
            "meta": [
              {
                "key": "SourceUrl",
                "value": "https://gaftp.epa.gov/EPADataCommons/ORD/Ecoregions/us/Eco_Level_IV_US.html",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DataProductVersion",
                "value": "2013-04-16",
                "type": null,
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              },
              {
                "key": "DocsUrl",
                "value": "https://tools.riverscapes.net/rscontext/data/#Ecoregions",
                "type": "URL",
                "locked": false,
                "ext": null,
                "__typename": "MetaData"
              }
            ],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "refProject": null,
            "layers": [
              {
                "lyrName": "NHDArea",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "NHDFlowline",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "NHDPlusCatchment",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "NHDPlusFlowlineVAA",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "NHDWaterbody",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "WBDHU10",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "WBDHU12",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "WBDHU2",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "WBDHU4",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "WBDHU6",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "WBDHU8",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "vw_NHDFlowlineVAA",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "vw_NHDPlusCatchmentVAA",
                "refProject": null,
                "__typename": "DatasetLayer"
              }
            ],
            "meta": [],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#HYDRODERIVATIVES",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#HYDRODERIVATIVES",
            "refProject": null,
            "layers": [
              {
                "lyrName": "NHDAreaSplit",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "NHDWaterbodySplit",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "buffered_clip100m",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "buffered_clip500m",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "catchments",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "network_crossings",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "network_intersected",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "network_segmented",
                "refProject": null,
                "__typename": "DatasetLayer"
              },
              {
                "lyrName": "processing_extent",
                "refProject": null,
                "__typename": "DatasetLayer"
              }
            ],
            "meta": [],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/HTMLFile#REPORT",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/HTMLFile#REPORT",
            "refProject": null,
            "layers": [],
            "meta": [],
            "__typename": "Dataset"
          },
          {
            "id": "ac104f27-93b7-4e47-b279-7a7dad8ccf1d/Project/Realizations/Realization#REALIZATION1/Datasets/File#Metrics",
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/File#Metrics",
            "refProject": null,
            "layers": [],
            "meta": [],
            "__typename": "Dataset"
          }
        ],
        "limit": 50,
        "offset": 0,
        "total": 37,
        "__typename": "PaginatedDatasets"
      },
      "tree": {
        "defaultView": "Default",
        "description": null,
        "leaves": [
          {
            "id": 0,
            "pid": 0,
            "label": "Project Report",
            "labelxpath": null,
            "nodeId": "REPORT",
            "filePath": "rs_context.html",
            "layerType": "REPORT",
            "blLayerId": null,
            "symbology": null,
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/HTMLFile#REPORT",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 1,
            "pid": 1,
            "label": "Roads",
            "labelxpath": "Name",
            "nodeId": "Roads",
            "filePath": "transportation/roads.shp",
            "layerType": "LINE",
            "blLayerId": "roads",
            "symbology": "roads",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Roads",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 2,
            "pid": 1,
            "label": "Roads (simple)",
            "labelxpath": null,
            "nodeId": "Roads",
            "filePath": "transportation/roads.shp",
            "layerType": "LINE",
            "blLayerId": "roads_simple",
            "symbology": "roads_simple",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Roads",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 3,
            "pid": 1,
            "label": "Rail",
            "labelxpath": "Name",
            "nodeId": "Rail",
            "filePath": "transportation/railways.shp",
            "layerType": "LINE",
            "blLayerId": "railroads",
            "symbology": "railroads",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Rail",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 4,
            "pid": 3,
            "label": "Perennial Drainage Network",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "LINE",
            "blLayerId": "perrenial",
            "symbology": "nhdperrenial",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "NHDFlowline",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 5,
            "pid": 3,
            "label": "Intermittent Drainage Network",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "LINE",
            "blLayerId": "intermittent",
            "symbology": "nhdintermittent",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "NHDFlowline",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 6,
            "pid": 3,
            "label": "Ephemeral Drainage Network",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "LINE",
            "blLayerId": "ephemeral",
            "symbology": "nhdephemeral",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "NHDFlowline",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 7,
            "pid": 3,
            "label": "Network - Upstream Drainage Area",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "LINE",
            "blLayerId": null,
            "symbology": "upstreamdrainagearea",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "NHDFlowline",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 8,
            "pid": 3,
            "label": "Full NHD HR+ Drainage Network (by FCode)",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "LINE",
            "blLayerId": null,
            "symbology": "flow_lines",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "NHDFlowline",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 9,
            "pid": 3,
            "label": "Full NHD HR+ Drainage Network (simple)",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "LINE",
            "blLayerId": null,
            "symbology": "flow_lines_simple",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "NHDFlowline",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 10,
            "pid": 3,
            "label": "Drainage Wings",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "drainagewings",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "NHDPlusCatchment",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 11,
            "pid": 3,
            "label": "River Polygons (NHD Area)",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "nhdarea",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#HYDRODERIVATIVES",
            "lyrName": "NHDAreaSplit",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 12,
            "pid": 3,
            "label": "Lakes, Ponds, Reservoirs and Water Bodies",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "waterbody",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "NHDWaterbody",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 13,
            "pid": 3,
            "label": "Canals and Ditches",
            "labelxpath": null,
            "nodeId": "Canals",
            "filePath": "transportation/canals.shp",
            "layerType": "LINE",
            "blLayerId": null,
            "symbology": "canals_ditches",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Canals",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 14,
            "pid": 3,
            "label": "Pipes and Ditches",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "LINE",
            "blLayerId": null,
            "symbology": "pipes",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "NHDFlowline",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 15,
            "pid": 4,
            "label": "Sub-Watersheds - 12-Digit HUC",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "wbdhu12",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "WBDHU12",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 16,
            "pid": 4,
            "label": "Watersheds - 10-Digit HUC",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POLYGON",
            "blLayerId": "huc10",
            "symbology": "wbdhu10",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "WBDHU10",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 17,
            "pid": 4,
            "label": "Sub-Basin - 8-Digit HUC",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POLYGON",
            "blLayerId": "huc8",
            "symbology": "wbdhu8",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "WBDHU8",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 18,
            "pid": 4,
            "label": "Basin - 6-Digit HUC",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "wbdhu6",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "WBDHU6",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 19,
            "pid": 4,
            "label": "Subregion - 4-Digit HUC",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "wbdhu4",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "WBDHU4",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 20,
            "pid": 4,
            "label": "Region - 2-Digit HUC",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "wbdhu2",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSHR",
            "lyrName": "WBDHU2",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 21,
            "pid": 5,
            "label": "Flow Lines (NHDPlus V2)",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "LINE",
            "blLayerId": null,
            "symbology": "nhdplusv2_flowlines",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSV2",
            "lyrName": "nhdflowline_network",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 22,
            "pid": 5,
            "label": "Flow Areas (NHDPlus V2)",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "nhdplusv2_flowareas",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSV2",
            "lyrName": "nhdarea",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 23,
            "pid": 5,
            "label": "Waterbodies (NHDPlus V2)",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "nhdplusv2_waterbodies",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NHDPLUSV2",
            "lyrName": "nhdwaterbody",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 24,
            "pid": 6,
            "label": "Dams by owner",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POINT",
            "blLayerId": null,
            "symbology": "nid_dams_ownership",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NATIONAL_DAMS",
            "lyrName": "NationalDams",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 25,
            "pid": 6,
            "label": "Dams by height",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POINT",
            "blLayerId": null,
            "symbology": "nid_dams_height",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NATIONAL_DAMS",
            "lyrName": "NationalDams",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 26,
            "pid": 6,
            "label": "Dam Name",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POINT",
            "blLayerId": null,
            "symbology": "nid_dams_name",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NATIONAL_DAMS",
            "lyrName": "NationalDams",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 27,
            "pid": 7,
            "label": "Wetlands",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "nwi_wetlands",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NATIONAL_WETLANDS",
            "lyrName": "Wetlands",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 28,
            "pid": 7,
            "label": "Riparian Areas",
            "labelxpath": null,
            "nodeId": "",
            "filePath": null,
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "nwi_riparian",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Geopackage#NATIONAL_WETLANDS",
            "lyrName": "Riparian",
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 29,
            "pid": 8,
            "label": "Mean Annual Precipitation (mm)",
            "labelxpath": null,
            "nodeId": "Precip",
            "filePath": "climate/precipitation.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "mean_annual_precip",
            "transparency": 50,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#Precip",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 30,
            "pid": 8,
            "label": "Mean Temperature (°C)",
            "labelxpath": null,
            "nodeId": "MeanTemp",
            "filePath": "climate/mean_temp.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "temperature",
            "transparency": 50,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MeanTemp",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 31,
            "pid": 8,
            "label": "Minimum Temperature (°C)",
            "labelxpath": null,
            "nodeId": "MinTemp",
            "filePath": "climate/min_temp.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "temperature",
            "transparency": 50,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MinTemp",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 32,
            "pid": 8,
            "label": "Maximum Temperature (°C)",
            "labelxpath": null,
            "nodeId": "MaxTemp",
            "filePath": "climate/max_temp.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "temperature",
            "transparency": 50,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MaxTemp",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 33,
            "pid": 8,
            "label": "Mean Dewpoint Temperature (°C)",
            "labelxpath": null,
            "nodeId": "MeanDew",
            "filePath": "climate/mean_dew_temp.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "temperature",
            "transparency": 50,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MeanDew",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 34,
            "pid": 8,
            "label": "Minimum Vapor Pressure Deficit (hPa)",
            "labelxpath": null,
            "nodeId": "MinVap",
            "filePath": "climate/min_vapor_pressure.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "vapor_pressure",
            "transparency": 50,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MinVap",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 35,
            "pid": 8,
            "label": "Maximum Vapor Pressure Deficit (hPa)",
            "labelxpath": null,
            "nodeId": "MaxVap",
            "filePath": "climate/max_vapor_pressure.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "vapor_pressure",
            "transparency": 50,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#MaxVap",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 36,
            "pid": 9,
            "label": "Level 1 Ecoregions",
            "labelxpath": null,
            "nodeId": "Ecoregions",
            "filePath": "ecoregions/ecoregions.shp",
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "ecoregions_1",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Ecoregions",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 37,
            "pid": 9,
            "label": "Level 2 Ecoregions",
            "labelxpath": null,
            "nodeId": "Ecoregions",
            "filePath": "ecoregions/ecoregions.shp",
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "ecoregions_2",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Ecoregions",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 38,
            "pid": 9,
            "label": "Level 3 Ecoregions",
            "labelxpath": null,
            "nodeId": "Ecoregions",
            "filePath": "ecoregions/ecoregions.shp",
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "ecoregions_3",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Ecoregions",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 39,
            "pid": 9,
            "label": "Level 4 Ecoregions",
            "labelxpath": null,
            "nodeId": "Ecoregions",
            "filePath": "ecoregions/ecoregions.shp",
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "ecoregions_4",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Ecoregions",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 40,
            "pid": 10,
            "label": "Rock Type",
            "labelxpath": null,
            "nodeId": "GEOLOGY",
            "filePath": "geology/geology.shp",
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "geo",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#GEOLOGY",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 41,
            "pid": 10,
            "label": "Age",
            "labelxpath": null,
            "nodeId": "GEOLOGY",
            "filePath": "geology/geology.shp",
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "geo_maxage",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#GEOLOGY",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 42,
            "pid": 11,
            "label": "Land Ownership",
            "labelxpath": null,
            "nodeId": "Ownership",
            "filePath": "ownership/ownership.shp",
            "layerType": "POLYGON",
            "blLayerId": "owner",
            "symbology": "ownership",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Ownership",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 43,
            "pid": 11,
            "label": "Fair Market Value",
            "labelxpath": null,
            "nodeId": "FAIRMARKETVALUE",
            "filePath": "ownership/fair_market_value.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "fair_market",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#FAIRMARKETVALUE",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 44,
            "pid": 12,
            "label": "State Boundaries",
            "labelxpath": null,
            "nodeId": "States",
            "filePath": "political_boundaries/states.shp",
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "states",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#States",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 45,
            "pid": 12,
            "label": "County Boundaries",
            "labelxpath": null,
            "nodeId": "Counties",
            "filePath": "political_boundaries/counties.shp",
            "layerType": "POLYGON",
            "blLayerId": null,
            "symbology": "counties",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Counties",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 46,
            "pid": 15,
            "label": "Veg Type - EVT Class",
            "labelxpath": null,
            "nodeId": "EXVEG",
            "filePath": "vegetation/existing_veg.tif",
            "layerType": "RASTER",
            "blLayerId": "exveg",
            "symbology": "Existing_Veg_EVT_Class",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#EXVEG",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 47,
            "pid": 15,
            "label": "Veg Type - EVT Name",
            "labelxpath": null,
            "nodeId": "EXVEG",
            "filePath": "vegetation/existing_veg.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "Existing_Veg_EVT_Name",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#EXVEG",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 48,
            "pid": 15,
            "label": "Veg Cover - EVC",
            "labelxpath": null,
            "nodeId": "VEGCOVER",
            "filePath": "vegetation/veg_cover.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "Veg_Cover",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#VEGCOVER",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 49,
            "pid": 15,
            "label": "Veg Height - EVH",
            "labelxpath": null,
            "nodeId": "VEGHEIGHT",
            "filePath": "vegetation/veg_height.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "Veg_Height",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#VEGHEIGHT",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 50,
            "pid": 15,
            "label": "Veg Type - EVT Riparian",
            "labelxpath": null,
            "nodeId": "EXVEG",
            "filePath": "vegetation/existing_veg.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "Existing_Veg_EVT_Riparian",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#EXVEG",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 51,
            "pid": 16,
            "label": "Veg Type - BPS Name",
            "labelxpath": null,
            "nodeId": "HISTVEG",
            "filePath": "vegetation/historic_veg.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "Historic_Veg_BPS_Name",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#HISTVEG",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 52,
            "pid": 16,
            "label": "Veg Type - BPS Riparian",
            "labelxpath": null,
            "nodeId": "HISTVEG",
            "filePath": "vegetation/historic_veg.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "Historic_Veg_BPS_Riparian",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#HISTVEG",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 53,
            "pid": 17,
            "label": "Historic Disturbance - HDst",
            "labelxpath": null,
            "nodeId": "HDIST",
            "filePath": "vegetation/historic_disturbance.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "Historic_Disturbance",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#HDIST",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 54,
            "pid": 17,
            "label": "Fuel Disturbance - FDst",
            "labelxpath": null,
            "nodeId": "FDIST",
            "filePath": "vegetation/fuel_disturbance.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "Fuel_Disturbance",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#FDIST",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 55,
            "pid": 18,
            "label": "Fuel Characteristic Classification - FCCS",
            "labelxpath": null,
            "nodeId": "FCCS",
            "filePath": "vegetation/fccs.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "fccs",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#FCCS",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 56,
            "pid": 19,
            "label": "Vegetation Condition",
            "labelxpath": null,
            "nodeId": "VEGCONDITION",
            "filePath": "vegetation/vegetation_condition.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "Vegetation_Condition",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#VEGCONDITION",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 57,
            "pid": 19,
            "label": "Vegetation Departure",
            "labelxpath": null,
            "nodeId": "VEGDEPARTURE",
            "filePath": "vegetation/vegetation_departure.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "Vegetation_Departure",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#VEGDEPARTURE",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 58,
            "pid": 19,
            "label": "Succession Classes",
            "labelxpath": null,
            "nodeId": "SCLASS",
            "filePath": "vegetation/succession_classes.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "Succession_Classes",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#SCLASS",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 59,
            "pid": 20,
            "label": "DEM (10 m NED)",
            "labelxpath": null,
            "nodeId": "DEM",
            "filePath": "topography/dem.tif",
            "layerType": "RASTER",
            "blLayerId": "dem",
            "symbology": "dem",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#DEM",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 61,
            "pid": 20,
            "label": "Slope Analysis (Degrees)",
            "labelxpath": null,
            "nodeId": "SLOPE",
            "filePath": "topography/slope.tif",
            "layerType": "RASTER",
            "blLayerId": null,
            "symbology": "slope",
            "transparency": 40,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#SLOPE",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 62,
            "pid": 21,
            "label": "DEM Hillshade",
            "labelxpath": "Name",
            "nodeId": "HILLSHADE",
            "filePath": "topography/dem_hillshade.tif",
            "layerType": "RASTER",
            "blLayerId": "hs",
            "symbology": "hillshade",
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/Raster#HILLSHADE",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 63,
            "pid": 0,
            "label": "Log File",
            "labelxpath": null,
            "nodeId": "LOGFILE",
            "filePath": "rs_context.log",
            "layerType": "FILE",
            "blLayerId": null,
            "symbology": null,
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Logs/LogFile#LOGFILE",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          },
          {
            "id": 64,
            "pid": 0,
            "label": "Metrics",
            "labelxpath": null,
            "nodeId": "Metrics",
            "filePath": "rscontext_metrics.json",
            "layerType": "FILE",
            "blLayerId": null,
            "symbology": null,
            "transparency": 0,
            "rsXPath": "Project/Realizations/Realization#REALIZATION1/Datasets/File#Metrics",
            "lyrName": null,
            "__typename": "ProjectTreeLeaf"
          }
        ],
        "branches": [
          {
            "bid": 0,
            "collapsed": false,
            "label": "Riverscapes Context for HUC 0430010816",
            "pid": -1,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 1,
            "collapsed": true,
            "label": "Transportation Local",
            "pid": 0,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 2,
            "collapsed": false,
            "label": "Hydrology",
            "pid": 0,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 3,
            "collapsed": true,
            "label": "Hydrography (NHD HR+, 1:24k)",
            "pid": 2,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 4,
            "collapsed": true,
            "label": "Watershed Boundaries (HUCs)",
            "pid": 2,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 5,
            "collapsed": true,
            "label": "Hydrography (NHDPlus V2, 1:100k)",
            "pid": 2,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 6,
            "collapsed": true,
            "label": "National Inventory of Dams",
            "pid": 2,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 7,
            "collapsed": true,
            "label": "National Wetlands Inventory",
            "pid": 2,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 8,
            "collapsed": true,
            "label": "Climate (PRISM)",
            "pid": 0,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 9,
            "collapsed": true,
            "label": "Ecoregions",
            "pid": 0,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 10,
            "collapsed": true,
            "label": "Geology",
            "pid": 0,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 11,
            "collapsed": true,
            "label": "Land Management",
            "pid": 0,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 12,
            "collapsed": true,
            "label": "Political Boundaries",
            "pid": 0,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 13,
            "collapsed": false,
            "label": "LANDFIRE",
            "pid": 0,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 14,
            "collapsed": true,
            "label": "Vegetation",
            "pid": 13,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 15,
            "collapsed": false,
            "label": "Existing Vegetation",
            "pid": 14,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 16,
            "collapsed": true,
            "label": "Historic Vegetation",
            "pid": 14,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 17,
            "collapsed": true,
            "label": "Disturbance",
            "pid": 13,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 18,
            "collapsed": true,
            "label": "Fuel",
            "pid": 13,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 19,
            "collapsed": true,
            "label": "Vegetation Condition",
            "pid": 13,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 20,
            "collapsed": true,
            "label": "Topography and Derivatives",
            "pid": 0,
            "__typename": "ProjectTreeBranch"
          },
          {
            "bid": 21,
            "collapsed": true,
            "label": "Hillshade",
            "pid": 0,
            "__typename": "ProjectTreeBranch"
          }
        ],
        "views": [
          {
            "id": "Default",
            "name": "Hydrology",
            "description": null,
            "layers": [
              {
                "id": "perrenial",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              },
              {
                "id": "intermittent",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              },
              {
                "id": "ephemeral",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              },
              {
                "id": "huc10",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              }
            ],
            "__typename": "ProjectTreeView"
          },
          {
            "id": "Topography",
            "name": "Topography",
            "description": null,
            "layers": [
              {
                "id": "perrenial",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              },
              {
                "id": "intermittent",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              },
              {
                "id": "dem",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              },
              {
                "id": "hs",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              }
            ],
            "__typename": "ProjectTreeView"
          },
          {
            "id": "Transportation",
            "name": "Transportation",
            "description": null,
            "layers": [
              {
                "id": "roads",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              },
              {
                "id": "railroads",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              }
            ],
            "__typename": "ProjectTreeView"
          },
          {
            "id": "veg",
            "name": "Existing Vegetation",
            "description": null,
            "layers": [
              {
                "id": "perrenial",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              },
              {
                "id": "intermittent",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              },
              {
                "id": "exveg",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              }
            ],
            "__typename": "ProjectTreeView"
          },
          {
            "id": "land",
            "name": "Land Ownership",
            "description": null,
            "layers": [
              {
                "id": "perrenial",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              },
              {
                "id": "intermittent",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              },
              {
                "id": "owner",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              }
            ],
            "__typename": "ProjectTreeView"
          },
          {
            "id": "Geology",
            "name": "Geology",
            "description": null,
            "layers": [
              {
                "id": "perrenial",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              },
              {
                "id": "geo",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              },
              {
                "id": "hs",
                "visible": true,
                "__typename": "ProjectTreeViewLayer"
              }
            ],
            "__typename": "ProjectTreeView"
          }
        ],
        "__typename": "ProjectTree"
      },
      "__typename": "Project"
    }
  }
}
```