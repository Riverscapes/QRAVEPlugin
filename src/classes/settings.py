import os
import json
import logging

from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsMessageLog, Qgis

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')) as cfg_file:
    cfg_json = json.load(cfg_file)

# We include these so that
_DEFAULTS = cfg_json['defaultSettings']
CONSTANTS = cfg_json['constants']

# BASE is the name we want to use inside the settings keys
BASE = "QRAVEToolbar"


class SettingsBorg(object):
    _shared_state = {}
    _initdone = False

    def __init__(self):
        self.__dict__ = self._shared_state


class Settings(SettingsBorg):
    """
    Read up on the Borg pattern if you don't already know it. Super useful
    """

    def __init__(self):
        SettingsBorg.__init__(self)
        if not self._initdone:
            QgsMessageLog.logMessage("Init Settings", 'QRAVE', level=Qgis.Info)
            s = QSettings()

            # Do a sanity check and reset anything that looks fishy
            s.beginGroup(BASE)
            for key in _DEFAULTS.keys():
                # self.setValue(key, _DEFAULTS[key])  # UNCOMMENT THIS FOR EMERGENCY RESET
                if key not in s.childKeys():
                    self.setValue(key, _DEFAULTS[key])

            # Remove any settings that aren't in the defaults. This way we don't get settings building
            # Up over time
            for key in s.childKeys():
                if key not in _DEFAULTS:
                    s.remove(key)

            s.endGroup()

            # Must be the last thing we do in init
            self._initdone = True

    def resetAllSettings(self):
        s = QSettings()
        for key in _DEFAULTS.keys():
            self.setValue(key, _DEFAULTS[key])
        # Remove any settings that aren't in the defaults. This way we don't get settings building
        # Up over time
        for key in s.childKeys():
            if key not in _DEFAULTS:
                s.remove(key)
        s.endGroup()

    def getValue(self, key):
        """
        Get one setting from the in-memory store and if not present then the settings file
        :return:
        """
        value = None
        s = QSettings()
        s.beginGroup(BASE)
        try:
            default = _DEFAULTS[key] if key in _DEFAULTS else None
            value = json.loads(s.value(key, default))['v']
        except Exception as e:
            print(e)
            value = None
        s.endGroup()
        return value

    def setValue(self, key, value):
        """
        Write or overwrite a setting. Update the in-memory store  at the same time
        :param name:
        :param settings:
        :return:
        """
        s = QSettings()
        s.beginGroup(BASE)
        # Set it in the file
        s.setValue(key, json.dumps({"v": value}))
        QgsMessageLog.logMessage("SETTINGS SET: {}={} of type '{}'".format(key, value, str(type(value))), 'QRAVE', level=Qgis.Info)
        s.endGroup()
