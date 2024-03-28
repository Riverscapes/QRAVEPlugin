from typing import List, Tuple
import os
from qgis.core import QgsTask, QgsMessageLog, QgsApplication, Qgis
import requests
import time
from ..borg import Borg


class UploadTask(QgsTask):
    """ _summary_

    Args:
        QgsTask (_type_): _description_
    """

    def __init__(self, file_path: str, upload_url: str, retries=5):
        super().__init__('UploadTask')
        self.file_path = file_path
        self.retries = retries
        self.current_attempt = 0
        self.upload_url = upload_url
        self.total_size = os.path.getsize(file_path)
        self.uploaded_size = 0

    def progress_callback(self, monitor):
        """ We stream the file to the server and update the progress bar

        Args:
            monitor (_type_): _description_
        """
        self.uploaded_size += monitor.len
        self.setProgress((self.uploaded_size / self.total_size) * 100)

    def run(self):
        try:
            with open(self.file_path, 'rb') as file:
                encoded_file = (b'--myboundary\r\nContent-Disposition: form-data; name="file"; filename="file"\r\nContent-Type: application/octet-stream\r\n\r\n' + file.read() + b'\r\n--myboundary--\r\n')
                response = requests.post(self.upload_url, data=encoded_file, headers={'Content-Type': 'multipart/form-data; boundary=myboundary', 'Cache-Control': 'no-cache'})
                if response.status_code == 200:
                    return True, None
                else:
                    QgsMessageLog.logMessage(f"Upload failed for {self.file_path}, status code: {response.status_code}", level=Qgis.Warning)
                    return False, response.text
        except Exception as e:
            QgsMessageLog.logMessage(f"Upload failed for {self.file_path}, error: {str(e)}", level=Qgis.Critical)
            return False, str(e)


class UploadQueue(Borg):
    """ _summary_

    Args:
        Borg (_type_): _description_

    Returns:
        _type_: _description_
    """

    MAX_CONCURRENT_UPLOADS = 4

    def __init__(self):
        self.active = False

        self.queue: List[UploadTask] = []
        self.active_tasks: List[UploadTask] = []
        self.completed_tasks: List[UploadTask] = []
        self.cancelled_tasks: List[UploadTask] = []

    def enqueue(self, file_path, upload_url, retries=5):
        """ _summary_

        Args:
            file_path (_type_): _description_
            upload_url (_type_): _description_
            retries (int, optional): _description_. Defaults to 5.
        """
        task = UploadTask(file_path, upload_url, retries)
        # Hook into the task's finished signal
        task.finished.connect(self.task_finished)

        self.queue.append(task)
        self.process_queue()

    def get_overall_status(self) -> Tuple[float, UploadTask]:
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

        big_task = self.get_biggest_task()

        return ((uploaded_size / total_size) * 100, big_task)

    def get_biggest_task(self):
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
        while self.active is True \
                and len(self.active_tasks) < self.MAX_CONCURRENT_UPLOADS \
                and len(self.queue) > 0:

            task = self.queue.pop(0)
            QgsApplication.taskManager().addTask(task)
            self.active_tasks.append(task)

    def task_finished(self, task):
        """ _summary_

        Args:
            task (_type_): _description_
        """
        self.active_tasks.remove(task)
        self.completed_tasks.append(task)

    def cancel_all(self):
        """ _summary_
        """
        self.active = False
        for task in self.active_tasks:
            task.cancel()
            self.active_tasks.remove(task)
            self.cancelled_tasks.append(task)


if __name__ == '__main__':

    # Usage example:
    upload_queue = UploadQueue()

    # Suppose you have a list of file paths to upload
    file_paths = [...]  # List of file paths

    # Enqueue files for upload
    for file_path in file_paths:
        upload_queue.enqueue(file_path, file_path, retries=5)
