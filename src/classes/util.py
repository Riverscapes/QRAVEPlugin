import hashlib
import requests
import os
import json

from time import time, sleep
from qgis.core import QgsMessageLog, Qgis, QgsMessageLog, QgsTask, QgsApplication


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
