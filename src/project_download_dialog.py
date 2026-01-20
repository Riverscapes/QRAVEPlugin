import os
import re
import math
from datetime import datetime
from typing import List, Dict, Tuple
from qgis.PyQt.QtWidgets import QDialog, QTreeWidgetItem, QMessageBox, QHeaderView
from qgis.PyQt.QtCore import pyqtSignal, Qt, QUrl
from qgis.PyQt.QtGui import QFont, QBrush, QColor, QDesktopServices
from qgis.core import Qgis
from rsxml.etag import calculate_etag

from .ui.project_download_dialog import Ui_ProjectDownloadDialog
from .classes.data_exchange.DataExchangeAPI import DataExchangeAPI, DEProject
from .classes.data_exchange.downloader import DownloadQueue
from .classes.GraphQLAPI import RunGQLQueryTask
from .classes.settings import Settings
from .classes.util import get_project_details_html, extract_project_id
from .file_selection_widget import ProjectFileSelectionWidget

# Removed SortableTreeWidgetItem - now in file_selection_widget.py

class ProjectDownloadDialog(QDialog, Ui_ProjectDownloadDialog):
    projectDownloaded = pyqtSignal(str)
    
    def __init__(self, parent=None, project_id: str = None, local_path: str = None):
        super(ProjectDownloadDialog, self).__init__(parent)
        self.setupUi(self)
        
        self.settings = Settings()
        self.log = self.settings.log
        self.dataExchangeAPI = DataExchangeAPI(on_login=self._on_login)
        self.queue = DownloadQueue(log_callback=self._log_msg)
        
        self.project: DEProject = None
        self.locked_mode = isinstance(project_id, str) and len(project_id) > 0
        self.initial_project_id = project_id if isinstance(project_id, str) else None
        self.initial_local_path = local_path if isinstance(local_path, str) else None
        self.fetching_urls_cancelled = False
        
        # Connect signals
        self.btnVerifyProject.clicked.connect(self._verify_project)
        self.btnNext.clicked.connect(self._next_step)
        self.btnBack.clicked.connect(self._prev_step)
        self.btnCancel.clicked.connect(self._handle_cancel)
        self.txtProjectInput.textChanged.connect(self._reset_validation)
        self.fileWidget.fileChanged.connect(self._validate_folder)
        self.txtFolderName.textChanged.connect(self._validate_folder)
        self.btnHelp.clicked.connect(self.showHelp)
        
        # Replace UI selection area with shared widget
        self.btnSelectAll.hide()
        self.btnDeselectAll.hide()
        self.treeFiles.hide()
        
        self.fileSelection = ProjectFileSelectionWidget()
        self.fileSelection.set_allow_delete_visible(False)
        self.layout3.addWidget(self.fileSelection)

        self.queue.progress_signal.connect(self._on_file_progress)
        self.queue.overall_progress_signal.connect(self._on_overall_progress)
        self.queue.complete_signal.connect(self._on_download_complete)

        # Initial state
        
        # Initial state
        self.btnBack.setEnabled(False)
        self.btnNext.setEnabled(False)
        self.btnVerifyProject.setEnabled(False)
        self.btnVerifyProject.setText("Authenticating...")
        
        if self.locked_mode and self.initial_project_id:
            self.txtProjectInput.setText(self.initial_project_id)
            self.txtProjectInput.setReadOnly(True)
            # We don't verify yet, we wait for _on_login
            
            if self.initial_local_path:
                project_dir = os.path.dirname(self.initial_local_path)
                parent_dir = os.path.dirname(project_dir)
                folder_name = os.path.basename(project_dir)
                self.fileWidget.setFilePath(parent_dir)
                self.txtFolderName.setText(folder_name)
                self.fileWidget.setEnabled(False)
                self.txtFolderName.setReadOnly(True)
        
        # Restore last used download path if not already set
        if not self.fileWidget.filePath():
            last_path = self.settings.getValue('lastDownloadPath')
            if last_path and os.path.isdir(last_path):
                self.fileWidget.setFilePath(last_path)

    def _on_login(self, task):
        self.btnVerifyProject.setEnabled(True)
        self.btnVerifyProject.setText("Verify Project")
        
        if task.error:
            self._log_msg(f"Login failed: {task.error}", Qgis.Critical)
            self.lblProjectDetails.setText(f"<b style='color: #c0392b;'>Authentication Error:</b><br>{task.error}")
            self.frameProjectDetails.show()
        else:
            self._log_msg("Logged in to Data Exchange", Qgis.Info)
            if self.locked_mode and self.initial_project_id:
                self._verify_project()

    def showHelp(self):
        from .classes.settings import CONSTANTS
        help_url = CONSTANTS['webUrl'].rstrip('/') + '/software-help/help-qgis-downloader/'
        QDesktopServices.openUrl(QUrl(help_url))

    def _log_msg(self, message: str, level: int = Qgis.Info):
        self.log(message, level)

    def _reset_validation(self):
        self.project = None
        self.btnNext.setEnabled(False)
        self.lblProjectDetails.setText("")
        self.frameProjectDetails.hide()

    def _verify_project(self):
        project_id_raw = self.txtProjectInput.text().strip()
        if not project_id_raw:
            return
            
        # Extract ID from URL if necessary
        project_id = extract_project_id(project_id_raw)
        
        if not project_id:
             # If we couldn't extract an ID, it might be an invalid URL or format.
             # We'll fail early here or let it try to fetch if it looks like a crude ID.
             # But extract_project_id returns None for invalid formats, so we should probably warn.
             # However, let's behave similar to before: if it fails, maybe just use raw? 
             # No, the requirement is to be robust. If it returns None, it's invalid.
             self.lblProjectDetails.setText("<b style='color: #c0392b;'>Invalid Project ID or URL</b>")
             self.frameProjectDetails.show()
             return
        
        self.frameProjectDetails.show()
        self.lblProjectDetails.setText("<i>Verifying project...</i>")
        self.btnVerifyProject.setEnabled(False)
        
        self.dataExchangeAPI.get_project(project_id, self._handle_project_response)

    def _handle_project_response(self, task: RunGQLQueryTask, project: DEProject):
        self.btnVerifyProject.setEnabled(True)
        self.frameProjectDetails.show()
        
        if task.error:
            self.lblProjectDetails.setText(f"<div style='color: #c0392b; font-weight: bold;'>Error:</div><div style='color: #333;'>{task.error}</div>")
            self.btnNext.setEnabled(False)
            return

        if project:
            self.project = project
            self.lblProjectDetails.setText(get_project_details_html(project))
            self.btnNext.setEnabled(True)

            # If we're in locked mode (updating), we skip straight to step 3 once we've verified
            if self.locked_mode:
                self._next_step()
            
            # Pre-populate folder name if not in locked mode or if it's a remote project (no local path)
            if not self.locked_mode or (self.locked_mode and not self.initial_local_path):
                folder_name = re.sub(r'[^a-zA-Z0-9_\- ]', '', project.name).strip().replace(' ', '_')
                self.txtFolderName.setText(folder_name)
        else:
            self.lblProjectDetails.setText("<b style='color: #c0392b;'>Project not found.</b><br>Please check the ID or URL.")
            self.btnNext.setEnabled(False)

    def _validate_folder(self):
        if self.stackedWidget.currentIndex() != 1:
            return
            
        parent = self.fileWidget.filePath()
        name = self.txtFolderName.text().strip()
        
        if not parent or not name:
            self.btnNext.setEnabled(False)
            self.lblFolderStatus.setText("Please select a parent folder and enter a name.")
            return
            
        # Save the parent folder choice
        self.settings.setValue('lastDownloadPath', parent)
        
        full_path = os.path.join(parent, name)
        
        # Check for existence. 
        # If locked mode AND existing path (update), we usually skip this step.
        # If locked mode AND NO existing path (remote download), we treat it like a new download (warn if exists).
        
        if os.path.exists(full_path):
            # If we are strictly updating an existing project, we shouldn't be here (Step 2 skipped).
            # So if we are here, it means we are either:
            # 1. New download 
            # 2. Remote download (locked ID but picking folder)
            
            # In both cases, warn about existing folder.
            self.btnNext.setEnabled(False)
            self.lblFolderStatus.setText("A folder with this name already exists.\nIf you are updating an existing local project, please use the context menu on that project.")
        else:
            self.btnNext.setEnabled(True)
            self.lblFolderStatus.setText("")

    def _get_target_dir(self):
        if self.locked_mode and self.initial_local_path:
            return os.path.dirname(self.initial_local_path)
        parent = self.fileWidget.filePath()
        name = self.txtFolderName.text().strip()
        if not parent or not name:
            return None
        return os.path.join(parent, name)

    def _populate_file_tree(self):
        self.fileSelection.set_sorting_enabled(False)
        self.fileSelection.clear()
        if not self.project:
            return
            
        target_dir = self._get_target_dir()
            
        for rel_path, file_info in self.project.files.items():
            # Check if file exists locally
            local_file_path = os.path.join(target_dir, rel_path) if target_dir else None
            file_exists = local_file_path and os.path.exists(local_file_path)
            
            status_text = "New"
            is_locked = False
            needs_update = False
            highlight_color = None
            tooltip = None
            
            # Comparison logic
            if file_exists:
                try:
                    # S3 Multipart etags have a dash. If no dash, it's a simple MD5.
                    is_single_part = not re.match(r'.*-[0-9]+$', file_info.etag)
                    from rsxml.etag import calculate_etag
                    local_etag = calculate_etag(local_file_path, force_single_part=is_single_part)
                    
                    if local_etag == file_info.etag:
                        status_text = "Up to date"
                        is_locked = True
                        tooltip = "This file is already up to date."
                    else:
                        status_text = "Update available"
                        needs_update = True
                        highlight_color = "#2980b9"
                        tooltip = "The local file differs from the version on the Data Exchange."
                except Exception as e:
                    self.log(f"Error comparing etag for {rel_path}: {e}", Qgis.Warning)
                    status_text = "Check failed"
            
            # Special handling for mandatory manifest
            is_mandatory = False
            if rel_path.lower() == 'project.rs.xml':
                is_mandatory = True
                tooltip = "This file is mandatory and required to open the project in QGIS."
                if status_text == "New":
                    status_text = "Mandatory"
            
            self.fileSelection.add_file_item(
                rel_path=rel_path,
                size=file_info.size,
                status_text=status_text,
                checked=not is_locked or is_mandatory,
                is_locked=is_locked,
                is_mandatory=is_mandatory,
                highlight_color=highlight_color,
                tooltip=tooltip
            )
            
        self.fileSelection.set_sorting_enabled(True)
        self.fileSelection.sort_by_column(0, Qt.AscendingOrder)

    # Removed _select_all_files, _deselect_all_files, _set_all_check_state - now in file_selection_widget.py

    # Removed _human_size - now in file_selection_widget.py

    def _next_step(self):
        curr = self.stackedWidget.currentIndex()
        if curr == 0: # From Step 1 to 2
            if self.locked_mode and self.initial_local_path:
                # Skip Step 2 (Folder selection) and go straight to Step 3 (File tree)
                self.stackedWidget.setCurrentIndex(2)
                self.btnBack.setEnabled(True)
                self._populate_file_tree()
                self.btnNext.setText("Download")
                self.btnNext.setEnabled(True)
            else:
                # Normal flow or RemoteProject download (locked but no path)
                self.stackedWidget.setCurrentIndex(1)
                self.btnBack.setEnabled(True)
                self._validate_folder()
        elif curr == 1: # From Step 2 to 3
            self.stackedWidget.setCurrentIndex(2)
            self._populate_file_tree()
            self.btnNext.setText("Download")
            self.btnNext.setEnabled(True)
        elif curr == 2: # From Step 3 to 4
            self._start_download()
            
    def _prev_step(self):
        curr = self.stackedWidget.currentIndex()
        if curr == 1:
            self.stackedWidget.setCurrentIndex(0)
            self.btnBack.setEnabled(False)
            self.btnNext.setEnabled(True)
        elif curr == 2:
            if self.locked_mode:
                # Skip back to Step 1
                self.stackedWidget.setCurrentIndex(0)
                self.btnBack.setEnabled(False)
                self.btnNext.setText("Next")
                self.btnNext.setEnabled(True)
            else:
                self.stackedWidget.setCurrentIndex(1)
                self.btnNext.setText("Next")
                self._validate_folder()

    def _start_download(self):
        self.stackedWidget.setCurrentIndex(3)
        self.btnBack.setEnabled(False)
        self.btnNext.setEnabled(False)
        self.btnCancel.setText("Cancel Download")
        
        selected_files = self.fileSelection.get_selected_files()
        
        if not selected_files:
            QMessageBox.warning(self, "No files selected", "Please select at least one file to download.")
            self.stackedWidget.setCurrentIndex(2)
            self.btnNext.setEnabled(True)
            self.btnCancel.setText("Cancel")
            return
            
        self.queue.reset()
        parent = self.fileWidget.filePath()
        name = self.txtFolderName.text().strip()
        local_root = os.path.join(parent, name)
        
        self.lblStatus.setText("Fetching download URLs...")
        self.fetching_urls_cancelled = False
        self._fetch_urls_and_enqueue(selected_files, local_root)

    def _fetch_urls_and_enqueue(self, files: List[str], local_root: str):
        # We need to fetch URLs for each file. 
        # For simplicity in this implementation, we'll do them sequentially or batch them.
        # Ideally, there might be a batch GraphQL query for this, but let's use what we have.
        
        remaining = list(files)
        total = len(files)
        
        def _get_next_url():
            if self.fetching_urls_cancelled:
                return
            if not remaining:
                self.lblStatus.setText("Starting downloads...")
                self.queue.start()
                return
                
            rel_path = remaining.pop(0)
            self.lblStatus.setText(f"Getting URL for {rel_path} ({total - len(remaining)}/{total})")
            
            def _handle_url(task, ret_obj):
                if ret_obj and 'downloadUrl' in ret_obj:
                    abs_path = os.path.join(local_root, rel_path)
                    self.queue.enqueue(rel_path, abs_path, ret_obj['downloadUrl'], self.project.files[rel_path].size)
                    _get_next_url()
                else:
                    self._log_msg(f"Failed to get download URL for {rel_path}", Qgis.Critical)
                    # Skip for now, or handle error
                    _get_next_url()
                    
            self.dataExchangeAPI.get_download_url(self.project.id, rel_path, _handle_url)
            
        _get_next_url()

    def _on_file_progress(self, rel_path, downloaded, total):
        self.lblProgressDetails.setText(f"Downloading: {rel_path}\n{ProjectFileSelectionWidget.human_size(downloaded)} / {ProjectFileSelectionWidget.human_size(total)}")

    def _on_overall_progress(self, downloaded, total):
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progressBar.setValue(percent)
            self.lblStatus.setText(f"Overall Progress: {percent}% ({ProjectFileSelectionWidget.human_size(downloaded)} / {ProjectFileSelectionWidget.human_size(total)})")

    def _on_download_complete(self):
        if self.queue.failed_tasks:
            self.lblStatus.setText(f"Download Finished with {len(self.queue.failed_tasks)} error(s).")
            self._log_msg(f"Failed downloads: {', '.join(self.queue.failed_tasks)}", Qgis.Warning)
        else:
            self.lblStatus.setText("Download Complete!")
            
        self.btnCancel.setText("Close")
        self.btnNext.setVisible(False)
        self.btnBack.setVisible(False)
        
        if not self.queue.failed_tasks:
            # Emit signal with path to project.rs.xml
            parent = self.fileWidget.filePath()
            name = self.txtFolderName.text().strip()
            project_xml = os.path.join(parent, name, 'project.rs.xml')
            
            # If we were in locked mode, use the initial path
            if self.locked_mode and self.initial_local_path:
                project_xml = self.initial_local_path
                
            if os.path.exists(project_xml):
                self.projectDownloaded.emit(project_xml)

            QMessageBox.information(self, "Download Complete", "The project has been successfully downloaded.")
            self.accept()
        else:
            QMessageBox.warning(self, "Download Finished with Errors", f"{len(self.queue.failed_tasks)} file(s) failed to download. Check the logs for details.")

    def _handle_cancel(self):
        if self.stackedWidget.currentIndex() == 3 and self.btnCancel.text() == "Cancel Download":
            if QMessageBox.question(self, "Cancel Download", "Are you sure you want to cancel the download?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self.fetching_urls_cancelled = True
                self.queue.cancel_all()
                self.lblStatus.setText("Download Cancelled.")
                self.btnCancel.setText("Close")
        else:
            self.reject()
