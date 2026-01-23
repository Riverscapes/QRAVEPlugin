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
            'apiUrl': (CONSTANTS['DE_API_URL'], 'string')
        }
        
        self.bounds = self.data.get('bounds')
        self.default_view = self.tree_data.get('defaultView')
        self.views = {}
        
        self.qproject = None
        self.exists = True  # Remote project always exists if we have data
        self.loadable = True
        self.project_dir = None # Remote projects don't have a local dir (yet)

        # Map datasets for metadata lookup
        self._build_dataset_maps()
        self.dataset_item_map = {}
        self._icon_cache = {}

    def _get_icon(self, path: str) -> QIcon:
        if path not in self._icon_cache:
            self._icon_cache[path] = QIcon(path)
        return self._icon_cache[path]

    def load(self):
        """Build the tree from GraphQL data"""
        self._build_tree()
        self._build_views()

    @property
    def has_bounds(self) -> bool:
        """Check if the project has valid bounds"""
        if not self.bounds:
            return False
        bbox = self.bounds.get('bbox')
        return bool(bbox and len(bbox) >= 4)

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
        datasets_resp = self.data.get('datasets', {})
        self.datasets = datasets_resp.get('items', []) if datasets_resp else []
        
        for ds in self.datasets:
            if not ds:
                continue
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
        self.qproject = QStandardItem(self._get_icon(':/plugins/qrave_toolbar/data-exchange-icon.svg'), self.name)
        self.qproject.setData(ProjectTreeData(QRaveTreeTypes.PROJECT_ROOT, project=self), Qt.UserRole)

        # Index branches and leaves by pid for efficient recursive lookup
        branch_map = {}
        for b in branches:
            p = b.get('pid', 'root')
            if p not in branch_map:
                branch_map[p] = []
            branch_map[p].append(b)

        leaf_map = {}
        for l in leaves:
            p = l.get('pid', 'root')
            if p not in leaf_map:
                leaf_map[p] = []
            leaf_map[p].append(l)

        # Start recursion. Usually roots have pid = -1 in the API results
        self._recurse_build_tree(-1, self.qproject, branch_map, leaf_map)
        
        # Fallback if -1 didn't catch anything (though usually it should)
        if self.qproject.rowCount() == 0:
            self._recurse_build_tree('root', self.qproject, branch_map, leaf_map)

    def _recurse_build_tree(self, pid, parent_item, branch_map, leaf_map):
        """Recursively build the tree starting from a given pid"""
        
        # Build branches
        for branch in branch_map.get(pid, []):
            bid = branch.get('bid')
            label = branch.get('label')
            
            # Skip the branch if it is at the root level and promote children
            if pid == -1:
                self.settings.log(f"Skipping root branch and promoting children: {label}", Qgis.Info)
                # Recurse from this branch's ID but attach children directly to the parent_item
                self._recurse_build_tree(bid, parent_item, branch_map, leaf_map)
                continue

            item = QStandardItem(self._get_icon(':/plugins/qrave_toolbar/BrowseFolder.png'), label)
            item.setData(ProjectTreeData(QRaveTreeTypes.PROJECT_FOLDER, project=self, data={'collapsed': branch.get('collapsed')}), Qt.UserRole)
            parent_item.appendRow(item)
            
            # Recurse for children of this branch
            self._recurse_build_tree(bid, item, branch_map, leaf_map)

        # Build leaves
        for leaf in leaf_map.get(pid, []):
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

            item = QStandardItem(self._get_icon(icon_path), leaf.get('label'))
            
            # Map GraphQL leaf to QRaveMapLayer
            layer_uri = leaf.get('filePath')
            
            bl_attr = {
                'id': leaf.get('blLayerId'),
                'type': leaf.get('layerType'),
                'symbology': leaf.get('symbology'),
                'transparency': str(leaf.get('transparency', 0)),
                'rsXPath': leaf.get('rsXPath'),
                'nodeId': leaf.get('nodeId')
            }
            
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
            
            map_layer.exists = False 
            
            item.setData(ProjectTreeData(QRaveTreeTypes.LEAF, project=self, data=map_layer), Qt.UserRole)
            parent_item.appendRow(item)

            # Add to the item map so we can update it later
            if rs_xpath:
                if rs_xpath not in self.dataset_item_map:
                    self.dataset_item_map[rs_xpath] = []
                self.dataset_item_map[rs_xpath].append(item)
            if node_id:
                if node_id not in self.dataset_item_map:
                    self.dataset_item_map[node_id] = []
                self.dataset_item_map[node_id].append(item)

    def _build_views(self):
        views_data = self.tree_data.get('views', [])
        if not views_data:
            return

        curr_item = QStandardItem(self._get_icon(':/plugins/qrave_toolbar/BrowseFolder.png'), "Project Views")
        curr_item.setData(ProjectTreeData(QRaveTreeTypes.PROJECT_VIEW_FOLDER, project=self), Qt.UserRole)

        for view in views_data:
            name = view.get('name')
            view_id = view.get('id')
            
            if not name or not view_id:
                continue

            view_item = QStandardItem(self._get_icon(':/plugins/qrave_toolbar/view.svg'), name)
            view_layers = view.get('layers', [])
            view_layer_ids = [l.get('id') for l in view_layers if l.get('visible')]
            self.views[view_id] = view_layer_ids
            view_item.setData(
                ProjectTreeData(QRaveTreeTypes.PROJECT_VIEW, project=self, data=view_layer_ids),
                Qt.UserRole
            )
            curr_item.appendRow(view_item)

        self.qproject.appendRow(curr_item)

    def update_dataset_metadata(self, new_datasets: List[Dict]):
        """Update metadata and description for datasets from async fetch"""
        count = 0
        for ds in new_datasets:
            dataset_meta = self._extract_meta(ds.get('meta', []))
            # In the new query we use 'description' but fallback to 'summary' if needed
            dataset_desc = ds.get('description', ds.get('summary', ''))
            
            ds_info = {'meta': dataset_meta, 'description': dataset_desc}
            
            xpath = ds.get('rsXPath')
            ds_id = ds.get('id')
            
            # Update the map
            if xpath:
                self.dataset_meta_map[xpath] = ds_info
            if ds_id:
                self.dataset_meta_map[ds_id] = ds_info
                
            # Update items
            tree_items = []
            if xpath and xpath in self.dataset_item_map:
                tree_items.extend(self.dataset_item_map[xpath])
            if ds_id and ds_id in self.dataset_item_map:
                tree_items.extend(self.dataset_item_map[ds_id])
                
            # Filter duplicates safely
            unique_items = []
            for item in tree_items:
                if item not in unique_items:
                    unique_items.append(item)
            tree_items = unique_items

            # Prepare layer lookup map for this dataset
            ds_layers = ds.get('layers', [])
            layers_map = {l['lyrName']: l for l in ds_layers if 'lyrName' in l}

            for item in tree_items:
                tree_data = item.data(Qt.UserRole)
                if tree_data and isinstance(tree_data.data, QRaveMapLayer):
                    layer = tree_data.data
                    
                    # Default to using dataset metadata
                    meta_to_use = dataset_meta
                    desc_to_use = dataset_desc
                    
                    # If the dataset has layers and this item matches a layer name, use specific layer metadata
                    if layer.layer_name and layer.layer_name in layers_map:
                        layer_data = layers_map[layer.layer_name]
                        layer_meta = self._extract_meta(layer_data.get('meta', []))
                        layer_desc = layer_data.get('description', layer_data.get('summary', ''))
                        
                        # Override if layer has specific metadata
                        if layer_meta:
                            meta_to_use = layer_meta
                        if layer_desc:
                            desc_to_use = layer_desc

                    layer.meta = meta_to_use
                    layer.description = desc_to_use
                    # We don't need to setData again because we modified the object in place
                    count += 1
        
        self.settings.log(f"RemoteProject {self.id}: Updated metadata for {count} dataset references", Qgis.Info)
