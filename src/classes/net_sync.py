from __future__ import annotations

from glob import glob
import json
import os
from time import time

from qgis.core import Qgis, QgsMessageLog, QgsTask

from ..compat import QGSTASK_CAN_CANCEL, QGSTASK_SILENT
from .settings import CONSTANTS, Settings
from .util import md5, requestDownload

# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS["logCategory"]


class NetSync(QgsTask):
    def __init__(self, description: str) -> None:
        super().__init__(description, QGSTASK_CAN_CANCEL | QGSTASK_SILENT)
        self.total = 0
        self.iterations = 0
        self.exception = None
        self.progress = 0
        self.downloaded = 0

        self.resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "resources"))
        self.business_logic_xml_dir = os.path.abspath(os.path.join(self.resource_dir, CONSTANTS["businessLogicDir"]))
        self.symbology_dir = os.path.abspath(os.path.join(self.resource_dir, CONSTANTS["symbologyDir"]))
        self.qris_dir = os.path.abspath(os.path.join(self.resource_dir, CONSTANTS["qrisDir"]))
        self.digest_path = os.path.abspath(os.path.join(self.resource_dir, "index.json"))

        self.initialized = False  # self.initialize sets this
        self.need_sync = True  # self.initialize sets this

        self._initialize()

    # EVERYTHING BELOW HERE IS ASYNC

    def run(self) -> bool:

        self._updateDigest()
        self._syncFiles()
        return True

    def cancel(self) -> None:
        QgsMessageLog.logMessage(f'Net Sync "{self.description()}" was canceled', MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()

    def finished(self, result: bool | None = None) -> None:
        """This is called when doSomething is finished.
        Exception is not None if doSomething raises an exception.
        result is the return value of doSomething."""
        settings = Settings()
        if self.exception is None:
            if result is None:
                settings.log("Completed with no exception and no result (probably manually canceled by the user)", Qgis.Warning)
            else:
                settings.setValue("initialized", True)
                settings.msg_bar("Riverscapes Resources Sync Success", f"{self.total} files checked, {self.downloaded} updated", Qgis.Success)
                if result:
                    settings.setValue("lastDigestSync", int(time()))

        else:
            settings.msg_bar("Error syncing network resources", f"Exception: {self.exception}", Qgis.Critical)
            # raise Exception(self.exception)

    def _initialize(self) -> None:
        need_sync = False
        if not os.path.isdir(self.resource_dir):
            need_sync = True
            os.makedirs(self.resource_dir, exist_ok=True)
        if not os.path.isdir(self.symbology_dir):
            need_sync = True
            os.makedirs(self.symbology_dir, exist_ok=True)
        if not os.path.isdir(self.business_logic_xml_dir):
            need_sync = True
            os.makedirs(self.business_logic_xml_dir, exist_ok=True)
        if not os.path.isdir(self.qris_dir):
            need_sync = True
            os.makedirs(self.qris_dir, exist_ok=True)
        if not os.path.isfile(self.digest_path):
            need_sync = True

        self.initialized = True
        self.need_sync = need_sync

    def _updateDigest(self) -> None:
        # Now get the JSON file
        json_url = CONSTANTS["resourcesUrl"] + "index.json"
        QgsMessageLog.logMessage(f"Requesting digest from: {json_url}", MESSAGE_CATEGORY, level=Qgis.Info)
        requestDownload(json_url, self.digest_path)

    def _syncFiles(self) -> None:
        if not os.path.isfile(self.digest_path):
            raise Exception(f"Digest file could not be found at: {self.digest_path}")

        with open(self.digest_path) as fl:
            digest = json.load(fl)

        symbologies = {x: v for x, v in digest.items() if x.startswith("Symbology/qgis") and x.endswith(".qml")}
        businesslogics = {x: v for x, v in digest.items() if x.startswith("RaveBusinessLogic") and x.endswith(".xml")}
        qris = {x: v for x, v in digest.items() if x.startswith("QRiS") and (x.endswith(".json") or x.endswith(".xml"))}
        basemaps = {x: v for x, v in digest.items() if x.startswith("BaseMaps.xml")}

        self.total = len(symbologies) + len(businesslogics) + len(qris) + 1
        self.progress = 0
        self.downloaded = 0

        all_local_files = [os.path.abspath(x) for x in glob(os.path.join(self.resource_dir, "**", "*.?ml"), recursive=True)] + [os.path.abspath(x) for x in glob(os.path.join(self.resource_dir, "**", "*.json"), recursive=True)]

        # Symbologies have directory structure
        for remote_path, remote_md5 in symbologies.items():
            local_path = os.path.abspath(os.path.join(self.symbology_dir, *remote_path.replace("Symbology/qgis/", "").split("/")))

            # There might be subdirs to make here
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            if not os.path.isfile(local_path) or remote_md5 != md5(local_path):
                requestDownload(CONSTANTS["resourcesUrl"] + remote_path, local_path, remote_md5)
                QgsMessageLog.logMessage(f"Symobology downloaded: {local_path}", MESSAGE_CATEGORY, level=Qgis.Info)

                self.downloaded += 1
            all_local_files = [x for x in all_local_files if x != local_path]
            self.progress += 1
            self.setProgress(self.progress)

        for remote_path, remote_md5 in businesslogics.items():
            local_path = os.path.join(self.business_logic_xml_dir, os.path.relpath(remote_path, "RaveBusinessLogic"))
            if not os.path.isfile(local_path) or remote_md5 != md5(local_path):
                requestDownload(CONSTANTS["resourcesUrl"] + remote_path, local_path, remote_md5)
                QgsMessageLog.logMessage(f"BusinessLogic downloaded: {local_path}", MESSAGE_CATEGORY, level=Qgis.Info)

                self.downloaded += 1
            all_local_files = [x for x in all_local_files if x != local_path]
            self.progress += 1
            self.setProgress(self.progress)

        for remote_path, remote_md5 in qris.items():
            local_path = os.path.join(self.qris_dir, os.path.relpath(remote_path, "QRiS"))
            if not os.path.isfile(local_path) or remote_md5 != md5(local_path):
                requestDownload(CONSTANTS["resourcesUrl"] + remote_path, local_path, remote_md5)
                QgsMessageLog.logMessage(f"QRiS Resource downloaded: {local_path}", MESSAGE_CATEGORY, level=Qgis.Info)

                self.downloaded += 1
            all_local_files = [x for x in all_local_files if x != local_path]
            self.progress += 1
            self.setProgress(self.progress)

        # Basemaps is a special case
        for remote_path, remote_md5 in basemaps.items():
            local_path = os.path.join(self.resource_dir, os.path.basename(remote_path))
            if not os.path.isfile(local_path) or remote_md5 != md5(local_path):
                requestDownload(CONSTANTS["resourcesUrl"] + remote_path, local_path, remote_md5)
                QgsMessageLog.logMessage(f"Basemaps downloaded: {local_path}", MESSAGE_CATEGORY, level=Qgis.Info)

                self.downloaded += 1
            all_local_files = [x for x in all_local_files if x != local_path]
            self.progress += 1
            self.setProgress(self.progress)

        # Now we clean up any files that aren't supposed to be there
        for dfile in all_local_files:
            try:
                if dfile == self.digest_path:
                    continue
                # Do a quick (probably redundant check) to make sure this file is in our current folder
                rel_check = os.path.relpath(dfile, os.path.join(os.path.dirname(__file__), "..", "..", "resources"))
                from pathlib import Path as _Path

                rel_parts = _Path(rel_check).parts
                # Guard: only delete files that live *within* the resources directory
                # (rel_parts[0] == '..' means the file resolved above the root).
                if rel_parts and rel_parts[0] != "..":
                    os.remove(dfile)
                    QgsMessageLog.logMessage(f"Extraneous file removed: {dfile}", MESSAGE_CATEGORY, level=Qgis.Warning)
                else:
                    QgsMessageLog.logMessage(f"Skipping file outside resources directory: {dfile}", MESSAGE_CATEGORY, level=Qgis.Critical)
            except Exception:
                QgsMessageLog.logMessage(f"Error deleting file: {dfile}", MESSAGE_CATEGORY, level=Qgis.Critical)
        self.setProgress(100)
