import os
import re
import math
from datetime import datetime
from typing import List, Dict, Tuple
from qgis.PyQt.QtWidgets import QDialog, QTreeWidgetItem, QMessageBox, QHeaderView
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtGui import QFont, QBrush
from qgis.core import Qgis

from .ui.project_download_dialog import Ui_ProjectDownloadDialog
from .classes.data_exchange.DataExchangeAPI import DataExchangeAPI, DEProject
from .classes.data_exchange.downloader import DownloadQueue
from .classes.GraphQLAPI import RunGQLQueryTask
from .classes.settings import Settings

class SortableTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        if column == 1:  # Size column
            size_raw_self = self.data(column, Qt.UserRole)
            size_raw_other = other.data(column, Qt.UserRole)
            if isinstance(size_raw_self, (int, float)) and isinstance(size_raw_other, (int, float)):
                return size_raw_self < size_raw_other
        return super().__lt__(other)

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
        
        self.btnSelectAll.clicked.connect(self._select_all_files)
        self.btnDeselectAll.clicked.connect(self._deselect_all_files)
        
        self.queue.progress_signal.connect(self._on_file_progress)
        self.queue.overall_progress_signal.connect(self._on_overall_progress)
        self.queue.complete_signal.connect(self._on_download_complete)
        
        # Enable sorting on tree widget
        self.treeFiles.setSortingEnabled(True)
        self.treeFiles.setAlternatingRowColors(True)
        self.treeFiles.header().setSectionsClickable(True)
        self.treeFiles.header().setSortIndicatorShown(True)
        self.treeFiles.header().setStretchLastSection(False)
        self.treeFiles.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.treeFiles.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
        # Initial state
        self.btnBack.setEnabled(False)
        self.btnNext.setEnabled(False)
        
        if self.locked_mode and self.initial_project_id:
            self.txtProjectInput.setText(self.initial_project_id)
            self.txtProjectInput.setReadOnly(True)
            self.btnVerifyProject.setEnabled(True)
            self._verify_project() # Auto verify
            
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
        if task.error:
            self._log_msg(f"Login failed: {task.error}", Qgis.Critical)
        else:
            self._log_msg("Logged in to Data Exchange", Qgis.Info)

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
        # Pattern: https://data.riverscapes.net/p/ac104f27-93b7-4e47-b279-7a7dad8ccf1d/
        match = re.search(r'/p/([a-f0-9\-]+)', project_id_raw)
        project_id = match.group(1) if match else project_id_raw
        
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
            
            self.lblProjectDetails.setText(html)
            self.btnNext.setEnabled(True)
            
            # Pre-populate folder name if not in locked mode
            if not self.locked_mode:
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
        if os.path.exists(full_path) and not self.locked_mode:
            self.btnNext.setEnabled(False)
            self.lblFolderStatus.setText("A folder with this name already exists.\nIf you're trying to update an existing project please load it into the Viewer first\nand then right click on it to \"Download or Update Project\".")
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
        self.treeFiles.setSortingEnabled(False)  # Disable while populating
        self.treeFiles.clear()
        if not self.project:
            return
            
        target_dir = self._get_target_dir()
            
        for rel_path, file_info in self.project.files.items():
            item = SortableTreeWidgetItem(self.treeFiles)
            item.setText(0, rel_path)
            item.setText(1, self._human_size(file_info.size))
            item.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            item.setCheckState(0, Qt.Checked)
            item.setData(0, Qt.UserRole, rel_path)
            item.setData(1, Qt.UserRole, file_info.size)  # Store raw size for sorting
            
            # Check if file exists locally
            local_file_path = os.path.join(target_dir, rel_path) if target_dir else None
            file_exists = local_file_path and os.path.exists(local_file_path)
            
            if rel_path.lower() == 'project.rs.xml':
                item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
                item.setToolTip(0, "This file is mandatory and required to open the project in QGIS.")
                font = item.font(0)
                font.setItalic(True)
                item.setFont(0, font)
                item.setFont(1, font)
            elif file_exists:
                item.setCheckState(0, Qt.Unchecked)
                item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
                item.setToolTip(0, "This file has already been downloaded.")
                item.setForeground(0, QBrush(Qt.gray))
                item.setForeground(1, QBrush(Qt.gray))
                font = item.font(0)
                font.setStrikeOut(True)
                item.setFont(0, font)
            
        self.treeFiles.setSortingEnabled(True)  # Re-enable
        self.treeFiles.sortByColumn(0, Qt.AscendingOrder)

    def _select_all_files(self):
        self._set_all_check_state(Qt.Checked)

    def _deselect_all_files(self):
        self._set_all_check_state(Qt.Unchecked)

    def _set_all_check_state(self, state: Qt.CheckState):
        root = self.treeFiles.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(0, state)

    def _human_size(self, nbytes):
        if nbytes == 0:
            return '0 B'
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        i = 0
        while nbytes >= 1024 and i < len(suffixes)-1:
            nbytes /= 1024.
            i += 1
            
        # Calculate precision for 2 significant digits
        precision = 2 - int(math.floor(math.log10(abs(nbytes)))) - 1
        nbytes = round(nbytes, precision)
            
        # Format to string, avoid unnecessary decimals for large numbers
        if nbytes >= 10:
            f = str(int(nbytes))
        else:
            f = ("%.1f" % nbytes).rstrip('0').rstrip('.')
            
        return '%s %s' % (f, suffixes[i])

    def _next_step(self):
        curr = self.stackedWidget.currentIndex()
        if curr == 0: # From Step 1 to 2
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
            self.stackedWidget.setCurrentIndex(1)
            self.btnNext.setText("Next")
            self._validate_folder()

    def _start_download(self):
        self.stackedWidget.setCurrentIndex(3)
        self.btnBack.setEnabled(False)
        self.btnNext.setEnabled(False)
        self.btnCancel.setText("Cancel Download")
        
        selected_files = []
        root = self.treeFiles.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.checkState(0) == Qt.Checked:
                selected_files.append(item.data(0, Qt.UserRole))
        
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
        self.lblProgressDetails.setText(f"Downloading: {rel_path}\n{self._human_size(downloaded)} / {self._human_size(total)}")

    def _on_overall_progress(self, downloaded, total):
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progressBar.setValue(percent)
            self.lblStatus.setText(f"Overall Progress: {percent}% ({self._human_size(downloaded)} / {self._human_size(total)})")

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
