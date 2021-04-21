# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QRAVE
                                 A QGIS plugin
 Explore symbolized Riverscapes projects
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-04-13
        git sha              : $Format:%H$
        copyright            : (C) 2021 by North Arrow Research
        email                : info@northarrowresearch.com
 ***************************************************************************/
"""
import os.path
from time import time
from functools import partial
from qgis.utils import showPluginHelp
from qgis.core import QgsTask, QgsApplication

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QUrl, pyqtSlot
from qgis.PyQt.QtGui import QIcon, QDesktopServices
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QToolButton, QMenu, QDialogButtonBox

from .classes.settings import Settings, CONSTANTS
from .classes.net_sync import NetSync
from .classes.async_worker import QAsync
from .classes.basemaps import BaseMaps
from .classes.project import Project


# Initialize Qt resources from file resources.py
# Import the code for the dialog
from .options_dialog import OptionsDialog
from .progress_dialog import ProgressDialog
from .about_dialog import AboutDialog
from .dock_widget import QRAVEDockWidget
from .meta_widget import QRAVEMetaWidget

# initialize Qt resources from file resources.py
from . import resources


class QRAVE:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.tm = QgsApplication.taskManager()
        self.pluginIsActive = False

        self.dockwidget = None
        self.metawidget = None

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'QRAVE_{}.qm'.format(locale))
        self.settings = Settings()

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Riverscapes Plugin (QRAVE)')

        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'QRAVE')
        self.toolbar.setObjectName(u'QRAVE')

    # noinspection PyMethodMayBeStatic

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('QRAVE', message)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        self.openAction = QAction(QIcon(':/plugins/qrave_toolbar/RaveAddIn_16px.png'), self.tr(u'Riverscapes Plugin (QRAVE)'), self.iface.mainWindow())
        self.openAction.triggered.connect(self.toggle_widget)

        self.openAction.setStatusTip('do a thing')
        self.openAction.setWhatsThis('what\'s this')

        self.openProjectAction = QAction(QIcon(':/plugins/qrave_toolbar/OpenProject.png'), self.tr(u'Open Riverscapes Project'), self.iface.mainWindow())
        self.openProjectAction.triggered.connect(self.projectBrowserDlg)

        self.openProjectAction.setStatusTip('do a thing')
        self.openProjectAction.setWhatsThis('what\'s this')

        self.helpButton = QToolButton()
        self.helpButton.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.helpButton.setMenu(QMenu())
        self.helpButton.setPopupMode(QToolButton.MenuButtonPopup)

        m = self.helpButton.menu()

        def openUrl():
            QDesktopServices.openUrl(QUrl("http://rave.riverscapes.xyz"))

        self.helpAction = QAction(
            QIcon(':/plugins/qrave_toolbar/Help.png'),
            self.tr('Help'),
            self.iface.mainWindow()
        )
        self.helpAction.triggered.connect(partial(showPluginHelp, None, filename=':/plugins/qrave_toolbar/help/build/html/index'))
        self.websiteAction = QAction(
            QIcon(':/plugins/qrave_toolbar/RaveAddIn_16px.png'),
            self.tr('Website'),
            self.iface.mainWindow()
        )
        self.websiteAction.triggered.connect(openUrl)

        self.raveOptionsAction = QAction(
            self.tr('Settings'),
            self.iface.mainWindow()
        )
        self.raveOptionsAction.triggered.connect(self.optionsLoad)

        self.net_sync_action = QAction(
            QIcon(':/plugins/qrave_toolbar/refresh.png'),
            self.tr('Update resources'),
            self.iface.mainWindow()
        )
        self.net_sync_action.triggered.connect(lambda: self.net_sync_load(force=True))

        self.about_action = QAction(
            QIcon(':/plugins/qrave_toolbar/RaveAddIn_16px.png'),
            self.tr('About QRAVE'),
            self.iface.mainWindow()
        )
        self.about_action.triggered.connect(self.about_load)

        m.addAction(self.helpAction)
        m.addAction(self.websiteAction)
        m.addAction(self.raveOptionsAction)
        m.addAction(self.net_sync_action)
        m.addSeparator()
        m.addAction(self.about_action)
        self.helpButton.setDefaultAction(self.helpAction)

        self.toolbar.addAction(self.openAction)
        self.toolbar.addAction(self.openProjectAction)
        self.toolbar.addWidget(self.helpButton)

        self.reloadGui()

    def reloadGui(self):
        plugin_init = self.settings.getValue('initialized')
        self.openAction.setEnabled(plugin_init)
        self.openProjectAction.setEnabled(plugin_init)

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        # print "** CLOSING QRAVE DockWidget"

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Riverscapes Plugin (QRAVE)'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def projectBrowserDlg(self):
        """
        Browse for a project directory
        :return:
        """
        last_project = self.settings.getValue('projectPath')
        last_dir = os.path.dirname(last_project) if last_project is not None else None

        dialog_return = QFileDialog.getOpenFileName(self.dockwidget, "Open a Riverscapes project", last_dir, self.tr("Riverscapes Project files (project.rs.xml)"))
        if dialog_return is not None and dialog_return[0] != "" and os.path.isfile(dialog_return[0]):
            self.settings.setValue('projectPath', dialog_return[0])
            self.reload_tree()

    def optionsLoad(self):
        """
        Open the options/settings dialog
        """
        dialog = OptionsDialog()
        if self.dockwidget:
            dialog.dataChange.connect(self.dockwidget.load)
        dialog.exec_()

    def about_load(self):
        """
        Open the About dialog
        """
        dialog = AboutDialog()
        dialog.exec_()

    def net_sync_load(self, force=False):
        """
        Periodically check for new files
        """

        lastDigestSync = self.settings.getValue('lastDigestSync')
        currTime = int(time())  # timestamp in seconds
        plugin_init = self.settings.getValue('initialized')

        if force is True:
            dialog = ProgressDialog()
            dialog.setWindowTitle('QRAVE Updater')
            netsync = NetSync(labelcb=dialog.progressLabel.setText, progresscb=dialog.progressBar.setValue, finishedcb=self.reload_tree)

            # No sync necessary in some cases
            if plugin_init \
                    and not netsync.need_sync \
                    and not force \
                    and isinstance(lastDigestSync, int) \
                    and ((currTime - lastDigestSync) / 3600) < CONSTANTS['digestSyncFreqHours']:
                return

            ns_task = QgsTask.fromFunction('QRAVE Sync', netsync.run,
                                           on_finished=netsync.completed)
            self.tm.addTask(ns_task)

            dialog.exec_()
        else:
            netsync = NetSync(finishedcb=self.reload_tree)

            # No sync necessary in some cases
            if plugin_init \
                    and not netsync.need_sync \
                    and not force \
                    and isinstance(lastDigestSync, int) \
                    and ((currTime - lastDigestSync) / 3600) < CONSTANTS['digestSyncFreqHours']:
                return

            ns_task = QgsTask.fromFunction('QRAVE Sync', netsync.run,
                                           on_finished=netsync.completed)
            self.tm.addTask(ns_task)

    def reload_tree(self):
        """
        The dockwidget may or may not be initialized when we call reload so we
        add a checking step in
        """

        if self.dockwidget:
            self.dockwidget.dataChange.emit()
        self.reloadGui()

    def toggle_widget(self, forceOn=False):
        """Toggle the widget open and closed when clicking the toolbar"""
        if not self.pluginIsActive:
            self.pluginIsActive = True

            # print "** STARTING QRAVE"

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget is None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = QRAVEDockWidget()
                self.metawidget = QRAVEMetaWidget()
                # Hook metadata changes up to the metawidget
                self.dockwidget.metaChange.connect(self.metawidget.load)

                # Run a network sync operation to get the latest stuff. Don't force it.
                #  This is just a quick check
                self.net_sync_load()

            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.metawidget)
            self.dockwidget.show()

        else:
            if self.dockwidget is not None:
                if self.dockwidget.isHidden():
                    self.dockwidget.show()
                elif forceOn is False:
                    self.dockwidget.hide()

        # The metawidget always starts hidden
        if self.metawidget is not None:
            self.metawidget.hide()
