from typing import List, Tuple, Callable, Dict
import os
import time
import json
import requests
from qgis.core import QgsTask, QgsApplication, Qgis
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

MAX_PROGRESS_INTERVAL = 1  # seconds

class DownloadFileTask(QgsTask):
    """
    Task to download a single file from a given URL.
    """
    def __init__(self, rel_path: str, abs_path: str, download_url: str, size: int, log_callback=None, progress_callback=None):
        super().__init__(f"Downloading {rel_path}", QgsTask.CanCancel)
        self.rel_path = rel_path
        self.abs_path = abs_path
        self.download_url = download_url
        self.total_size = size
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.exception = None

    def run(self):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.abs_path), exist_ok=True)

            response = requests.get(self.download_url, stream=True)
            response.raise_for_status()
            
            downloaded = 0
            last_progress_time = time.time()

            with open(self.abs_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.isCanceled():
                        return False
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress
                        curr_time = time.time()
                        if curr_time - last_progress_time > MAX_PROGRESS_INTERVAL:
                            if self.progress_callback:
                                self.progress_callback(self.rel_path, downloaded, self.total_size)
                            last_progress_time = curr_time

            if self.progress_callback:
                self.progress_callback(self.rel_path, downloaded, self.total_size)
            
            return True
        except Exception as e:
            self.exception = e
            if self.log_callback:
                self.log_callback(f"Error downloading {self.rel_path}: {str(e)}", Qgis.Critical)
            return False

    def finished(self, result):
        if result:
            if self.log_callback:
                self.log_callback(f"Successfully downloaded {self.rel_path}", Qgis.Info)
        elif self.isCanceled():
            if self.log_callback:
                self.log_callback(f"Download cancelled for {self.rel_path}", Qgis.Warning)
        else:
            if self.log_callback:
                self.log_callback(f"Failed to download {self.rel_path}: {self.exception}", Qgis.Critical)

class DownloadQueue(QObject):
    """
    Queue to manage multiple file downloads.
    """
    progress_signal = pyqtSignal(str, int, int)  # rel_path, downloaded, total
    overall_progress_signal = pyqtSignal(int, int) # downloaded, total
    complete_signal = pyqtSignal()
    cancelled_signal = pyqtSignal()
    all_tasks_done_signal = pyqtSignal(bool) # success

    MAX_CONCURRENT_DOWNLOADS = 4

    def __init__(self, log_callback=None):
        super().__init__()
        self.log = log_callback
        self.pending_tasks = []
        self.active_tasks = {}
        self.total_size = 0
        self.total_downloaded = 0
        self.file_progress = {} # rel_path -> downloaded
        self.is_cancelled = False
        self.failed_tasks = []

    def reset(self):
        self.pending_tasks = []
        self.active_tasks = {}
        self.total_size = 0
        self.total_downloaded = 0
        self.file_progress = {}
        self.is_cancelled = False
        self.failed_tasks = []

    def enqueue(self, rel_path: str, abs_path: str, download_url: str, size: int):
        task = DownloadFileTask(rel_path, abs_path, download_url, size, 
                                 log_callback=self.log, 
                                 progress_callback=self._on_progress)
        self.pending_tasks.append(task)
        self.total_size += size
        self.file_progress[rel_path] = 0

    def start(self):
        self.is_cancelled = False
        self._process_queue()

    def cancel_all(self):
        self.is_cancelled = True
        for task in self.active_tasks.values():
            task.cancel()
        self.pending_tasks = []
        self.cancelled_signal.emit()

    def _on_progress(self, rel_path, downloaded, total):
        self.file_progress[rel_path] = downloaded
        self.total_downloaded = sum(self.file_progress.values())
        self.progress_signal.emit(rel_path, downloaded, total)
        self.overall_progress_signal.emit(self.total_downloaded, self.total_size)

    def _process_queue(self):
        if self.is_cancelled:
            return

        while len(self.active_tasks) < self.MAX_CONCURRENT_DOWNLOADS and self.pending_tasks:
            task = self.pending_tasks.pop(0)
            self.active_tasks[task.rel_path] = task
            # Use a closure to capture the task
            task.taskCompleted.connect(lambda t=task: self._on_task_completed(t))
            task.taskTerminated.connect(lambda t=task: self._on_task_completed(t))
            QgsApplication.taskManager().addTask(task)

        if not self.active_tasks and not self.pending_tasks:
            self.complete_signal.emit()

    def _on_task_completed(self, task: DownloadFileTask):
        if task.rel_path in self.active_tasks:
            del self.active_tasks[task.rel_path]
        
            if task.status() != QgsTask.Complete:
                self.failed_tasks.append(task.rel_path)
            
            self._process_queue()
