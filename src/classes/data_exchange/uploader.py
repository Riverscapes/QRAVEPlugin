from typing import List, Tuple, Optional, Callable
import os
import time
import json
import math
from qgis.core import QgsTask, QgsMessageLog, QgsApplication, Qgis
import requests
from ..borg import Borg
from ..util import MULTIPART_CHUNK_SIZE


class UploadMultiPartFileTask(QgsTask):
    def __init__(self, file_path: str, urls: List[str], ext_prog_callback: Callable[[int], None] = None, retries=5):
        super().__init__(f"Upload {file_path}", QgsTask.CanCancel)
        self.file_path = file_path
        self.ext_prog_callback = ext_prog_callback
        self.urls = urls
        self.uploaded_size = 0
        self.allowed_retries = retries
        self.retry_count = 0
        self.total_size = os.path.getsize(file_path)
        self.chunk_size = MULTIPART_CHUNK_SIZE
        self.chunks = math.ceil(self.total_size / self.chunk_size)
        self.error = None

    def debug_log(self) -> str:
        debug_obj = {
            'urls': self.urls,
            'uploaded_size': self.uploaded_size,
            'total_size': self.total_size,
            'chunk_size': self.chunk_size,
            'chunks': self.chunks,
            'retry_count': self.retry_count,
            'allowed_retries': self.allowed_retries,
            'errors': str(self.error),
        }
        json_str = json.dumps(debug_obj, indent=4, sort_keys=True)
        # Replace all \n line breaks with a newline character
        json_str = json_str.replace('\\n', '\n                ')
        return json_str

    def _progress_callback(self, uploaded: int):
        self.uploaded_size += uploaded
        if self.ext_prog_callback:
            self.ext_prog_callback()

    def upload_file_part(self, url: str, start: int, end: int) -> bool:
        original_size = self.uploaded_size
        for _ in range(self.allowed_retries):
            try:
                with open(self.file_path, 'rb') as file:
                    file.seek(start)
                    part = file.read(end - start)
                    print(f"      Uploading chunk {start}-{end} to {url}")
                    response = requests.put(url, data=part)
                    response.raise_for_status()
                    self.uploaded_size += len(part)
                    if self.ext_prog_callback:
                        self.ext_prog_callback()
                    return True
            except Exception as e:
                self.uploaded_size = original_size
                self.error = f"Error while uploading chunk {start}-{end} to {url}: {str(e)}"
                self.retry_count += 1
                time.sleep(1)  # Wait for a second before retrying
        return False

    def run(self):
        if self.chunks != len(self.urls):
            self.error = f"Number of URLs ({len(self.urls)}) does not match number of chunks ({self.chunks})"
            return False
        for idx, url in enumerate(self.urls):
            print(f"--------START: Uploading chunk {idx + 1} of {self.chunks}")
            start = idx * self.chunk_size
            end = (idx + 1) * self.chunk_size if idx < len(self.urls) - 1 else self.total_size
            if not self.upload_file_part(url, start, end):
                return False  # Stop if the upload fails
            print(f"---------DONE: Uploaded chunk {idx + 1} of {self.chunks}")
        return True


class UploadQueue(Borg):
    """ _summary_

    Args:
        Borg (_type_): _description_

    Returns:
        _type_: _description_
    """

    MAX_CONCURRENT_UPLOADS = 4

    def __init__(self, log_callback=None, complete_callback=None, progress_callback=None):
        self.active = True
        self.log_callback = log_callback
        self.complete_callback = complete_callback
        self.progress_callback = progress_callback

        self.queue: List[UploadMultiPartFileTask] = []
        self.active_tasks: List[UploadMultiPartFileTask] = []
        self.completed_tasks: List[UploadMultiPartFileTask] = []
        self.cancelled_tasks: List[UploadMultiPartFileTask] = []

    def queue_logger(self, message: str, level: int, context_obj=None):
        if self.log_callback:
            self.log_callback(message, Qgis.Info, context_obj)

    def enqueue(self, file_path, upload_urls: List[str], retries=5):
        """ Push a file onto the queue for upload

        Args:
            file_path (_type_): _description_
            upload_url (_type_): _description_
            retries (int, optional): _description_. Defaults to 5.
        """
        task = UploadMultiPartFileTask(file_path, upload_urls, self.get_overall_status, retries)
        self.queue_logger(f"Enqueued {file_path} for upload", Qgis.Info)
        # Hook into the task's finished signal
        task.taskCompleted.connect(lambda: self.task_finished(task))
        task.taskTerminated.connect(lambda: self.task_finished(task))

        self.queue.append(task)
        self.active = True
        self.process_queue()

    def get_overall_status(self) -> Tuple[float, UploadMultiPartFileTask]:
        """
        Returns the overall status of the queue
        Status is the percent of the total bytes sent
        """
        total_size = 0
        uploaded_size = 0

        # First add all the tasks in the queue. These are all assumed to be 0% uplaoded
        for task in self.queue:
            total_size += task.total_size

        for task in self.completed_tasks:
            total_size += task.total_size
            uploaded_size += task.total_size

        # Now add all the active tasks
        for task in self.active_tasks:
            total_size += task.total_size
            uploaded_size += task.uploaded_size

        big_task = self.get_biggest_active_task()
        progress = int((uploaded_size / total_size) * 100)

        if self.progress_callback:
            self.progress_callback(big_task, progress)

        # Also return the values in case we're calling it directly
        return (progress, big_task)

    def get_biggest_active_task(self):
        """ Pull task with the biggest file size off the stack and return it

        Returns:
            _type_: _description_
        """
        if self.active_tasks and self.active_tasks[0].total_size > 0:
            return self.active_tasks[0]
        else:
            return None

    def process_queue(self):
        """ _summary_
        """
        while self.active is True and len(self.active_tasks) < self.MAX_CONCURRENT_UPLOADS:
            # There are things to queue and slots open
            if len(self.queue) > 0:
                task = self.queue.pop(0)
                self.queue_logger(f"Starting upload of {task.file_path}", Qgis.Info)
                self.active_tasks.append(task)
                QgsApplication.taskManager().addTask(task)

            # If the queue is empty and there are no active tasks, we're done
            elif len(self.queue) == 0 and len(self.active_tasks) == 0:
                self.queue_logger(f"Queue is empty, stopping", Qgis.Info)
                self.active = False
                if self.complete_callback:
                    self.complete_callback()
            else:
                # There are some active tasks but the queue is empty
                # Nothing to do but wait until the next task finishes and this function is called again
                break

    def task_finished(self, task):
        """ _summary_

        Args:
            task (_type_): _description_
        """
        if task.error:
            self.queue_logger(f"Error uploading {task.file_path}: {task.error}", Qgis.Critical, task)
        else:
            self.queue_logger(f"Finished uploading: {task.file_path}", Qgis.Info)
        self.active_tasks.remove(task)
        self.completed_tasks.append(task)
        self.process_queue()

    def cancel_all(self):
        """ _summary_
        """
        self.queue_logger(f"Canceling all uploads", Qgis.Info)
        self.active = False
        for task in self.active_tasks:
            task.cancel()
            self.queue_logger(f"Cancelled upload of {task.file_path}", Qgis.Info, task)
            self.active_tasks.remove(task)
            self.cancelled_tasks.append(task)
            if self.complete_callback:
                self.complete_callback()
