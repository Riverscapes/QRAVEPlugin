from queue import Queue
from qgis.PyQt.QtCore import QThread, pyqtSignal, QObject, pyqtSlot
import traceback

# Snip...

# Step 1: Create a worker class


class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, cb, *args, **kwargs):
        QObject.__init__(self)
        self.cb = cb
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        """Long-running task."""
        self.cb(*self.args, **self.kwargs)
        self.finished.emit()


class QAsync():

    def __init__(self, cb, *args, **kwargs):
        # Step 2: Create a QThread object
        self.thread = QThread()
        # Step 3: Create a worker object
        self.worker = Worker(cb, *args, **kwargs)
        # Step 4: Move worker to the thread
        self.worker.moveToThread(self.thread)

    def run(self):
        # Step 5: Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # self.worker.progress.connect(self.reportProgress)

        # Step 6: Start the thread
        self.thread.start()
        # Final resets
        # self.longRunningBtn.setEnabled(False)
        # self.thread.finished.connect(
        #     lambda: self.longRunningBtn.setEnabled(True)
        # )
        # self.thread.finished.connect(
        #     lambda: self.stepLabel.setText("Long-Running Step: 0")
        # )
