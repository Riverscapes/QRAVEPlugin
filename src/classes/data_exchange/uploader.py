from typing import List, Tuple, Callable, Generator
import os
import time
import json
import math
from qgis.core import QgsTask, QgsApplication, Qgis
from PyQt5.QtCore import QByteArray, QUrl, QIODevice, QFile, QEventLoop, pyqtSlot, pyqtSignal
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import requests
from ..borg import Borg
from ..util import MULTIPART_CHUNK_SIZE

MAX_PROGRESS_INTERVAL = 1  # seconds
UPLOAD_PROGESS_CHUNK_SIZE = 1024


class PartialFile(QIODevice):
    def __init__(self, filepath: str, start: int, end: int, log_callback=None):
        super().__init__()
        self.filepath = filepath
        self.file = QFile(filepath)
        self.log = log_callback
        self.start = start
        self.end = end
        self.current_pos = start

    def open(self, mode: QIODevice.OpenMode) -> bool:
        fileopen = self.file.open(mode)
        partial_open = super().open(mode)
        self.log(f"                         PartialFile: Opening and seeking to ({self.current_pos}) fileopen: {fileopen} partial_open: {partial_open}", Qgis.Info)
        return partial_open

    def close(self) -> None:
        self.log(f"                         PartialFile: Closing", Qgis.Info)
        closed = super().close()
        self.file.close()
        return closed

    def read(self, maxlen: int) -> bytes:
        self.log(f"                         PartialFile: Reading(read) {maxlen}", Qgis.Info)
        return self.readData(maxlen)

    def readyRead(self) -> None:
        self.log(f"                         PartialFile: Reading(readyRead)", Qgis.Info)
        return super().readyRead()

    def readData(self, maxlen):
        self.log(f"                         PartialFile: Reading(readData) {maxlen}", Qgis.Info)
        self.file.seek(self.current_pos)
        if self.current_pos + maxlen > self.end:
            maxlen = self.end - self.current_pos
        data = self.file.read(maxlen)
        self.current_pos += len(data)
        self.log(f"                         PartialFile: Read {len(data)} bytes from {self.current_pos} of {self.end}")
        return data

    def isSequential(self):
        return False


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

    @pyqtSlot()
    def _progress_callback(self, bytesSent: int = 0, bytesTotal: int = 0):
        """ When we get a progress update from the task, we update the total uploaded size
        """
        self.log(f"      Progress callback: {bytesSent} of {bytesTotal}", Qgis.Info)
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
        original_size = self.uploaded_size

        for _ in range(self.allowed_retries):
            try:
                loop = QEventLoop()
                part_size = end - start
                self.log(f"      Uploading chunk {start}-{end} for file: {self.file_path} Retry: {self.retry_count} to url: {url}", Qgis.Info)

                request = QNetworkRequest(QUrl(url))
                request.setHeader(QNetworkRequest.ContentLengthHeader, part_size)

                partial_file = PartialFile(self.file_path, start, end, self.log)
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
                        self.log(f"        Error uploading chunk {start}-{end} to {url}: {self.reply.errorString()}", Qgis.Critical)
                        self.error = self.reply.errorString()

                    # print the response
                    self.log(f"        Response: {self.reply.readAll().data().decode()}")
                    self.log(f"        Finished uploading chunk {start}-{end} for file: {self.file_path}", Qgis.Info)
                    self.log
                    self.reply.close()
                    partial_file.close()
                    loop.quit()

                # Connect the readyRead signal to read chunks of data and write to the network reply
                # self.reply.readyRead.connect(stream_file_chunk)

                self.reply.uploadProgress.connect(self._progress_callback)
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


class UploadQueue(Borg):
    """ _summary_

    Args:
        Borg(_type_): _description_

    Returns:
        _type_: _description_
    """

    MAX_CONCURRENT_UPLOADS = 4

    def __init__(self, log_callback=None, complete_callback=None, progress_callback=None):
        self.active = True
        self.log_callback = log_callback
        self.complete_callback = complete_callback
        self.progress_callback = progress_callback
        # datetime of last progress update
        self.last_progress = None

        self.queue: List[UploadMultiPartFileTask] = []
        self.active_tasks: List[UploadMultiPartFileTask] = []
        self.completed_tasks: List[UploadMultiPartFileTask] = []
        self.cancelled_tasks: List[UploadMultiPartFileTask] = []

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
        self.queue_logger(f"""Overall status: {progress}%
                        queue: {len(self.queue)}
                        active_tasks: {len(self.active_tasks)}
                        completed_tasks: {len(self.completed_tasks)}
                        cancelled_tasks: {len(self.cancelled_tasks)}""", Qgis.Info)
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
                if self.complete_callback:
                    self.complete_callback()
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