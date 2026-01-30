"""
Time logging prompt dialog.
"""

from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QTimeEdit, QPushButton, QTextEdit, QMessageBox,
    QProgressBar
)
from PySide6.QtCore import Qt, QTime, QThread, Signal
from PySide6.QtGui import QFont

from api_client import APIClient, ResearchGroup


class SubmitWorker(QThread):
    """Worker thread for submitting entries."""
    finished = Signal(object)  # TimeEntryResponse or Exception
    
    def __init__(self, api_client, group_id, task, start_time, end_time):
        super().__init__()
        self.api_client = api_client
        self.group_id = group_id
        self.task = task
        self.start_time = start_time
        self.end_time = end_time
    
    def run(self):
        try:
            response = self.api_client.create_entry(
                research_group_id=self.group_id,
                task_description=self.task,
                start_time=self.start_time,
                end_time=self.end_time
            )
            self.finished.emit(response)
        except Exception as e:
            self.finished.emit(e)


class PromptDialog(QDialog):
    """Dialog for logging time entries."""
    
    def __init__(self, api_client: APIClient, settings_manager, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.settings_manager = settings_manager
        self.groups: list[ResearchGroup] = []
        self.worker = None
        
        self.setup_ui()
        self.load_groups()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Log Time")
        self.setFixedWidth(400)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("What are you working on?")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Task description
        task_label = QLabel("Task Description")
        task_label.setStyleSheet("color: #666;")
        layout.addWidget(task_label)
        
        self.task_input = QTextEdit()
        self.task_input.setPlaceholderText("Enter what you've been working on...")
        self.task_input.setMaximumHeight(80)
        layout.addWidget(self.task_input)
        
        # Research group
        group_label = QLabel("Research Group")
        group_label.setStyleSheet("color: #666;")
        layout.addWidget(group_label)
        
        self.group_combo = QComboBox()
        self.group_combo.addItem("Loading groups...", None)
        layout.addWidget(self.group_combo)
        
        # Time pickers
        time_layout = QHBoxLayout()
        
        start_layout = QVBoxLayout()
        start_label = QLabel("Start Time")
        start_label.setStyleSheet("color: #666;")
        start_layout.addWidget(start_label)
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        start_layout.addWidget(self.start_time)
        time_layout.addLayout(start_layout)
        
        end_layout = QVBoxLayout()
        end_label = QLabel("End Time")
        end_label.setStyleSheet("color: #666;")
        end_layout.addWidget(end_label)
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        end_layout.addWidget(self.end_time)
        time_layout.addLayout(end_layout)
        
        layout.addLayout(time_layout)
        
        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red;")
        self.error_label.hide()
        layout.addWidget(self.error_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.submit_btn = QPushButton("Submit")
        self.submit_btn.setDefault(True)
        self.submit_btn.clicked.connect(self.submit_entry)
        self.submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                padding: 6px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        button_layout.addWidget(self.submit_btn)
        
        layout.addLayout(button_layout)
        
        # Set default times
        self.reset_form()
    
    def reset_form(self):
        """Reset the form to default values."""
        now = datetime.now()
        interval = self.settings_manager.prompt_interval_minutes
        start = now - timedelta(minutes=interval)
        
        self.start_time.setTime(QTime(start.hour, start.minute))
        self.end_time.setTime(QTime(now.hour, now.minute))
        self.task_input.clear()
        self.error_label.hide()
        
        # Set default group if configured
        default_id = self.settings_manager.default_group_id
        if default_id is not None:
            for i in range(self.group_combo.count()):
                if self.group_combo.itemData(i) == default_id:
                    self.group_combo.setCurrentIndex(i)
                    break
    
    def load_groups(self):
        """Load research groups from the API."""
        self.group_combo.clear()
        
        try:
            self.groups = self.api_client.fetch_groups()
            
            if not self.groups:
                self.group_combo.addItem("No groups available", None)
            else:
                self.group_combo.addItem("Select a group", None)
                for group in self.groups:
                    self.group_combo.addItem(group.name, group.id)
                
                # Set default group
                default_id = self.settings_manager.default_group_id
                if default_id is not None:
                    for i in range(self.group_combo.count()):
                        if self.group_combo.itemData(i) == default_id:
                            self.group_combo.setCurrentIndex(i)
                            break
        except Exception as e:
            self.group_combo.addItem("Failed to load groups", None)
            self.error_label.setText(str(e))
            self.error_label.show()
    
    def submit_entry(self):
        """Submit the time entry."""
        task = self.task_input.toPlainText().strip()
        group_id = self.group_combo.currentData()
        
        # Validation
        if not task:
            self.error_label.setText("Task description is required")
            self.error_label.show()
            return
        
        if group_id is None:
            self.error_label.setText("Please select a research group")
            self.error_label.show()
            return
        
        start = self.start_time.time().toString("HH:mm")
        end = self.end_time.time().toString("HH:mm")
        
        # Disable UI during submission
        self.submit_btn.setEnabled(False)
        self.submit_btn.setText("Submitting...")
        self.error_label.hide()
        
        # Submit in background thread
        self.worker = SubmitWorker(
            self.api_client, group_id, task, start, end
        )
        self.worker.finished.connect(self.on_submit_finished)
        self.worker.start()
    
    def on_submit_finished(self, result):
        """Handle submission result."""
        self.submit_btn.setEnabled(True)
        self.submit_btn.setText("Submit")
        
        if isinstance(result, Exception):
            self.error_label.setText(f"Failed to save: {result}")
            self.error_label.show()
        else:
            # Success - show notification and close
            QMessageBox.information(
                self,
                "Entry Saved",
                f"Logged {result.total_hours:.2f} hours for:\n{result.task_description[:50]}..."
            )
            self.accept()
    
    def showEvent(self, event):
        """Called when dialog is shown."""
        super().showEvent(event)
        self.reset_form()
        self.load_groups()
        self.task_input.setFocus()
