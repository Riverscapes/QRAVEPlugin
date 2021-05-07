# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './src/ui/meta_widget.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_QRAVEMetaWidgetBase(object):
    def setupUi(self, QRAVEMetaWidgetBase):
        QRAVEMetaWidgetBase.setObjectName("QRAVEMetaWidgetBase")
        QRAVEMetaWidgetBase.resize(555, 559)
        self.dockWidgetContents = QtWidgets.QWidget()
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setContentsMargins(0, 4, 0, 4)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.treeView = QtWidgets.QTreeView(self.dockWidgetContents)
        self.treeView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.treeView.setProperty("showDropIndicator", False)
        self.treeView.setAlternatingRowColors(True)
        self.treeView.setIndentation(0)
        self.treeView.setSortingEnabled(False)
        self.treeView.setHeaderHidden(False)
        self.treeView.setObjectName("treeView")
        self.verticalLayout.addWidget(self.treeView)
        QRAVEMetaWidgetBase.setWidget(self.dockWidgetContents)

        self.retranslateUi(QRAVEMetaWidgetBase)
        QtCore.QMetaObject.connectSlotsByName(QRAVEMetaWidgetBase)

    def retranslateUi(self, QRAVEMetaWidgetBase):
        _translate = QtCore.QCoreApplication.translate
        QRAVEMetaWidgetBase.setWindowTitle(_translate("QRAVEMetaWidgetBase", "Riverscapes Meta"))
