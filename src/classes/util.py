import hashlib
import requests
import os
import json

from time import time, sleep
from qgis.core import QgsMessageLog, Qgis, QgsMessageLog, QgsTask, QgsApplication
from .settings import Settings


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


def requestFetch(remote_url: str, expected_md5=None):
    # Get a file and put it somewhere local
    try:
        resp = requests.get(url=remote_url, timeout=15)
        return resp.content

    except requests.exceptions.Timeout:
        QgsMessageLog.logMessage("Fetching digest timed out: {}".format(remote_url), 'Riverscapes Viewer', level=Qgis.Critical)
        return False
        # Maybe set up for a retry, or continue in a retry loop
    except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
        QgsMessageLog.logMessage("Fetching digest failed with too many redirects: {}".format(remote_url), 'Riverscapes Viewer', level=Qgis.Critical)
        return False
    except requests.exceptions.RequestException as e:
        QgsMessageLog.logMessage("Unknown error downloading file: {}".format(remote_url), 'Riverscapes Viewer', level=Qgis.Critical)
        # catastrophic error. bail.
        raise SystemExit(e)
    return True


def requestDownload(remote_url: str, local_path: str, expected_md5=None):
    # Get a file and put it somewhere local
    try:
        resp = requests.get(url=remote_url, timeout=15, headers={'Cache-Control': 'no-cache'})
        local_dir = os.path.dirname(local_path)     # Excludes file name
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
        with open(local_path, 'wb') as lf:
            lf.write(resp.content)

        # Do an MD5 check if we need to
        if os.path.isfile(local_path) and expected_md5 is not None and expected_md5 != md5(local_path):
            os.remove(local_path)
            QgsMessageLog.logMessage("MD5 did not match expected for file: {}".format(remote_url), 'Riverscapes Viewer', level=Qgis.Warning)
            return False

    except requests.exceptions.Timeout:
        QgsMessageLog.logMessage("Fetching file timed out: {}".format(remote_url), 'Riverscapes Viewer', level=Qgis.Critical)
        return False
        # Maybe set up for a retry, or continue in a retry loop
    except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
        QgsMessageLog.logMessage("Fetching file failed with too many redirects: {}".format(remote_url), 'Riverscapes Viewer', level=Qgis.Critical)
        return False
    except requests.exceptions.RequestException as e:
        QgsMessageLog.logMessage("Unknown error downloading file: {}".format(remote_url), 'Riverscapes Viewer', level=Qgis.Critical)
        # catastrophic error. bail.
        raise SystemExit(e)
    return True
