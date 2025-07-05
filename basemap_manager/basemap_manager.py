from qgis.PyQt.QtWidgets import (
    QAction, QDialog, QListWidget, QListWidgetItem, QLineEdit,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox,
    QCheckBox, QComboBox, QTabWidget, QSplitter, QFrame, QMessageBox,
    QSizePolicy, QSpacerItem
)
from qgis.PyQt.QtCore import Qt, QSettings, QSize
from qgis.PyQt.QtGui import QIcon, QFont, QColor, QPalette
from qgis.core import (
    QgsProject, QgsRasterLayer, QgsCoordinateReferenceSystem,
    QgsApplication, QgsSettings
)
import json
import os
import webbrowser

class BasemapManager:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.providers = self.load_providers()
        self.custom_providers = []
        self.load_custom_providers()
        
    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "logo.png")
        self.action = QAction(
            QIcon(icon_path),
            "Basemap Manager",
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self.show_dialog)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("Basemap Tools", self.action)
        
    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("Basemap Tools", self.action)
        
    def load_styles(self):
        """Load styles from external stylesheet"""
        style_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(style_path):
            with open(style_path, "r") as f:
                return f.read()
        return ""
        
    def load_providers(self):
        try:
            with open(os.path.join(os.path.dirname(__file__), 'providers.json')) as f:
                return json.load(f)
        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                "Provider Error",
                f"Failed to load providers: {str(e)}"
            )
            return {}
    
    def load_custom_providers(self):
        settings = QgsSettings()
        custom = settings.value("basemap_manager/custom_providers", "[]")
        try:
            self.custom_providers = json.loads(custom)
        except:
            self.custom_providers = []
    
    def save_custom_providers(self):
        settings = QgsSettings()
        settings.setValue("basemap_manager/custom_providers", json.dumps(self.custom_providers))
    
    def add_basemap(self, provider_data):
        """Add basemap from provider data dictionary"""
        # Remove previous basemap if configured
        if QSettings().value("basemap_manager/auto_remove", True, type=bool):
            self.remove_existing_basemaps()
            
        # Create layer
        url = provider_data["url"]
        name = provider_data["name"]
        
        rlayer = QgsRasterLayer(
            f"type=xyz&url={url}&zmax={provider_data.get('zmax',19)}",
            name,
            "wms"
        )
        
        # Validate projection
        auto_crs = QSettings().value("basemap_manager/auto_crs", True, type=bool)
        if auto_crs and not rlayer.crs().isValid():
            # Use Web Mercator (EPSG:3857) for basemaps instead of WGS84
            rlayer.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
            
        if rlayer.isValid():
            QgsProject.instance().addMapLayer(rlayer)
            # Move to bottom of layer stack
            root = QgsProject.instance().layerTreeRoot()
            layer_node = root.findLayer(rlayer.id())
            if layer_node:
                layer_clone = layer_node.clone()
                root.insertChildNode(0, layer_clone)
                parent = layer_node.parent()
                parent.removeChildNode(layer_node)
            return True
        
        # Show error if layer not valid
        QMessageBox.warning(
            self.iface.mainWindow(),
            "Layer Error",
            f"Failed to load basemap: {rlayer.error().message()}"
        )
        return False
        
    def remove_existing_basemaps(self):
        """Remove any existing basemap layers"""
        provider_names = [p['name'] for p in self.providers.values()]
        provider_names += [p['name'] for p in self.custom_providers]
        
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() in provider_names:
                QgsProject.instance().removeMapLayer(layer)
                
    def show_dialog(self):
        """Show the main dialog window"""
        self.dlg = QDialog(self.iface.mainWindow())
        self.dlg.setWindowTitle("Basemap Manager")
        self.dlg.setMinimumSize(700, 550)
        
        # Set object name for styling
        self.dlg.setObjectName("mainDialog")
        
        # Apply styles
        self.dlg.setStyleSheet(self.load_styles())
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Tab widget for different sections
        tabs = QTabWidget()
        tabs.setObjectName("mainTabs")
        
        # Main basemap selection tab
        main_tab = QFrame()
        main_layout = QVBoxLayout(main_tab)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Search box
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search basemaps...")
        self.search_box.setMinimumHeight(32)
        self.search_box.textChanged.connect(self.filter_basemaps)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_box)
        main_layout.addLayout(search_layout)
        
        # Basemap list
        self.basemap_list = QListWidget()
        self.basemap_list.setObjectName("basemapList")
        self.basemap_list.setIconSize(QSize(32, 32))
        self.basemap_list.setMinimumHeight(300)
        self.populate_basemap_list()
        self.basemap_list.itemDoubleClicked.connect(self.apply_selected_basemap)
        main_layout.addWidget(self.basemap_list)
        
        # Apply button
        btn_apply = QPushButton("Apply Basemap")
        btn_apply.setObjectName("primaryButton")
        btn_apply.setMinimumHeight(36)
        btn_apply.clicked.connect(self.apply_selected_basemap)
        main_layout.addWidget(btn_apply)
        
        # Settings tab
        settings_tab = QFrame()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(15)
        
        # Layer management group
        layer_group = QGroupBox("Layer Management")
        layer_layout = QVBoxLayout()
        layer_layout.setContentsMargins(12, 15, 12, 15)
        layer_layout.setSpacing(10)
        
        self.cb_auto_remove = QCheckBox("Automatically remove previous basemap")
        self.cb_auto_remove.setChecked(
            QSettings().value("basemap_manager/auto_remove", True, type=bool)
        )
        layer_layout.addWidget(self.cb_auto_remove)
        
        self.cb_auto_crs = QCheckBox("Auto-set CRS to EPSG:3857 when missing")
        self.cb_auto_crs.setChecked(
            QSettings().value("basemap_manager/auto_crs", True, type=bool)
        )
        self.cb_auto_crs.setToolTip("Most basemaps use Web Mercator projection (EPSG:3857)")
        layer_layout.addWidget(self.cb_auto_crs)
        layer_group.setLayout(layer_layout)
        settings_layout.addWidget(layer_group)
        
        # Custom providers group
        custom_group = QGroupBox("Custom Basemaps")
        custom_layout = QVBoxLayout()
        custom_layout.setContentsMargins(12, 15, 12, 15)
        custom_layout.setSpacing(10)
        
        self.custom_list = QListWidget()
        self.custom_list.setObjectName("customList")
        self.custom_list.setMinimumHeight(150)
        self.populate_custom_list()
        custom_layout.addWidget(self.custom_list)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_add = QPushButton("Add New")
        btn_add.setObjectName("actionButton")
        btn_add.clicked.connect(self.show_custom_provider_dialog)
        btn_remove = QPushButton("Remove Selected")
        btn_remove.setObjectName("warningButton")
        btn_remove.clicked.connect(self.remove_custom_provider)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        custom_layout.addLayout(btn_layout)
        custom_group.setLayout(custom_layout)
        settings_layout.addWidget(custom_group)
        
        # Add spacer to push content up
        settings_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Add tabs
        tabs.addTab(main_tab, "Basemaps")
        tabs.addTab(settings_tab, "Settings")
        layout.addWidget(tabs)
        
        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Documentation button
        btn_docs = QPushButton("Documentation")
        btn_docs.setObjectName("secondaryButton")
        btn_docs.clicked.connect(self.open_documentation)
        button_layout.addWidget(btn_docs)
        
        # Close button
        btn_close = QPushButton("Close")
        btn_close.setObjectName("secondaryButton")
        btn_close.setMinimumWidth(100)
        btn_close.clicked.connect(self.dlg.close)
        button_layout.addWidget(btn_close)
        
        layout.addLayout(button_layout)
        
        # Connect finished signal to save settings
        self.dlg.finished.connect(self.save_settings)
        
        self.dlg.setLayout(layout)
        self.dlg.show()
    
    def open_documentation(self):
        """Open documentation in browser"""
        webbrowser.open("https://github.com/qgis/basemap-manager/docs")
    
    def populate_basemap_list(self):
        """Populate list with all available basemaps"""
        self.basemap_list.clear()
        
        # Add standard providers
        for key, provider in self.providers.items():
            item = QListWidgetItem(provider["name"])
            item.setData(Qt.UserRole, {"type": "standard", "key": key})
            # Add placeholder icon
            icon_path = os.path.join(os.path.dirname(__file__), "basemap_icon.png")
            if os.path.exists(icon_path):
                item.setIcon(QIcon(icon_path))
            self.basemap_list.addItem(item)
        
        # Add custom providers
        if self.custom_providers:
            item = QListWidgetItem("─── Custom Basemaps ───")
            item.setFlags(Qt.NoItemFlags)
            font = QFont()
            font.setBold(True)
            item.setFont(font)
            self.basemap_list.addItem(item)
            
            for provider in self.custom_providers:
                item = QListWidgetItem(provider["name"])
                item.setData(Qt.UserRole, {"type": "custom", "data": provider})
                icon_path = os.path.join(os.path.dirname(__file__), "custom_icon.png")
                if os.path.exists(icon_path):
                    item.setIcon(QIcon(icon_path))
                self.basemap_list.addItem(item)
    
    def populate_custom_list(self):
        """Populate custom providers list in settings"""
        self.custom_list.clear()
        for provider in self.custom_providers:
            item = QListWidgetItem(provider["name"])
            icon_path = os.path.join(os.path.dirname(__file__), "custom_icon.png")
            if os.path.exists(icon_path):
                item.setIcon(QIcon(icon_path))
            self.custom_list.addItem(item)
    
    def filter_basemaps(self, text):
        """Filter basemap list based on search text"""
        text = text.lower()
        for i in range(self.basemap_list.count()):
            item = self.basemap_list.item(i)
            item.setHidden(text not in item.text().lower())
    
    def apply_selected_basemap(self):
        """Apply the selected basemap"""
        selected = self.basemap_list.currentItem()
        if not selected:
            return
            
        data = selected.data(Qt.UserRole)
        provider = None
        
        if data["type"] == "standard":
            provider = self.providers[data["key"]]
        elif data["type"] == "custom":
            provider = data["data"]
            
        if provider:
            success = self.add_basemap(provider)
            if success:
                self.dlg.close()
    
    def show_custom_provider_dialog(self):
        """Show dialog to add new custom provider"""
        dlg = QDialog(self.dlg)
        dlg.setWindowTitle("Add Custom Basemap")
        dlg.setMinimumWidth(500)
        dlg.setObjectName("addCustomProviderDialog")
        dlg.setStyleSheet(self.load_styles())
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Form layout
        form_layout = QVBoxLayout()
        form_layout.setSpacing(12)
        
        # Name field
        name_layout = QHBoxLayout()
        name_layout.setSpacing(15)
        name_layout.addWidget(QLabel("Name:"))
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g., My Satellite Imagery")
        name_layout.addWidget(self.txt_name)
        form_layout.addLayout(name_layout)
        
        # URL field
        url_layout = QHBoxLayout()
        url_layout.setSpacing(15)
        url_layout.addWidget(QLabel("URL Template:"))
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("https://example.com/{z}/{x}/{y}.png")
        url_layout.addWidget(self.txt_url)
        form_layout.addLayout(url_layout)
        
        # Max Zoom
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(15)
        zoom_layout.addWidget(QLabel("Max Zoom:"))
        self.spin_zoom = QComboBox()
        self.spin_zoom.addItems([str(i) for i in range(10, 23)])
        self.spin_zoom.setCurrentText("19")
        zoom_layout.addWidget(self.spin_zoom)
        form_layout.addLayout(zoom_layout)
        
        # Attribution
        attr_layout = QHBoxLayout()
        attr_layout.setSpacing(15)
        attr_layout.addWidget(QLabel("Attribution:"))
        self.txt_attr = QLineEdit()
        self.txt_attr.setPlaceholderText("© Map Provider 2023")
        attr_layout.addWidget(self.txt_attr)
        form_layout.addLayout(attr_layout)
        
        layout.addLayout(form_layout)
        
        # Info label
        info_label = QLabel("Note: Use {x}, {y}, {z} placeholders in URL")
        info_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        layout.addWidget(info_label)
        
        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Buttons
        btn_save = QPushButton("Save")
        btn_save.setObjectName("actionButton")
        btn_save.setMinimumWidth(100)
        btn_save.clicked.connect(lambda: self.save_custom_provider(dlg))
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.setMinimumWidth(100)
        btn_cancel.clicked.connect(dlg.reject)
        
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)
        
        dlg.setLayout(layout)
        dlg.exec_()
    
    def save_custom_provider(self, dlg):
        """Save new custom provider"""
        name = self.txt_name.text().strip()
        url = self.txt_url.text().strip()
        zmax = int(self.spin_zoom.currentText())
        attribution = self.txt_attr.text().strip()
        
        if not name or not url:
            QMessageBox.warning(
                dlg,
                "Missing Information",
                "Name and URL are required fields"
            )
            return
            
        new_provider = {
            "name": name,
            "url": url,
            "zmax": zmax,
            "attribution": attribution,
            "category": "Custom"
        }
        
        self.custom_providers.append(new_provider)
        self.save_custom_providers()
        self.populate_basemap_list()
        self.populate_custom_list()
        dlg.accept()
    
    def remove_custom_provider(self):
        """Remove selected custom provider"""
        selected = self.custom_list.currentRow()
        if selected >= 0:
            reply = QMessageBox.question(
                self.dlg,
                "Confirm Removal",
                "Delete this custom basemap?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.custom_providers.pop(selected)
                self.save_custom_providers()
                self.populate_basemap_list()
                self.populate_custom_list()

    def save_settings(self):
        """Save settings when dialog closes"""
        settings = QSettings()
        settings.setValue("basemap_manager/auto_remove", self.cb_auto_remove.isChecked())
        settings.setValue("basemap_manager/auto_crs", self.cb_auto_crs.isChecked())