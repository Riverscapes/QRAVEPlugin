from typing import List
from collections import namedtuple
from qgis.core import QgsMessageLog, Qgis

from .GraphQLAPI import GraphQLAPI, GraphQLAPIConfig
from .settings import CONSTANTS

MyOrgs = namedtuple('MyOrgs', ['id', 'name', 'myRole'])


class DataExchangeAPI():
    """ Class to handle data exchange between the different components of the system
    """

    def __init__(self):
        self.myId = None
        self.myName = None
        self.myOrgs = []
        self.initialized = False
        self.api = GraphQLAPI(
            apiUrl=CONSTANTS['DE_API_Url'],
            config=GraphQLAPIConfig(**CONSTANTS['DE_API_Auth'])
        )
        self.api.refresh_token()
        self.initialized = self.api.access_token is not None

    def get_project(self, project_id: str):
        """ Get the metadata for a project

        Args:
            project_id (str): the id of the project to get
        """
        project = self.api.run_query("""
            query project($id: ID!) {
                project(id: $id) {
                    id
                    name
                    description
                    tags
                    owner {
                        id
                        name
                    }
                    organization {
                        id
                        name
                    }
                    access
                }
            }
            """, {'id': project_id})
        QgsMessageLog.logMessage('get_project success', 'QRAVE')
        return project['data']['project']

    def get_user_info(self) -> List[MyOrgs]:
        """ Get the organizations that the user is a part of

        """
        orgs = self.api.run_query("""
            query profile {
                profile {
                    id
                    name
                    organizations(limit: 500, offset: 0) {
                        items {
                            id
                            name
                            myRole
                        }
                    }
                }
            }
            """, {})
        QgsMessageLog.logMessage('get_organizations success', 'QRAVE')
        self.myId = orgs['data']['profile']['id']
        self.myName = orgs['data']['profile']['name']
        self.myOrgs = [MyOrgs(**org) for org in orgs['data']['profile']['organizations']['items']]

    def upload_file(self, fpath: str):
        """ Upload a file to the data exchange API

        Args:
            fpath (str): the path to the file to upload
        """
        pass
