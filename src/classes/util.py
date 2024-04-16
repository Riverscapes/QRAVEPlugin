from typing import Dict
import hashlib
import requests
import os

from qgis.core import QgsMessageLog, Qgis, QgsMessageLog
from .settings import CONSTANTS

# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS['logCategory']
# In order to calculate etags correctly we need the multipart file sizes to be exactly the same
MULTIPART_CHUNK_SIZE = 50 * pow(1024, 2)
# On the S3 client the threshold can be different than the chnk size.
MULTIPART_THRESHOLD = 50 * pow(1024, 2)

# for uploading files to S3, we need to upload in chunks
# This has nothing to do with multipart uploads but rather how often we send a progress signal
# Back to the UI. We set thgis as 1Mb
UPLOAD_PROGESS_CHUNK_SIZE = 1 * pow(1024, 2)


def md5(fname: str) -> str:
    """ Calculate the MD5 hash of a file. Used to check downloaded files against a known hash.
    Also used to calculate the ETag for a file.

    Args:
        fname (str): _description_

    Returns:
        str: _description_
    """
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
    """ Request a file from a remote URL and return the content. Optionally check the MD5 hash of the file.

    Args:
        remote_url (str): _description_
        expected_md5 (_type_, optional): _description_. Defaults to None.

    Raises:
        SystemExit: _description_

    Returns:
        _type_: _description_
    """
    # Get a file and put it somewhere local
    try:
        resp = requests.get(url=remote_url, timeout=15)
        return resp.content

    except requests.exceptions.Timeout:
        QgsMessageLog.logMessage("Fetching digest timed out: {}".format(remote_url), MESSAGE_CATEGORY, level=Qgis.Critical)
        return False
        # Maybe set up for a retry, or continue in a retry loop
    except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
        QgsMessageLog.logMessage("Fetching digest failed with too many redirects: {}".format(remote_url), MESSAGE_CATEGORY, level=Qgis.Critical)
        return False
    except requests.exceptions.RequestException as e:
        QgsMessageLog.logMessage("Unknown error downloading file: {}".format(remote_url), MESSAGE_CATEGORY, level=Qgis.Critical)
        # catastrophic error. bail.
        raise SystemExit(e)
    return True


def requestDownload(remote_url: str, local_path: str, expected_md5=None):
    """ Request a file from a remote URL and save it to a local path. Optionally check the MD5 hash of the file.

    Args:
        remote_url (str): _description_
        local_path (str): _description_
        expected_md5 (_type_, optional): _description_. Defaults to None.

    Raises:
        SystemExit: _description_

    Returns:
        _type_: _description_
    """
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
            QgsMessageLog.logMessage("MD5 did not match expected for file: {}".format(remote_url), MESSAGE_CATEGORY, level=Qgis.Warning)
            return False

    except requests.exceptions.Timeout:
        QgsMessageLog.logMessage("Fetching file timed out: {}".format(remote_url), MESSAGE_CATEGORY, level=Qgis.Critical)
        return False
        # Maybe set up for a retry, or continue in a retry loop
    except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
        QgsMessageLog.logMessage("Fetching file failed with too many redirects: {}".format(remote_url), MESSAGE_CATEGORY, level=Qgis.Critical)
        return False
    except requests.exceptions.RequestException as e:
        QgsMessageLog.logMessage("Unknown error downloading file: {}".format(remote_url), MESSAGE_CATEGORY, level=Qgis.Critical)
        # catastrophic error. bail.
        raise SystemExit(e)
    return True


def error_level_to_str(level: int) -> str:
    """ Convert an error level to a string for logging.

    Args:
        level (int): _description_

    Returns:
        str: _description_
    """
    if level == Qgis.Critical:
        return 'Critical'
    elif level == Qgis.Warning:
        return 'Warning'
    elif level == Qgis.Success:
        return 'Success'
    else:
        return 'Info'


def calculate_etag(
    file_path: str,
    chunk_size_bytes: int = MULTIPART_CHUNK_SIZE,
    chunk_thresh_bytes: int = MULTIPART_THRESHOLD
) -> Dict[str, str]:
    """ We need a way to calculate the ETag for a file, which is a hash of the file contents. 
    If the file is small enough, we can just hash the whole thing. 
    If it's too big, we need to hash it in chunks.

    This should mirror the way AWS S3 calculates ETags for multipart uploads.

    Args:
        file_path (str): _description_
        chunk_size_bytes (int): _description_
        chunk_thresh_bytes (int): _description_

    Returns:
        Dict[str, str]: _description_
    """
    file_size_in_bytes = os.path.getsize(file_path)

    if file_size_in_bytes < chunk_thresh_bytes:
        with open(file_path, 'rb') as f:
            fbytes_read = f.read()
        etag = hashlib.md5(fbytes_read).hexdigest()
    else:
        parts = file_size_in_bytes // chunk_size_bytes
        if file_size_in_bytes % chunk_size_bytes > 0:
            parts += 1
        total_md5 = ''
        with open(file_path, 'rb') as file:
            for part in range(parts):
                skip_bytes = chunk_size_bytes * part
                total_bytes_left = file_size_in_bytes - skip_bytes
                bytes_to_read = min(total_bytes_left, chunk_size_bytes)
                file.seek(skip_bytes)
                buffer = file.read(bytes_to_read)
                total_md5 += hashlib.md5(buffer).hexdigest()
        combined_hash = hashlib.md5(bytes.fromhex(total_md5)).hexdigest()
        etag = f'{combined_hash}-{parts}'

    return {
        'size': file_size_in_bytes,
        'etag': f'"{etag}"',
    }
