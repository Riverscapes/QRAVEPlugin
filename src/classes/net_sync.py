import traceback
import requests
import os
import json
import hashlib

from time import time, sleep
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtCore import pyqtSlot, pyqtSignal
from .settings import Settings, CONSTANTS


class NetSync():

    def __init__(self, labelcb=None, progresscb=None, closecb=None):

        def nullfunc():
            pass

        self.settings = Settings()
        self.labelcb = labelcb if labelcb is not None else nullfunc
        self.progresscb = progresscb if progresscb is not None else nullfunc
        self.closecb = closecb if closecb is not None else nullfunc

        self.resource_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'resources')
        self.symbology_dir = os.path.join(self.resource_dir, CONSTANTS['businessLogicDir'])
        self.business_logic_xml_dir = os.path.join(self.resource_dir, CONSTANTS['symbologyDir'])
        self.digest_path = os.path.join(self.resource_dir, 'index.json')

        self.initialized = False  # self.initialize sets this
        self.need_sync = True  # self.initialize sets this

        self.initialize()

    def run(self):
        """Long-running task."""
        self.progresscb(0)

        self.updateDigest()
        self.syncFiles()
        self.closecb()

    def initialize(self):
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

    def updateDigest(self):
        self.labelcb('Updating digest')
        # Now get the JSON file
        json_url = CONSTANTS['resourcesUrl'] + 'index.json'
        result = requestDownload(json_url, self.digest_path)
        if result is True:
            self.settings.setValue('lastDigestSync', int(time()))

    def syncFiles(self):
        digest = {}
        if not os.path.isfile(self.digest_path):
            QgsMessageLog.logMessage("Digest file could not be found", 'QRAVE', level=Qgis.Warning)
            return

        with open(self.digest_path) as fl:
            digest = json.load(fl)

        symbologies = {x: v for x, v in digest.items() if x.startswith('Symbology/qgis') and x.endswith('.qml')}
        businesslogics = {x: v for x, v in digest.items() if x.startswith('RaveBusinessLogic') and x.endswith('.xml')}
        basemaps = {x: v for x, v in digest.items() if x.startswith('BaseMaps.xml')}

        total = len(symbologies.keys()) + len(businesslogics.keys()) + 1
        progress = 0
        downloaded = 0

        def update_progress():
            self.labelcb('Updating files {}/{}'.format(progress, total))
            self.progresscb(int(100 * progress / total))

        for remote_path, remote_md5 in symbologies.items():
            local_path = os.path.join(self.symbology_dir, os.path.basename(remote_path))
            if not os.path.isfile(local_path) or remote_md5 != md5(local_path):
                QgsMessageLog.logMessage("Symobology download: {}".format(local_path), 'QRAVE', level=Qgis.Warning)
                requestDownload(CONSTANTS['resourcesUrl'] + remote_path, local_path, remote_md5)
                downloaded += 1
            progress += 1
            update_progress()

        for remote_path, remote_md5 in businesslogics.items():
            local_path = os.path.join(self.business_logic_xml_dir, os.path.basename(remote_path))
            if not os.path.isfile(local_path) or remote_md5 != md5(local_path):
                QgsMessageLog.logMessage("BusinessLogic download: {}".format(local_path), 'QRAVE', level=Qgis.Warning)
                requestDownload(CONSTANTS['resourcesUrl'] + remote_path, local_path, remote_md5)
                downloaded += 1
            progress += 1
            update_progress()

        # Basemaps is a special case
        for remote_path, remote_md5 in basemaps.items():
            local_path = os.path.join(self.resource_dir, os.path.basename(remote_path))
            if not os.path.isfile(local_path) or remote_md5 != md5(local_path):
                QgsMessageLog.logMessage("Basemaps download: {}".format(local_path), 'QRAVE', level=Qgis.Warning)
                requestDownload(CONSTANTS['resourcesUrl'] + remote_path, local_path, remote_md5)
                downloaded += 1
            progress += 1
            update_progress()

        self.progresscb(100)
        if downloaded == 0:
            self.labelcb('No symbology or xml updates needed. 0 files downloaded')
        else:
            self.labelcb('Downloaded and updated {}/{} symbology or xml files'.format(downloaded, total))


def md5(fname: str) -> str:
    try:
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(e)
        return None


def requestDownload(remote_url: str, local_path: str, expected_md5=None):
    # Get a file and put it somewhere local
    try:
        resp = requests.get(url=remote_url, timeout=15)
        open(local_path, 'wb').write(resp.content)

        # Do an MD5 check if we need to
        if os.path.isfile(local_path) and expected_md5 is not None and expected_md5 != md5(local_path):
            os.remove()
            QgsMessageLog.logMessage("MD5 did not match expected for file: {}".format(remote_url), 'QRAVE', level=Qgis.Warning)
            return False

    except requests.exceptions.Timeout:
        QgsMessageLog.logMessage("Fetching digest timed out: {}".format(remote_url), 'QRAVE', level=Qgis.Warning)
        return False
        # Maybe set up for a retry, or continue in a retry loop
    except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
        QgsMessageLog.logMessage("Fetching digest failed with too many redirects: {}".format(remote_url), 'QRAVE', level=Qgis.Warning)
        return False
    except requests.exceptions.RequestException as e:
        QgsMessageLog.logMessage("Unknown error downloading file: {}".format(remote_url), 'QRAVE', level=Qgis.Warning)
        # catastrophic error. bail.
        raise SystemExit(e)
    return True
