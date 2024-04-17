from typing import List, Tuple, Callable, Generator
import os
import time
import json
import math
from qgis.core import QgsTask, QgsApplication, Qgis
from PyQt5.QtCore import QObject, QByteArray, QUrl, QIODevice, QFile, QEventLoop, pyqtSlot, pyqtSignal
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from ..borg import Borg
from ..util import MULTIPART_CHUNK_SIZE

MAX_PROGRESS_INTERVAL = 1  # seconds


class PartialFile(QFile):

    def __init__(self, filepath: str, start: int, end: int, log_callback=None, progress_callback=None):
        super().__init__(filepath)
        self.log = log_callback
        self.progress_callback = progress_callback
        self.start = start
        self.end = end
        self.current_pos = start
        self.part_size = end - start

    def open(self, mode: QIODevice.OpenMode) -> bool:
        fileopen = super().open(mode)
        self.seek(self.start)
        return fileopen

    def close(self) -> None:
        return super().close()

    def readData(self, maxlen) -> bytes:
        actual_len = maxlen

        if self.current_pos + maxlen > self.end:
            actual_len = self.end - self.current_pos

        if actual_len <= 0:
            return QByteArray()

        self.current_pos += actual_len
        self.progress_callback(actual_len)
        return super().readData(actual_len)  # Call read method of superclass


class UploadMultiPartFileTask(QgsTask):
    cancelled = pyqtSignal()

    def __init__(self, file_path: str, urls: List[str], ext_prog_callback: Callable[[int], None] = None, log_callback: Callable[[int], None] = None, retries=5):
        super().__init__(f"Upload {file_path}", QgsTask.CanCancel)
        self.file_path = file_path
        self.log = log_callback
        self.ext_prog_callback = ext_prog_callback
        self.urls = urls
        self.uploaded_size = 0
        self.allowed_retries = retries
        self.retry_count = 0
        self.nam = QNetworkAccessManager()
        self.total_size = os.path.getsize(file_path)
        self.chunk_size = MULTIPART_CHUNK_SIZE
        self.chunks = math.ceil(self.total_size / self.chunk_size)
        self.error = None

    def cancel(self) -> None:
        """Implements a really simple cancel method that just emits a signal when the task is cancelled
        """
        self.log(f"      Cancelling task: {self.description()}", Qgis.Info)
        super().cancel()
        self.cancelled.emit()

    def debug_log(self) -> str:
        """ Useful helper function for printing task state to a log file

        Returns:
            str: _description_
        """
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

    def _progress_callback(self, bytesSent: int):
        """ When we get a progress update from the task, we update the total uploaded size
        """
        # self.log(f"      Progress callback: {bytesSent} of {self.file_path}", Qgis.Info)
        self.uploaded_size += bytesSent
        if self.ext_prog_callback:
            self.ext_prog_callback()

    def upload_file_part(self, url: str, start: int, end: int) -> bool:
        """ This is the actual upload code that will physically send all or part of a local file to a single remote URL

        Args:
            url (str): _description_
            start (int): 0 for single file or the first chunk of a multipart upload
            end (int): The last byte of the chunk to upload. End of file for single file or the last byte of the chunk for multipart

        Returns:
            bool: _description_
        """

        # Keep track of the original size before upload so we can reset if the upload fails
        original_size = self.uploaded_size

        for _ in range(self.allowed_retries):
            try:
                loop = QEventLoop()
                part_size = end - start
                # only want the first 100 characters of the url
                self.log(f"      Uploading chunk {start}-{end} for file: {self.file_path} Retry: {self.retry_count} to url: {url[:200]}", Qgis.Info)

                request = QNetworkRequest(QUrl(url))
                request.setHeader(QNetworkRequest.ContentLengthHeader, part_size)

                partial_file = PartialFile(self.file_path, start, end, self.log, self._progress_callback)
                seq = partial_file.isSequential()
                partial_file.open(QIODevice.ReadOnly)

                # Start the actual Call
                self.reply = self.nam.put(request, partial_file)

                def handle_cancelled():
                    self.log(f"        Task was cancelled, aborting upload of chunk {start}-{end} for file: {self.file_path}", Qgis.Warning)
                    self.reply.abort()
                    partial_file.close()
                    loop.quit()

                # Handle the network request completion
                def handle_done():
                    if self.reply.error() != QNetworkReply.NoError:
                        self.error = self.reply.errorString()
                        raise Exception(f"Error uploading chunk {start}-{end} to {url}: {self.reply.errorString()}")

                    # print the response
                    self.log(f"        Response: {self.reply.readAll().data().decode()}")
                    self.log(f"        Finished uploading chunk {start}-{end} for file: {self.file_path}", Qgis.Info)
                    self.log
                    self.reply.close()
                    partial_file.close()
                    loop.quit()

                # If the task is cancelled, abort the upload
                self.cancelled.connect(handle_cancelled)
                self.reply.finished.connect(handle_done)

                # Wait for the upload to complete or for the task to be cancelled
                self.log(f"     ######### LOOP: Waiting.....", Qgis.Info)
                # Hooke the loop to the reply
                loop.exec_()
                self.log(f"     ######### LOOP: Waiting Done!!.", Qgis.Info)

                # Return false on failure
                if self.error:
                    self.uploaded_size = original_size
                    self.log(f"      Error uploading chunk {start}-{end} to {url}: {self.error}", Qgis.Info)
                    # Reset the error and the next retry will try again

                self.log(f"      Uploaded chunk {start}-{end}", Qgis.Info)
                return True
            except Exception as e:
                self.uploaded_size = original_size
                self.error = f"Error while uploading chunk {start}-{end} to {url}: {str(e)}"
                self.log(f"      {self.error}", Qgis.Info)
                self.retry_count += 1
                time.sleep(1)  # Wait for a second before retrying

        return False

    def run(self):
        """ Implements the QgsTask run method. This is where the actual work is done

        Returns:
            _type_: _description_
        """

        # Quick check to make sure our chunk math is right
        if self.chunks != len(self.urls):
            self.error = f"Number of URLs ({len(self.urls)}) does not match number of chunks ({self.chunks})"
            return False

        # For each URL (1 for single file, many for multipart) upload the chunk
        for idx, url in enumerate(self.urls):
            self.log(f"--------START: Uploading chunk {idx + 1} of {self.chunks}", Qgis.Info)
            start = idx * self.chunk_size
            end = (idx + 1) * self.chunk_size if idx < len(self.urls) - 1 else self.total_size
            if not self.upload_file_part(url, start, end):
                return False  # Stop if the upload fails
            self.log(f"---------DONE: Uploaded chunk {idx + 1} of {self.chunks}", Qgis.Info)
        return True


class UploadQueue(QObject):
    """ _summary_

    Args:
        Borg(_type_): _description_

    Returns:
        _type_: _description_
    """
    progress_signal = pyqtSignal(str, int)
    complete_signal = pyqtSignal()

    MAX_CONCURRENT_UPLOADS = 4

    def __init__(self, log_callback=None, complete_callback=None):
        super().__init__()
        self.log_callback = log_callback
        # datetime of last progress update
        self.active = True
        self.last_progress = None

        self.queue: List[UploadMultiPartFileTask] = []
        self.active_tasks: List[UploadMultiPartFileTask] = []
        self.completed_tasks: List[UploadMultiPartFileTask] = []
        self.cancelled_tasks: List[UploadMultiPartFileTask] = []

    def clear(self):
        self.queue = []
        self.active_tasks = []
        self.completed_tasks = []
        self.cancelled_tasks = []
        self.last_progress = None
        self.active = True

    def queue_logger(self, message: str, level: int, context_obj=None):
        if self.log_callback:
            self.log_callback('UploadQueue: ' + message, Qgis.Info, context_obj)

    def enqueue(self, file_path, upload_urls: List[str], retries=5):
        """ Push a file onto the queue for upload

        Args:
            file_path(_type_): _description_
            upload_url(_type_): _description_
            retries(int, optional): _description_. Defaults to 5.
        """
        self.queue_logger(f"Enqueued {file_path} for upload", Qgis.Info)
        # Hook into the task's finished signal
        task = UploadMultiPartFileTask(file_path, upload_urls, self.get_overall_status, self.log_callback, retries)
        task.taskCompleted.connect(lambda: self.task_finished(task))
        task.taskTerminated.connect(lambda: self.task_finished(task))

        self.queue.append(task)
        self.active = True
        self.process_queue()

    def get_overall_status(self, force=False) -> Tuple[float, UploadMultiPartFileTask]:
        """
        Returns the overall status of the queue
        Status is the percent of the total bytes sent
        """
        if not force and self.last_progress is not None and (time.time() - self.last_progress) < MAX_PROGRESS_INTERVAL:
            return
        self.last_progress = time.time()

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

        self.progress_signal.emit(big_task.file_path, progress)

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
        """ Here we process the queue and start tasks as slots become available
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
                self.complete_signal.emit()
            else:
                # There are some active tasks but the queue is empty
                # Nothing to do but wait until the next task finishes and this function is called again
                break

    def task_finished(self, task):
        """ When a single task finishes we need to clean up and process the queue

        Args:
            task(_type_): _description_
        """
        if task.error:
            self.queue_logger(f"Error uploading {task.file_path}: {task.error}", Qgis.Critical, task)
        else:
            self.queue_logger(f"Finished uploading: {task.file_path}", Qgis.Info)
        # Put it on the correct list
        self.active_tasks.remove(task)
        self.completed_tasks.append(task)
        # Kick off queue processing again
        self.process_queue()

    def cancel_all(self):
        """ _summary_
        """
        self.queue_logger(f"Canceling all {len(self.active_tasks)} uploads", Qgis.Info)
        # Shut down the queue processor
        self.active = False

        # Cancel all the active tasks
        for task in self.active_tasks:
            task.cancel()
            self.queue_logger(f"Cancelled upload of {task.file_path}", Qgis.Info, task)
            self.active_tasks.remove(task)
            self.cancelled_tasks.append(task)

        # Now signal that we're done
        self.queue_logger(f"Uploads cancelled", Qgis.Info)
        if self.complete_callback:
            self.complete_callback()
