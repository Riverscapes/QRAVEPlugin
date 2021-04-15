# from qgis.PyQt.QtCore import Qmodel
# https://github.com/avi-psvm-dutta/eSim/blob/8e49c648311dec359374d9360d9f571dd5477093/src/frontEnd/ProjectExplorer.py


class TreeModel:

    FROM, SUBJECT, DATE = range(3)

    # def createMailModel(self, parent):
    #     model = QStandardItemModel(0, 3, parent)
    #     model.setHeaderData(self.FROM, Qt.Horizontal, "From")
    #     model.setHeaderData(self.SUBJECT, Qt.Horizontal, "Subject")
    #     model.setHeaderData(self.DATE, Qt.Horizontal, "Date")
    #     return model
