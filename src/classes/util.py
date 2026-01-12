from typing import Dict
import hashlib
import requests
import os

from datetime import datetime
from qgis.core import QgsMessageLog, Qgis
from .settings import CONSTANTS

# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS['logCategory']
# In order to calculate etags correctly we need the multipart file sizes to be exactly the same
MULTIPART_CHUNK_SIZE = 50 * pow(1024, 2)
# On the S3 client the threshold can be different than the chnk size.
MULTIPART_THRESHOLD = 50 * pow(1024, 2)


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
        QgsMessageLog.logMessage(f"Unknown error downloading file: {remote_url} | {e}", MESSAGE_CATEGORY, level=Qgis.Critical)
        # catastrophic error. bail.
        return False
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
        resp.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
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
        return False
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


def humane_bytes(size: int, precision: int = 1) -> str:
    """ Convert a byte size to a human readable string.

    Args:
        size (int): _description_

    Returns:
        str: _description_
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            break
        size /= 1024.0
    if unit == 'B':
        precision = 0

    return f"{size:.{precision}f} {unit}"


def get_project_details_html(project) -> str:
    """ Generate HTML for project details to be shown in a QLabel.
    
    Args:
        project (DEProject): The project object from DataExchangeAPI
        
    Returns:
        str: HTML string
    """
    if not project:
        return ""
        
    # Extract names from nested objects
    p_type = project.projectType.get('name', 'Unknown Type') if project.projectType else 'Unknown Type'
    owner = project.ownedBy.get('name', 'Unknown Owner') if project.ownedBy else 'Unknown Owner'
    
    # Format dates
    def pretty_date(iso_str):
        if not iso_str: return "Unknown"
        try:
            # Generic ISO parsing
            dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
            return dt.strftime('%B %d, %Y')
        except Exception:
            return iso_str

    created = pretty_date(project.createdOn)
    updated = pretty_date(project.updatedOn)
    
    # Visibility styling
    vis_color = "#27ae60" if project.visibility == "PUBLIC" else "#e67e22"
    
    # Tags styling
    tags_html = ""
    if project.tags:
        tags_list = [f"<span style='background-color: #f1f1f1; color: #555; border-radius: 3px; padding: 1px 4px; margin-right: 6px;'>{t}</span>" for t in project.tags]
        tags_html = f"<div style='margin-top: 8px;'>{' '.join(tags_list)}</div>"

    html = f"""
    <div style="font-family: sans-serif;">
        <div style="font-size: 14pt; font-weight: bold; color: #2c3e50;">{project.name}</div>
        <div style="font-size: 10pt; color: #7f8c8d; margin-bottom: 10px;">{p_type}</div>
        
        <table border="0" cellpadding="3" cellspacing="0" style="width: 100%;">
            <tr><td style="color: #95a5a6; width: 90px;">Owner:</td><td><b>{owner}</b></td></tr>
            <tr><td style="color: #95a5a6;">Visibility:</td><td><span style="color: {vis_color}; font-weight: bold;">{project.visibility}</span></td></tr>
            <tr><td style="color: #95a5a6;">Created:</td><td>{created}</td></tr>
            <tr><td style="color: #95a5a6;">Updated:</td><td>{updated}</td></tr>
            <tr><td style="color: #95a5a6;">Total Files:</td><td>{len(project.files)}</td></tr>
        </table>
    """
    
    if project.summary:
        html += f"""
        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; color: #34495e;">
            {project.summary}
        </div>
        """
        
    if tags_html:
        html += f"""
        <div style="margin-top: 10px; padding-top: 5px; border-top: 1px solid #eee;">
            Tags: {tags_html}
        </div>
        """
        
    html += "</div>"
    return html
