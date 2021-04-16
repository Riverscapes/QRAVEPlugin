

# from qgis.PyQt.QtWidgets import
# class TreeeView(QWidget):
#     def __init__(self, treeView: QTreeView, tree: QStandardItem = None):

#         super(TreeeView, self).__init__()

#         self.settings = Settings()
#         self.tree = treeView
#         self.tree = tree
#         self.basemaps = None

#         layout = QVBoxLayout(self)
#         layout.addWidget(self.tree)
#         self.model = QStandardItemModel()
#         # self.model.setHorizontalHeaderLabels(['Name', 'Height', 'Weight'])
#         # self.tree.header().setDefaultSectionSize(180)
#         self.tree.setModel(self.model)
#         # self.importData(data)
#         self.load()


#     def load_basemaps(self):
#         if not os.path.isfile(BASEMAPS_XML_PATH):
#             return
#         self.tree = ET.parse(BASEMAPS_XML_PATH)
#         self.root = self.tree.getroot()
