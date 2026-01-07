from __future__ import annotations
import os
import json
from typing import Dict, List
from qgis.core import Qgis
from qgis.PyQt.QtGui import QStandardItem, QIcon, QBrush
from qgis.PyQt.QtCore import Qt

from .qrave_map_layer import QRaveMapLayer, QRaveTreeTypes, ProjectTreeData
from .settings import CONSTANTS, Settings


class RemoteProject:

    def __init__(self, gql_data: Dict):
        self.settings = Settings()
        # Handle both wrapped and unwrapped data
        if 'data' in gql_data:
            self.data = gql_data.get('data', {}).get('project', {}) or {}
        else:
            self.data = gql_data.get('project', {}) or gql_data

        self.id = self.data.get('id')
        self.name = self.data.get('name')
        self.tree_data = self.data.get('tree', {}) or {}
        self.description = self.data.get('summary') or self.tree_data.get('description', '')
        self.project_type = self.data.get('projectType', {}).get('id')
        self.meta = self._extract_meta(self.data.get('meta', []))
        self.warehouse_meta = {
            'id': (self.id, 'string'),
            'apiUrl': (CONSTANTS['DE_API_URL'], 'string')
        }
        
        self.default_view = self.tree_data.get('defaultView')
        self.views = {}
        
        self.qproject = None
        self.exists = True  # Remote project always exists if we have data
        self.loadable = True
        self.project_dir = None # Remote projects don't have a local dir (yet)

        # Map datasets for metadata lookup
        self._build_dataset_maps()

    def load(self):
        """Build the tree from GraphQL data"""
        self._build_tree()
        self._build_views()

    def _extract_meta(self, meta_list: List[Dict]):
        meta = {}
        if meta_list is None:
            return meta
        for m in meta_list:
            key = m.get('key')
            if key:
                # MetaWidget expects a string for value, and GQL might return null
                val = str(m.get('value')) if m.get('value') is not None else ""
                meta[key] = (val, m.get('type'))
        return meta

    def _build_dataset_maps(self):
        # Map datasets for metadata lookup by both rsXPath and ID
        self.dataset_meta_map = {}
        self.datasets = self.data.get('datasets', {}).get('items', [])
        
        for ds in self.datasets:
            meta = self._extract_meta(ds.get('meta', []))
            summary = ds.get('summary', '')
            
            ds_info = {'meta': meta, 'description': summary}
            
            xpath = ds.get('rsXPath')
            if xpath:
                self.dataset_meta_map[xpath] = ds_info
            
            # Also map by ID as a fallback
            ds_id = ds.get('id')
            if ds_id:
                self.dataset_meta_map[ds_id] = ds_info
        
        self.settings.log(f"RemoteProject {self.id}: Mapped {len(self.datasets)} datasets for metadata lookup", Qgis.Info)

    def _build_tree(self):
        """Parse the flat GraphQL tree structure and build QStandardItems"""
        leaves = self.tree_data.get('leaves', [])
        branches = self.tree_data.get('branches', [])
        
        # Create the root item
        self.qproject = QStandardItem(QIcon(':/plugins/qrave_toolbar/data-exchange-icon.svg'), self.name)
        self.qproject.setData(ProjectTreeData(QRaveTreeTypes.PROJECT_ROOT, project=self), Qt.UserRole)

        # Map to store items by their id (bid for branches, id for leaves)
        items_map = {'root': self.qproject}
        
        # Build branches first
        # We might need to iterate multiple times if parents are defined after children
        pending_branches = list(branches)
        while pending_branches:
            progress = False
            for branch in list(pending_branches):
                bid = branch.get('bid')
                pid = branch.get('pid') or 'root'
                
                if pid in items_map:
                    item = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), branch.get('label'))
                    item.setData(ProjectTreeData(QRaveTreeTypes.PROJECT_FOLDER, project=self, data={'collapsed': branch.get('collapsed')}), Qt.UserRole)
                    items_map[pid].appendRow(item)
                    items_map[bid] = item
                    pending_branches.remove(branch)
                    progress = True
            
            if not progress and pending_branches:
                # This means some branches have missing parents or a circular dependency
                # Fallback to root for them
                for branch in pending_branches:
                    item = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), branch.get('label'))
                    item.setData(ProjectTreeData(QRaveTreeTypes.PROJECT_FOLDER, project=self, data={'collapsed': branch.get('collapsed')}), Qt.UserRole)
                    self.qproject.appendRow(item)
                    items_map[branch.get('bid')] = item
                break

        # Build leaves
        for leaf in leaves:
            pid = leaf.get('pid') or 'root'
            
            # Decide icon based on layer type
            icon_path = ':/plugins/qrave_toolbar/viewer-icon.png'
            bl_type = leaf.get('layerType', '').lower()
            if bl_type == 'polygon':
                icon_path = ':/plugins/qrave_toolbar/layers/Polygon.png'
            elif bl_type == 'line':
                icon_path = ':/plugins/qrave_toolbar/layers/Polyline.png'
            elif bl_type == 'point':
                icon_path = ':/plugins/qrave_toolbar/layers/MultiDot.png'
            elif bl_type == 'raster':
                icon_path = ':/plugins/qrave_toolbar/layers/Raster.png'
            elif bl_type == 'file':
                icon_path = ':/plugins/qrave_toolbar/draft.svg'
            elif bl_type == 'report':
                icon_path = ':/plugins/qrave_toolbar/description.svg'
            elif bl_type == 'tin':
                icon_path = ':/plugins/qrave_toolbar/layers/tin.svg'

            item = QStandardItem(QIcon(icon_path), leaf.get('label'))
            
            # Map GraphQL leaf to QRaveMapLayer
            # In remote projects, layer_uri might be a URL or we might not have it locally
            # For now, we'll store the filePath as layer_uri
            layer_uri = leaf.get('filePath')
            
            # Mock bl_attr from leaf data
            bl_attr = {
                'id': leaf.get('blLayerId'),
                'type': leaf.get('layerType'),
                'symbology': leaf.get('symbology'),
                'transparency': str(leaf.get('transparency', 0)),
                'rsXPath': leaf.get('rsXPath'),
                'nodeId': leaf.get('nodeId')
            }
            
            # Match leaf to dataset metadata
            rs_xpath = leaf.get('rsXPath')
            node_id = leaf.get('nodeId')
            
            meta = {}
            description = None
            if rs_xpath and rs_xpath in self.dataset_meta_map:
                ds_info = self.dataset_meta_map[rs_xpath]
                meta = ds_info['meta']
                description = ds_info['description']
            elif node_id and node_id in self.dataset_meta_map:
                ds_info = self.dataset_meta_map[node_id]
                meta = ds_info['meta']
                description = ds_info['description']
            
            map_layer = QRaveMapLayer(
                label=leaf.get('label'),
                layer_type=bl_type,
                layer_uri=layer_uri,
                bl_attr=bl_attr,
                meta=meta,
                layer_name=leaf.get('lyrName'),
                description=description
            )
            
            # Since this is remote, the file likely doesn't exist locally unless downloaded
            # The UI highlights missing files in red.
            map_layer.exists = False 
            
            item.setData(ProjectTreeData(QRaveTreeTypes.LEAF, project=self, data=map_layer), Qt.UserRole)
            
            if pid in items_map:
                items_map[pid].appendRow(item)
            else:
                self.qproject.appendRow(item)

    def _build_views(self):
        views_data = self.tree_data.get('views', [])
        if not views_data:
            return

        curr_item = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), "Project Views")
        curr_item.setData(ProjectTreeData(QRaveTreeTypes.PROJECT_VIEW_FOLDER, project=self), Qt.UserRole)

        for view in views_data:
            name = view.get('name')
            view_id = view.get('id')
            
            if not name or not view_id:
                continue

            view_item = QStandardItem(QIcon(':/plugins/qrave_toolbar/view.svg'), name)
            view_layers = view.get('layers', [])
            view_layer_ids = [l.get('id') for l in view_layers if l.get('visible')]
            self.views[view_id] = view_layer_ids
            view_item.setData(
                ProjectTreeData(QRaveTreeTypes.PROJECT_VIEW, project=self, data=view_layer_ids),
                Qt.UserRole
            )
            curr_item.appendRow(view_item)

        self.qproject.appendRow(curr_item)
