"""
Settings dialog for configuring the application.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QSpinBox, QCheckBox, QGroupBox,
    QFormLayout, QMessageBox, QListWidget, QListWidgetItem,
    QInputDialog
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from api_client import APIClient, ResearchGroup


class ConnectionTestWorker(QThread):
    """Worker thread for testing connection."""
    finished = Signal(bool)
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
    
    def run(self):
        result = self.api_client.health_check()
        self.finished.emit(result)


class SettingsDialog(QDialog):
    """Dialog for application settings."""
    
    def __init__(self, api_client: APIClient, settings_manager, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.settings_manager = settings_manager
        self.groups: list[ResearchGroup] = []
        self.worker = None
        
        self.setup_ui()
        self.load_settings()
        self.load_groups()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Settings")
        self.setFixedWidth(450)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Timing section
        timing_group = QGroupBox("Timing")
        timing_layout = QFormLayout(timing_group)
        
        self.interval_combo = QComboBox()
        for minutes in [15, 30, 45, 60]:
            self.interval_combo.addItem(f"{minutes} minutes", minutes)
        timing_layout.addRow("Prompt Interval:", self.interval_combo)
        
        layout.addWidget(timing_group)
        
        # Server section
        server_group = QGroupBox("Server")
        server_layout = QVBoxLayout(server_group)
        
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://localhost:5001")
        url_layout.addWidget(self.url_input)
        
        self.test_btn = QPushButton("Test")
        self.test_btn.clicked.connect(self.test_connection)
        url_layout.addWidget(self.test_btn)
        
        server_layout.addLayout(url_layout)
        
        self.status_label = QLabel("Status: Unknown")
        self.status_label.setStyleSheet("color: #666;")
        server_layout.addWidget(self.status_label)
        
        layout.addWidget(server_group)
        
        # Research Groups section
        groups_group = QGroupBox("Research Groups")
        groups_layout = QVBoxLayout(groups_group)
        
        # Default group picker
        default_layout = QHBoxLayout()
        default_layout.addWidget(QLabel("Default Group:"))
        self.default_group_combo = QComboBox()
        default_layout.addWidget(self.default_group_combo, 1)
        groups_layout.addLayout(default_layout)
        
        # Groups list with delete
        self.groups_list = QListWidget()
        self.groups_list.setMaximumHeight(120)
        groups_layout.addWidget(self.groups_list)
        
        # Group buttons
        group_btn_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_groups)
        group_btn_layout.addWidget(self.refresh_btn)
        
        self.new_group_btn = QPushButton("New Group...")
        self.new_group_btn.clicked.connect(self.create_new_group)
        group_btn_layout.addWidget(self.new_group_btn)
        
        self.delete_group_btn = QPushButton("Delete")
        self.delete_group_btn.clicked.connect(self.delete_selected_group)
        self.delete_group_btn.setStyleSheet("color: red;")
        group_btn_layout.addWidget(self.delete_group_btn)
        
        groups_layout.addLayout(group_btn_layout)
        
        layout.addWidget(groups_group)
        
        # Startup section
        startup_group = QGroupBox("Startup")
        startup_layout = QVBoxLayout(startup_group)
        
        self.launch_checkbox = QCheckBox("Launch at login")
        startup_layout.addWidget(self.launch_checkbox)
        
        layout.addWidget(startup_group)
        
        # Buttons
        layout.addStretch()
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                padding: 6px 20px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        button_layout.addWidget(self.save_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def load_settings(self):
        """Load current settings into the UI."""
        # URL
        self.url_input.setText(self.settings_manager.backend_url)
        
        # Interval
        interval = self.settings_manager.prompt_interval_minutes
        for i in range(self.interval_combo.count()):
            if self.interval_combo.itemData(i) == interval:
                self.interval_combo.setCurrentIndex(i)
                break
        
        # Launch at login
        self.launch_checkbox.setChecked(self.settings_manager.launch_at_login)
    
    def load_groups(self):
        """Load research groups from the API."""
        self.groups_list.clear()
        self.default_group_combo.clear()
        self.default_group_combo.addItem("None", None)
        
        try:
            self.groups = self.api_client.fetch_groups()
            
            for group in self.groups:
                # Add to list
                item = QListWidgetItem(f"{group.name} ({group.project_name})")
                item.setData(Qt.ItemDataRole.UserRole, group.id)
                self.groups_list.addItem(item)
                
                # Add to default combo
                self.default_group_combo.addItem(group.name, group.id)
            
            # Set default group
            default_id = self.settings_manager.default_group_id
            if default_id is not None:
                for i in range(self.default_group_combo.count()):
                    if self.default_group_combo.itemData(i) == default_id:
                        self.default_group_combo.setCurrentIndex(i)
                        break
                        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load groups: {e}")
    
    def test_connection(self):
        """Test connection to the backend."""
        # Update API client URL first
        url = self.url_input.text().strip()
        if url:
            self.api_client.update_base_url(url)
        
        self.status_label.setText("Status: Testing...")
        self.status_label.setStyleSheet("color: #666;")
        self.test_btn.setEnabled(False)
        
        self.worker = ConnectionTestWorker(self.api_client)
        self.worker.finished.connect(self.on_connection_test_finished)
        self.worker.start()
    
    def on_connection_test_finished(self, connected: bool):
        """Handle connection test result."""
        self.test_btn.setEnabled(True)
        
        if connected:
            self.status_label.setText("Status: Connected")
            self.status_label.setStyleSheet("color: green;")
            self.load_groups()
        else:
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("color: red;")
    
    def create_new_group(self):
        """Create a new research group."""
        name, ok = QInputDialog.getText(
            self, "New Group", "Group Name:"
        )
        if not ok or not name.strip():
            return
        
        manager, _ = QInputDialog.getText(
            self, "New Group", "Manager Name (optional):"
        )
        
        project, _ = QInputDialog.getText(
            self, "New Group", "Project Name (optional):"
        )
        
        try:
            group = self.api_client.create_group(
                name=name.strip(),
                manager_name=manager.strip() if manager else "",
                project_name=project.strip() if project else ""
            )
            self.load_groups()
            
            # Select the new group as default
            for i in range(self.default_group_combo.count()):
                if self.default_group_combo.itemData(i) == group.id:
                    self.default_group_combo.setCurrentIndex(i)
                    break
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create group: {e}")
    
    def delete_selected_group(self):
        """Delete the selected group."""
        item = self.groups_list.currentItem()
        if not item:
            QMessageBox.information(self, "Info", "Please select a group to delete")
            return
        
        group_id = item.data(Qt.ItemDataRole.UserRole)
        group_name = item.text().split(" (")[0]
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete '{group_name}' and all its entries?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.api_client.delete_group(group_id):
                # Clear default if it was the deleted group
                if self.settings_manager.default_group_id == group_id:
                    self.settings_manager.default_group_id = None
                self.load_groups()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete group")
    
    def save_settings(self):
        """Save settings."""
        self.settings_manager.backend_url = self.url_input.text().strip()
        self.settings_manager.prompt_interval_minutes = self.interval_combo.currentData()
        self.settings_manager.default_group_id = self.default_group_combo.currentData()
        self.settings_manager.launch_at_login = self.launch_checkbox.isChecked()
        
        # Update API client
        self.api_client.update_base_url(self.settings_manager.backend_url)
        
        QMessageBox.information(self, "Settings", "Settings saved successfully")
