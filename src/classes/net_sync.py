import traceback

import os
import json
import pdb
from glob import glob
from time import time, sleep
from qgis.core import QgsTask, QgsMessageLog, Qgis

from .util import md5, requestDownload
from .settings import Settings, CONSTANTS

# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS['logCategory']


class NetSync(QgsTask):

    def __init__(self, description):
        super().__init__(description, QgsTask.CanCancel)
        self.total = 0
        self.iterations = 0
        self.exception = None

        self.total = 0
        self.progress = 0
        self.downloaded = 0

        self.resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'resources'))
        self.business_logic_xml_dir = os.path.abspath(os.path.join(self.resource_dir, CONSTANTS['businessLogicDir']))
        self.symbology_dir = os.path.abspath(os.path.join(self.resource_dir, CONSTANTS['symbologyDir']))
        self.digest_path = os.path.abspath(os.path.join(self.resource_dir, 'index.json'))

        self.initialized = False  # self.initialize sets this
        self.need_sync = True  # self.initialize sets this

        self._initialize()

    # EVERYTHING BELOW HERE IS ASYNC

    def run(self):
        """
        Raises an exception to abort the task.
        Returns a result if success.
        The result will be passed, together with the exception (None in
        the case of success), to the on_finished method.
        If there is an exception, there will be no result.
        """

        # DEBUGGING
        # sleep(10)  # FOR DEBUG ONLY
        # sleep(10)  # FOR DEBUG ONLY
        self._updateDigest()
        # sleep(10)  # FOR DEBUG ONLY
        self._syncFiles()
        # sleep(10)  # FOR DEBUG ONLY
        return True

    def cancel(self):
        QgsMessageLog.logMessage('Net Sync "{name}" was canceled'.format(name=self.description()), MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()

    def finished(self, result=None):
        """This is called when doSomething is finished.
        Exception is not None if doSomething raises an exception.
        result is the return value of doSomething."""
        settings = Settings()
        if self.exception is None:
            if result is None:
                settings.log(
                    'Completed with no exception and no result '
                    '(probably manually canceled by the user)',
                    Qgis.Warning)
            else:
                settings.setValue('initialized', True)
                settings.msg_bar('Riverscapes Resources Sync Syccess', '{} files checked, {} updated'.format(self.total, self.downloaded), Qgis.Success)
                if result is True:
                    settings.setValue('lastDigestSync', int(time()))

        else:
            settings.msg_bar("Error syncing network resources", "Exception: {}".format(self.exception),
                             Qgis.Critical)
            # raise Exception(self.exception)

    def _initialize(self):
        need_sync = False
        if not os.path.isdir(self.resource_dir):
            need_sync = True
            os.mkdir(self.resource_dir)
        if not os.path.isdir(self.symbology_dir):
            need_sync = True
            os.mkdir(self.symbology_dir)
        if not os.path.isdir(self.business_logic_xml_dir):
            need_sync = True
            os.mkdir(self.business_logic_xml_dir)
        if not os.path.isfile(self.digest_path):
            need_sync = True

        self.initialized = True
        self.need_sync = need_sync

    def _updateDigest(self):
        # Now get the JSON file
        json_url = CONSTANTS['resourcesUrl'] + 'index.json'
        QgsMessageLog.logMessage("Requesting digest from: {}".format(json_url), MESSAGE_CATEGORY, level=Qgis.Info)
        requestDownload(json_url, self.digest_path)

    def _syncFiles(self):
        digest = {}
        if not os.path.isfile(self.digest_path):
            raise Exception("Digest file could not be found at: {}".format(self.digest_path))

        with open(self.digest_path) as fl:
            digest = json.load(fl)

        symbologies = {x: v for x, v in digest.items() if x.startswith('Symbology/qgis') and x.endswith('.qml')}
        businesslogics = {x: v for x, v in digest.items() if x.startswith('RaveBusinessLogic') and x.endswith('.xml')}
        basemaps = {x: v for x, v in digest.items() if x.startswith('BaseMaps.xml')}

        self.total = len(symbologies.keys()) + len(businesslogics.keys()) + 1
        self.progress = 0
        self.downloaded = 0

        all_local_files = [os.path.abspath(x) for x in glob(os.path.join(self.resource_dir, '**', '*.?ml'), recursive=True)]

        # Symbologies have directory structure
        for remote_path, remote_md5 in symbologies.items():
            local_path = os.path.abspath(os.path.join(self.symbology_dir, *remote_path.replace('Symbology/qgis/', '').split('/')))

            # There might be subdirs to make here
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            if not os.path.isfile(local_path) or remote_md5 != md5(local_path):
                requestDownload(CONSTANTS['resourcesUrl'] + remote_path, local_path, remote_md5)
                QgsMessageLog.logMessage("Symobology downloaded: {}".format(local_path), MESSAGE_CATEGORY, level=Qgis.Info)

                self.downloaded += 1
            all_local_files = [x for x in all_local_files if x != local_path]
            self.progress += 1
            self.setProgress(self.progress)

        for remote_path, remote_md5 in businesslogics.items():
            local_path = os.path.join(self.business_logic_xml_dir, os.path.relpath(remote_path, "RaveBusinessLogic"))
            if not os.path.isfile(local_path) or remote_md5 != md5(local_path):
                requestDownload(CONSTANTS['resourcesUrl'] + remote_path, local_path, remote_md5)
                QgsMessageLog.logMessage("BusinessLogic downloaded: {}".format(local_path), MESSAGE_CATEGORY, level=Qgis.Info)

                self.downloaded += 1
            all_local_files = [x for x in all_local_files if x != local_path]
            self.progress += 1
            self.setProgress(self.progress)

        # Basemaps is a special case
        for remote_path, remote_md5 in basemaps.items():
            local_path = os.path.join(self.resource_dir, os.path.basename(remote_path))
            if not os.path.isfile(local_path) or remote_md5 != md5(local_path):
                requestDownload(CONSTANTS['resourcesUrl'] + remote_path, local_path, remote_md5)
                QgsMessageLog.logMessage("Basemaps downloaded: {}".format(local_path), 'Riverscapes Viewer', level=Qgis.Info)

                self.downloaded += 1
            all_local_files = [x for x in all_local_files if x != local_path]
            self.progress += 1
            self.setProgress(self.progress)

        # Now we clean up any files that aren't supposed to be there
        for dfile in all_local_files:
            try:
                # Do a quick (probably redundant check) to make sure this file is in our current folder
                rel_check = os.path.relpath(dfile, os.path.join(os.path.dirname(__file__), '..', '..', 'resources'))
                if len(os.path.split(rel_check)) < 3:
                    os.remove(dfile)
                    QgsMessageLog.logMessage("Extraneous file removed: {}".format(dfile), 'Riverscapes Viewer', level=Qgis.Warning)
                else:
                    QgsMessageLog.logMessage("Can't remove file because it's in the wrong place: {}".format(dfile), 'QRiverscapes Viewer', level=Qgis.Critical)
            except Exception as e:
                QgsMessageLog.logMessage("Error deleting file: {}".format(dfile), 'Riverscapes Viewer', level=Qgis.Critical)
        self.setProgress(100)
