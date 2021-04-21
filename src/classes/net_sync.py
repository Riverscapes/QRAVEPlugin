import traceback
import requests
import os
import json
import hashlib

from time import time, sleep
from qgis.core import QgsMessageLog, Qgis, QgsMessageLog, QgsTask, QgsApplication

from .settings import Settings, CONSTANTS

MESSAGE_CATEGORY = CONSTANTS['logCategory']


class NetSync():

    def __init__(self, labelcb=None, progresscb=None, finishedcb=None):

        self.settings = Settings()
        self.labelcb = labelcb
        self.progresscb = progresscb
        self.finishedcb = finishedcb

        self.resource_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'resources')
        self.business_logic_xml_dir = os.path.join(self.resource_dir, CONSTANTS['businessLogicDir'])
        self.symbology_dir = os.path.join(self.resource_dir, CONSTANTS['symbologyDir'])
        self.digest_path = os.path.join(self.resource_dir, 'index.json')

        self.initialized = False  # self.initialize sets this
        self.need_sync = True  # self.initialize sets this

        self.initialize()

    def set_progress(self, task, val: int):
        task.setProgress(val)
        if self.progresscb is not None:
            self.progresscb(val)

    def set_label(self, task, labelval: str):
        QgsMessageLog.logMessage(labelval, MESSAGE_CATEGORY, Qgis.Info)
        if self.labelcb is not None:
            self.labelcb(labelval)

    def run(self, task):
        """
        Raises an exception to abort the task.
        Returns a result if success.
        The result will be passed, together with the exception (None in
        the case of success), to the on_finished method.
        If there is an exception, there will be no result.
        """

        QgsMessageLog.logMessage('Started QRAVE Sync: {}'.format(task.description()),
                                 MESSAGE_CATEGORY, Qgis.Info)
        self.set_progress(task, 0)
        self.updateDigest(task)
        self.syncFiles(task)
        if self.finishedcb is not None:
            self.finishedcb()
        return True

    def stopped(self, task):
        QgsMessageLog.logMessage(
            'Task "{name}" was canceled'.format(
                name=task.description()),
            MESSAGE_CATEGORY, Qgis.Info)

    def completed(self, exception, result=None):
        """This is called when doSomething is finished.
        Exception is not None if doSomething raises an exception.
        result is the return value of doSomething."""
        if exception is None:
            if result is None:
                QgsMessageLog.logMessage(
                    'Completed with no exception and no result '
                    '(probably manually canceled by the user)',
                    MESSAGE_CATEGORY, Qgis.Warning)
            else:
                self.settings.setValue('initialized', True)
                QgsMessageLog.logMessage(
                    'Task {name} completed\n'
                    'Total: {total} ( with {iterations} '
                    'iterations)'.format(
                        name=result['task'],
                        total=result['total'],
                        iterations=result['iterations']),
                    MESSAGE_CATEGORY, Qgis.Info)
        else:
            QgsMessageLog.logMessage("Exception: {}".format(exception),
                                     MESSAGE_CATEGORY, Qgis.Critical)
            raise exception

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

    def updateDigest(self, task):
        self.set_label(task, 'Updating digest')
        # Now get the JSON file
        json_url = CONSTANTS['resourcesUrl'] + 'index.json'
        result = requestDownload(json_url, self.digest_path)
        if result is True:
            self.settings.setValue('lastDigestSync', int(time()))

    def syncFiles(self, task):
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
            self.set_label(task, 'Updating files {}/{}'.format(progress, total))
            self.set_progress(task, int(100 * progress / total))

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

        self.set_progress(task, 100)
        if downloaded == 0:
            self.set_label(task, 'No symbology or xml updates needed. 0 files downloaded')
        else:
            self.set_label(task, 'Downloaded and updated {}/{} symbology or xml files'.format(downloaded, total))


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
