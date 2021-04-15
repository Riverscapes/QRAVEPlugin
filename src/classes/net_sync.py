import traceback
import requests
import os
import json
import hashlib


from time import time
from queue import Queue
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtCore import QThread, QObject, pyqtSlot, pyqtSignal
from .settings import Settings, CONSTANTS


class QueueStatus():
    STARTED = 1
    STOPPED = 0


class NetSyncQueuesBorg(object):
    _shared_state = {}
    _initdone = False
    _alive = False

    def __init__(self):
        self.__dict__ = self._shared_state


class NetSyncQueues(NetSyncQueuesBorg):

    def __init__(self):
        NetSyncQueuesBorg.__init__(self)
        self.settings = Settings()

        if not self._initdone:
            print("Init NetSyncQueues")
            self.load_q = Queue()

            # These are the thread processes that run the downloading processes
            self.worker = NetSyncQueues.Worker()
            self.worker_thread = QThread()
            self.worker_thread.start()

            self.worker.moveToThread(self.worker_thread)
            self.worker.start.connect(self.worker.run)

            self.killrequested = False
            # Must be the last thing we do in init
            self._initdone = True

    def queuePush(self, item):
        self.load_q.put(item)
        self.startWorker()

    def startWorker(self):
        # print "Attempting TreeLoadQueues Start:"
        if not self._alive:
            self.worker.killrequested = False
            self.worker.start.emit("start")

    def stopWorker(self):
        print("Attempting NetSyncQueues Stop:")
        self.worker.killrequested = True

    def resetQueue(self):
        if self.worker_thread.isRunning():
            self.worker_thread.terminate()
            self.worker_thread.wait()
            self.worker_thread.start()

    # http://stackoverflow.com/questions/16879971/example-of-the-right-way-to-use-qthread-in-pyqt
    class Worker(QObject):

        killrequested = False

        def __init__(self):
            super(NetSyncQueues.Worker, self).__init__()
            self.currentProject = None

        start = pyqtSignal(str)
        error = pyqtSignal(object)

        @pyqtSlot()
        def run(self):
            # Gives us breakpoints in a thread but only if we are in debug mode
            # Note that we're not subclassing QThread as per:
            # http://stackoverflow.com/questions/20324804/how-to-use-qthread-correctly-in-pyqt-with-movetothread
            Qs = NetSyncQueues()
            try:
                while not self.killrequested and Qs.load_q.qsize() > 0:
                    Qs._alive = True
                    if Qs.load_q.qsize() > 0:
                        thePartial = Qs.load_q.get()
                        thePartial()
                Qs._alive = False
            except Exception as e:
                Qs.stopWorker()
                Qs.load_q.empty()
                print("TransferWorkerThread Exception: {}".format(str(e)))
                traceback.print_exc()
                self.error.emit((e, traceback.format_exc()))


class NetSync:

    def __init__(self):
        self.q = NetSyncQueues()
        self.settings = Settings()

        self.resource_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'resources')
        self.symbology_dir = os.path.join(self.resource_dir, 'symbology')
        self.business_logic_xml_dir = os.path.join(self.resource_dir, 'blXML')
        self.digest_path = os.path.join(self.resource_dir, 'index.json')

        self.initialize()
        self.updateDigest()

    def initialize(self):
        if not os.path.isdir(self.resource_dir):
            os.mkdir(self.resource_dir)
        if not os.path.isdir(self.symbology_dir):
            os.mkdir(self.symbology_dir)
        if not os.path.isdir(self.business_logic_xml_dir):
            os.mkdir(self.business_logic_xml_dir)

    def updateDigest(self):

        # Now get the JSON file
        json_url = CONSTANTS['resourcesUrl'] + 'index.json'
        try:
            resp = requests.get(url=json_url, timeout=15)
            content_type = resp.headers.get('content-type')
            open(self.digest_path, 'wb').write(resp.content)
            self.settings.setValue('lastDigestSync', int(time()))

        except requests.exceptions.Timeout:
            QgsMessageLog.logMessage("Fetching digest timed out", 'QRAVE', level=Qgis.Error)
            return
            # Maybe set up for a retry, or continue in a retry loop
        except requests.exceptions.TooManyRedirects:
            # Tell the user their URL was bad and try a different one
            QgsMessageLog.logMessage("Fetching digest failed with too many redirects", 'QRAVE', level=Qgis.Error)
            return
        except requests.exceptions.RequestException as e:
            # catastrophic error. bail.
            raise SystemExit(e)

    def syncFiles(self):
        digest = {}
        if not os.path.isfile(self.digest_path):
            QgsMessageLog.logMessage("Digest file could not be found", 'QRAVE', level=Qgis.Error)
            return

        with open(self.digest_path) as fl:
            digest = json.load(fl)

        symbologies = {x: v for x, v in digest.items() if x.startswith('Symbology/qgis') and x.endswith('.qml')}
        symbologies = {x: v for x, v in digest.items() if x.startswith('RaveBusinessLogic') and x.endswith('.xml')}


def md5(fname: str) -> str:
    try:
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(e)
        return None
