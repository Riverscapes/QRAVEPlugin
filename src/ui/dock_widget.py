# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './src/ui/dock_widget.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_QRAVEDockWidgetBase(object):
    def setupUi(self, QRAVEDockWidgetBase):
        QRAVEDockWidgetBase.setObjectName("QRAVEDockWidgetBase")
        QRAVEDockWidgetBase.resize(555, 559)
        self.dockWidgetContents = QtWidgets.QWidget()
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setContentsMargins(0, 4, 0, 4)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.treeView = QtWidgets.QTreeView(self.dockWidgetContents)
        self.treeView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.treeView.setProperty("showDropIndicator", False)
        self.treeView.setAlternatingRowColors(False)
        self.treeView.setIndentation(15)
        self.treeView.setSortingEnabled(False)
        self.treeView.setHeaderHidden(True)
        self.treeView.setObjectName("treeView")
        self.verticalLayout.addWidget(self.treeView)
        QRAVEDockWidgetBase.setWidget(self.dockWidgetContents)

        self.retranslateUi(QRAVEDockWidgetBase)
        QtCore.QMetaObject.connectSlotsByName(QRAVEDockWidgetBase)

    def retranslateUi(self, QRAVEDockWidgetBase):
        _translate = QtCore.QCoreApplication.translate
        QRAVEDockWidgetBase.setWindowTitle(_translate("QRAVEDockWidgetBase", "Riverscapes Toolbar (QRAVE)"))
