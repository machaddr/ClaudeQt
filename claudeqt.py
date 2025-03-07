#!/usr/bin/env python   

import sys
import anthropic
import re
import markdown
import speech_recognition as sr
import pyaudio
from PyQt6 import QtCore, QtGui, QtWidgets


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
                max_tokens=4096,
                temperature=0.7
            )
            self.response_received.emit(response.content[0].text)
        except Exception as e:
            self.response_received.emit(f"Error: {e}")

class ClaudeAIWidget(QtWidgets.QWidget):
    def closeEvent(self, event):
        if self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()
        event.accept()
        
    def __init__(self):
        super().__init__()
        
        # Set minimum window size
        self.setMinimumSize(800, 640)
    
        # Set window title
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
        
        # Set font size and type
        font = QtGui.QFont("Monospace")
        font.setPointSize(12)
        self.output_window.setFont(font)
        
        self.output_window.setReadOnly(True)        
        self.layout.addWidget(self.output_window)

        # Input field and send button layout
        input_layout = QtWidgets.QHBoxLayout()

        self.input_field = QtWidgets.QLineEdit(self)
        input_layout.addWidget(self.input_field)
        
        # Add a microphone button to trigger voice input
        self.microphone_button = QtWidgets.QPushButton("Mic", self)
        self.microphone_button.clicked.connect(self.toggle_voice_input)
        self.is_listening = False  # Flag to track voice input state
        input_layout.addWidget(self.microphone_button)
        
        # Add a send button to send the input
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
        
        # Set size of AI prompt widget
        self.setFixedWidth(int(0.25 * QtWidgets.QApplication.primaryScreen().size().width()))
        
        # Try to import markdown library
        try:
            self.markdown_module = markdown
        except ImportError:
            self.markdown_module = None
            
    def toggle_voice_input(self):
        if self.is_listening:
            self.stop_listening()
        else:
            self.start_listening()
            
    def start_listening(self):
        self.is_listening = True
        self.microphone_button.setStyleSheet("background-color: red;")
        self.microphone_button.setText("Stop")
        self.input_field.setPlaceholderText("Listening...")
        
        try:
            # Initialize PyAudio explicitly first
            self.audio = pyaudio.PyAudio()
            
            # Start listening for voice input
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            
            # Set up listening in background
            self.stop_listening_callback = self.recognizer.listen_in_background(
                self.microphone, self.process_voice_input)
                
        except Exception as e:
            self.is_listening = False
            self.microphone_button.setStyleSheet("")
            self.microphone_button.setText("Mic")
            self.input_field.setPlaceholderText("")
            
            # Show error message
            QtWidgets.QMessageBox.warning(
                self, 
                "Microphone Error", 
                f"Could not initialize microphone: {str(e)}\n\n"
                "Make sure your microphone is connected and that the application "
                "has permission to access it."
            )
            
    def stop_listening(self):
        self.is_listening = False
        self.microphone_button.setStyleSheet("")
        self.microphone_button.setText("Mic")
        self.input_field.setPlaceholderText("")
        
        # First, stop the background listening and wait for it to complete
        # This ensures the thread isn't still using the resources we're about to clean up
        if hasattr(self, 'stop_listening_callback'):
            try:
                # Wait for the callback to stop properly
                self.stop_listening_callback(wait_for_stop=True)
            except Exception:
                pass
            finally:
                # Remove the reference
                if hasattr(self, 'stop_listening_callback'):
                    del self.stop_listening_callback
        
        # Give a short delay to ensure threads have stopped
        QtCore.QThread.msleep(100)
        
        # Clean up microphone (which will also clean up its stream)
        if hasattr(self, 'microphone'):
            try:
                self.microphone.__exit__(None, None, None)
            except Exception:
                pass
            finally:
                if hasattr(self, 'microphone'):
                    del self.microphone
        
        # Clean up PyAudio last, after all streams are closed
        if hasattr(self, 'audio'):
            try:
                self.audio.terminate()
            except Exception as e:
                # Show error message only if termination fails
                QtWidgets.QMessageBox.warning(
                    self, 
                    "Microphone Error", 
                    f"Could not properly close microphone: {str(e)}\n\n"
                    "Make sure your microphone is connected and that the application "
                    "has permission to access it."
                )
            finally:
                if hasattr(self, 'audio'):
                    del self.audio
                self.input_field.setPlaceholderText("")
        
    def process_voice_input(self, recognizer, audio):
        try:
            user_input = recognizer.recognize_google(audio)
            self.input_field.setText(user_input)
            self.send_request()
        except sr.UnknownValueError:
            pass
        except sr.RequestError:
            pass        

    def send_request(self):
        user_input = str(self.input_field.text())
        if user_input.strip() == "/clear":
            self.output_window.clear()
        else:
            self.worker.user_input = user_input
            self.worker.start()
        self.input_field.clear()

    def format_markdown(self, text):
        """
        Convert markdown text to HTML using a markdown transpiler.
        Uses the markdown library if available, otherwise falls back to basic formatter.
        """
        if self.markdown_module:
            try:
                # Convert markdown to HTML with code highlighting
                html = self.markdown_module.markdown(text, extensions=['fenced_code'])
                return html
            except:
                pass  # Fall back to basic formatter on error
        
        # Fallback to basic formatter
        return self.format_markdown_code_blocks(text)

    def format_markdown_code_blocks(self, text):
        # Detect code fences and wrap them in HTML for better readability
        pattern = r'```(.*?)\n(.*?)´´´'
        def replacer(match):
            lang = match.group(1).strip()
            code_text = match.group(2).replace('<', '&lt;').replace('>', '&gt;')
            if lang and lang.lower() == 'python':
                # Python code
                return f"<pre><code style='color: #0000AA;'>{code_text}</code></pre>"
            else:
                # No specified language
                return f"<pre><code>{code_text}</code></pre>"
        
        # Process code blocks
        processed_text = re.sub(pattern, replacer, text, flags=re.DOTALL)
        
        # Process headers (# Header)
        processed_text = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', processed_text, flags=re.MULTILINE)
        processed_text = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', processed_text, flags=re.MULTILINE)
        processed_text = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', processed_text, flags=re.MULTILINE)
        
        # Process bullet lists
        processed_text = re.sub(r'^\*\s+(.+)$', r'<li>\1</li>', processed_text, flags=re.MULTILINE)
        processed_text = re.sub(r'^-\s+(.+)$', r'<li>\1</li>', processed_text, flags=re.MULTILINE)
        
        # Process numbered lists
        processed_text = re.sub(r'^\d+\.\s+(.+)$', r'<li>\1</li>', processed_text, flags=re.MULTILINE)
        
        # Process bold (**text**)
        processed_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', processed_text)
        
        # Process italic (*text*)
        processed_text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', processed_text)
        
        # Process links [text](url)
        processed_text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', processed_text)
        
        # Add paragraph breaks
        processed_text = re.sub(r'\n\n+', r'<br><br>', processed_text)
        
        return processed_text

    def update_output(self, response):
        user_input = self.worker.user_input
        formatted_response = self.format_markdown(response)
        self.output_window.append(
            f"<span style='color: red; font-weight: bold;'>Human:</span> {user_input}<br><br>"
            f"<span style='color: blue; font-weight: bold;'>Assistant:</span> {formatted_response}<br>"
        )

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    widget = ClaudeAIWidget()
    widget.show()
    sys.exit(app.exec())
    