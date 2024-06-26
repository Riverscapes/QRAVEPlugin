from typing import List, Tuple, Callable
import os
import time
import json
import math
from qgis.core import QgsTask, QgsApplication, Qgis
from PyQt5.QtCore import QObject, QByteArray, QUrl, QIODevice, QFile, QEventLoop, pyqtSlot, pyqtSignal
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
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

    def __init__(self, rel_path: str, abs_path: str, urls: List[str], ext_prog_callback: Callable[[int], None] = None, log_callback: Callable[[int], None] = None, retries=5):
        super().__init__(f"Upload {rel_path}", QgsTask.CanCancel)
        self.rel_path = rel_path
        self.file_path = abs_path
        self.log = log_callback
        self.ext_prog_callback = ext_prog_callback
        self.urls = urls
        self.uploaded_size = 0
        self.allowed_retries = retries
        self.retry_count = 0
        self.nam = QNetworkAccessManager()
        self.total_size = os.path.getsize(abs_path)
        self.chunk_size = MULTIPART_CHUNK_SIZE
        self.chunks = math.ceil(self.total_size / self.chunk_size)
        self.error = None

    def cancel(self) -> None:
        """Implements a really simple cancel method that just emits a signal when the task is cancelled
        """
        self.file_upload_log(f"Cancelling task: {self.description()}", Qgis.Info)
        super().cancel()
        self.cancelled.emit()

    def file_upload_log(self, message: str, level: int, context_obj=None):
        if self.log:
            log_str = 'UploadMultiPartFileTask: ' + message
            # indent everuything by 6 spaces
            spacer = ' ' * 6
            log_str = spacer + log_str.replace(os.linesep, '\n' + spacer)
            self.log(log_str, level, context_obj)

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
        json_str = json_str.replace(os.linesep, '\n                ')
        return json_str

    def _progress_callback(self, bytesSent: int):
        """ When we get a progress update from the task, we update the total uploaded size
        """
        # self.file_upload_log(f"      Progress callback: {bytesSent} of {self.file_path}", Qgis.Info)
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
            self.error = None
            try:
                loop = QEventLoop()
                part_size = end - start
                # Only the first 100 and last 50 characters of the URL need to be shown
                # url_str = url[:100] + '...'
                self.file_upload_log(f"Uploading chunk bytes {start:,} - {end:,} for file: {self.rel_path} Retry: {self.retry_count}", Qgis.Info)

                request = QNetworkRequest(QUrl(url))
                request.setHeader(QNetworkRequest.ContentLengthHeader, part_size)

                partial_file = PartialFile(self.file_path, start, end, self.file_upload_log, self._progress_callback)
                seq = partial_file.isSequential()
                partial_file.open(QIODevice.ReadOnly)

                # Start the actual Call
                self.reply = self.nam.put(request, partial_file)

                def handle_cancelled():
                    """Make sure we clean up and close file handles if the cancel signal has been called
                    """
                    # self.file_upload_log(f"WARNING: Task was cancelled, aborting upload of chunk {start:,} - {end:,} for file: {self.rel_path} Retry: {self.retry_count}", Qgis.Warning)
                    self.error = QNetworkReply.OperationCanceledError
                    self.reply.abort()
                    partial_file.close()

                # Handle the network request completion
                def handle_done():
                    # Detect if the reply was cancelled
                    if self.reply.error() == QNetworkReply.OperationCanceledError:
                        self.error = QNetworkReply.OperationCanceledError
                        # self.file_upload_log(f"WARNING: Upload cancelled for chunk {start:,} - {end:,} for file: {self.rel_path} Retry: {self.retry_count}", Qgis.Warning)
                        loop.quit()

                    elif self.reply.error() != QNetworkReply.NoError:
                        self.error = self.reply.errorString()
                        # Raising here will be caught below and cause a retry (hopefully)
                        raise Exception(f"Error uploading chunk {start}-{end} to {url}: {self.reply.errorString()}")
                    else:
                        # print the response
                        # self.file_upload_log(f"Response: {self.reply.readAll().data().decode()}")
                        # self.file_upload_log(f"Finished uploading chunk {start}-{end} for file: {self.rel_path}", Qgis.Info)
                        self.reply.close()
                        partial_file.close()
                        loop.quit()

                # If the task is cancelled, abort the upload
                self.cancelled.connect(handle_cancelled)
                self.reply.finished.connect(handle_done)

                # Wait for the upload to complete or for the task to be cancelled
                # self.file_upload_log(f"     ######### LOOP: Waiting.....", Qgis.Info)
                # Hooke the loop to the reply
                loop.exec_()
                # self.file_upload_log(f"     ######### LOOP: Waiting Done!!.", Qgis.Info)

                # Return false on failure
                if self.error == QNetworkReply.OperationCanceledError:
                    # Cancelled. Don't retry and don't continue
                    return False
                elif self.error:
                    self.uploaded_size = original_size
                    self.file_upload_log(f"ERROR: uploading chunk {start}-{end} to {url}: {self.error}", Qgis.Critical)
                    # Don't return here so we can retry
                else:
                    self.file_upload_log(f"SUCCESS: Finished uploading chunk {start:,}-{end:,}", Qgis.Info)
                    return True
            except Exception as e:
                self.uploaded_size = original_size
                self.error = f"Error while uploading chunk {start}-{end} to {url}: {str(e)}"
                self.file_upload_log(f"{self.error}", Qgis.Info)
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
            # self.file_upload_log(f"START: Uploading chunk {idx + 1}:{self.chunks} for file: {self.rel_path}", Qgis.Info)
            start = idx * self.chunk_size
            end = (idx + 1) * self.chunk_size if idx < len(self.urls) - 1 else self.total_size
            if not self.upload_file_part(url, start, end):
                return False  # Stop if the upload fails after retries (or is cancelled)
            # self.file_upload_log(f"DONE: Uploaded chunk {idx + 1}:{self.chunks} for file: {self.rel_path}", Qgis.Info)
        return True


class UploadQueue(QObject):
    """ _summary_

    Returns:
        _type_: _description_
    """
    progress_signal = pyqtSignal(str, int, int, int)
    complete_signal = pyqtSignal()
    cancelled_signal = pyqtSignal()

    MAX_CONCURRENT_UPLOADS = 4

    def __init__(self, log_callback=None):
        super().__init__()
        self.log_callback = log_callback
        # datetime of last progress update
        self.active = True
        self.last_progress = None
        self.cancelled = False

        self.queue: List[UploadMultiPartFileTask] = []
        self.active_tasks: List[UploadMultiPartFileTask] = []
        self.completed_tasks: List[UploadMultiPartFileTask] = []
        self.cancelled_tasks: List[UploadMultiPartFileTask] = []

    def reset(self):
        self.queue = []
        self.active_tasks = []
        self.completed_tasks = []
        self.cancelled_tasks = []
        self.last_progress = None
        self.cancelled = False
        self.active = True

    def queue_logger(self, message: str, level: int, context_obj=None):
        if self.log_callback:
            log_str = 'UploadQueue: ' + message
            # indent everuything by 4 spaces
            spacer = ' ' * 4
            log_str = spacer + log_str.replace(os.linesep, '\n' + spacer)
            self.log_callback(log_str, level, context_obj)

    def enqueue(self, rel_path, abs_path, upload_urls: List[str], retries=5):
        """ Push a file onto the queue for upload

        Args:
            rel_path(_type_): Relpath is used as an id of sorts here. Not for any other reason
            abs_path(_type_): _description_
            upload_url(_type_): _description_
            retries(int, optional): _description_. Defaults to 5.
        """
        self.queue_logger(f"Enqueued {rel_path} for upload", Qgis.Info)
        # Hook into the task's finished signal
        task = UploadMultiPartFileTask(rel_path, abs_path, upload_urls, self.get_overall_status, self.log_callback, retries)
        task.taskCompleted.connect(lambda: self.task_finished(task))
        task.taskTerminated.connect(lambda: self.task_finished(task))

        self.queue.append(task)
        self.active = True
        self.process_queue()

    def get_overall_status(self, force=False) -> Tuple[float, UploadMultiPartFileTask, int, int]:
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

        self.progress_signal.emit(big_task.rel_path if big_task else "...", progress, uploaded_size, total_size)

        return (progress, big_task, uploaded_size, total_size)

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
                self.queue_logger(f"Starting upload of {task.rel_path}", Qgis.Info)
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

    def task_finished(self, task: UploadMultiPartFileTask):
        """ When a single task finishes we need to clean up and process the queue

        Args:
            task(_type_): _description_
        """
        if task.error == QNetworkReply.OperationCanceledError:
            self.queue_logger(f"Cancelled upload of {task.rel_path}", Qgis.Warning)
        elif task.error:
            self.queue_logger(f"Error uploading {task.rel_path}: {task.error}", Qgis.Critical, task)
        else:
            self.queue_logger(f"Finished uploading: {task.rel_path}", Qgis.Info)
            # Put it on the correct list
            try:
                self.active_tasks.remove(task)
                self.completed_tasks.append(task)
            except Exception as e:
                print(f"Error removing task: {str(e)}")

        # Kick off queue processing again
        self.process_queue()

    def cancel_all(self):
        """ _summary_
        """
        self.queue_logger(f"Canceling all {len(self.active_tasks)} uploads", Qgis.Info)
        # Shut down the queue processor
        self.active = False
        self.cancelled = True

        # Drain the queue
        finished_tasks = 0
        tasks_need_cancel = 0

        # Now QLoop wait for all tasks to be finished
        loop = QEventLoop()

        def on_task_finished():
            nonlocal finished_tasks
            nonlocal tasks_need_cancel
            finished_tasks += 1
            self.queue_logger(f"Finished cancelling {finished_tasks} of {tasks_need_cancel} uploads", Qgis.Info)
            if finished_tasks == tasks_need_cancel:
                self.log_callback(f"ALl uploads cancelled", Qgis.Info)
                loop.quit()

        for task_list in [self.queue, self.active_tasks]:
            for task in task_list:
                if not task.isCanceled():
                    self.queue_logger(f"Cancelling upload of {task.rel_path}", Qgis.Info)
                    # We connect it to both signals just in case the task is already finished or finishes in the meantime
                    task.taskCompleted.connect(on_task_finished)
                    task.taskTerminated.connect(on_task_finished)
                    task.cancel()
                    tasks_need_cancel += 1

        loop.exec_()

        # Now signal that we're done
        self.queue_logger(f"Uploads cancelled", Qgis.Info)
        self.cancelled_signal.emit()
