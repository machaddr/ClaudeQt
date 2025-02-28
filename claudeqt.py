#!/usr/bin/env python   

import sys
from PyQt6 import QtCore, QtGui, QtWidgets
import anthropic

class ClaudeAIWorker(QtCore.QThread):
    response_received = QtCore.pyqtSignal(str)

    def __init__(self, user_input, parent=None):
        super().__init__(parent)
        self.user_input = user_input

    def run(self):
        api_key = "YOUR-CLAUDE-API"  # Store securely

        client = anthropic.Anthropic(api_key=api_key)

        try:
            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                messages=[
                    {"role": "user", "content": self.user_input}
                ],
                max_tokens=2048,
                temperature=0.7
            )
            self.response_received.emit(response.content[0].text)
        except Exception as e:
            self.response_received.emit(f"Error: {e}")

class ClaudeAIWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        
        self.setGeometry(100, 100, 800, 640)
        self.setWindowTitle("ClaudeQt")
        
        # Use a transparent pixmap
        transparent_pixmap = QtGui.QPixmap(1, 1)
        transparent_pixmap.fill()
        self.setWindowIcon(QtGui.QIcon(transparent_pixmap))

        # Set up the layout
        self.layout = QtWidgets.QVBoxLayout(self)

        # Output window (read-only)
        self.output_window = QtWidgets.QTextEdit(self)
        self.output_window.setStyleSheet("background-color: #FDF6E3; color: #657B83;")
        self.output_window.setReadOnly(True)        
        self.layout.addWidget(self.output_window)

        # Input field and send button layout
        input_layout = QtWidgets.QHBoxLayout()

        self.input_field = QtWidgets.QLineEdit(self)
        input_layout.addWidget(self.input_field)

        self.send_button = QtWidgets.QPushButton("Send", self)
        self.send_button.clicked.connect(self.send_request)
        input_layout.addWidget(self.send_button)

        self.layout.addLayout(input_layout)
        
        # Add a loading spinner while getting the response from Claude
        self.loading_spinner = QtWidgets.QProgressBar(self)
        self.loading_spinner.setRange(0, 0)  # Indeterminate progress
        self.layout.addWidget(self.loading_spinner)
        self.loading_spinner.hide()  # Hide initially

        # Initialize worker
        self.worker = ClaudeAIWorker("")
        self.worker.response_received.connect(self.update_output)

        # Connect signals to show and hide the loading spinner
        self.worker.started.connect(self.loading_spinner.show)
        self.worker.finished.connect(self.loading_spinner.hide)

        # Send request on pressing Enter
        self.input_field.returnPressed.connect(self.send_request)
        
        # Change output window font type and size to system font
        font = self.output_window.font()
        font.setFamily(QtGui.QFont().defaultFamily())
        font.setPointSize(QtGui.QFont().pointSize())
        self.output_window.setFont(font)
        
        # Change input field font type and size to system font
        font = self.input_field.font()
        font.setFamily(QtGui.QFont().defaultFamily())
        font.setPointSize(QtGui.QFont().pointSize())
        self.input_field.setFont(font)
        
        # Change send button font type and size to system font
        font = self.send_button.font()
        font.setFamily(QtGui.QFont().defaultFamily())
        font.setPointSize(QtGui.QFont().pointSize())
        self.send_button.setFont(font)
        
        # Set the layout
        self.setLayout(self.layout)        

    def send_request(self):
        user_input = str(self.input_field.text())
        if user_input.strip() == "/clear":
            self.output_window.clear()
        else:
            self.worker.user_input = user_input
            self.worker.start()
        self.input_field.clear()

    def update_output(self, response):
        user_input = self.worker.user_input
        self.output_window.append(f"<span style='color: red; font-weight: bold;'>Human:</span> {user_input}<br><br><span style='color: blue; font-weight: bold;'>Assistant:</span> {response}<br>")    

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    widget = ClaudeAIWidget()
    widget.show()
    sys.exit(app.exec())
    