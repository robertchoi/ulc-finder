"""
Main Window GUI for ULC Finder
"""

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QGroupBox, QLabel, QComboBox, QPushButton,
                              QPlainTextEdit, QProgressBar, QMessageBox,
                              QProgressDialog, QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.serial_manager import SerialManager
from core.ulc_scanner import ULCScanner, ScanResult
from core.key_generator import KeyGenerator, generate_random_key, DEFAULT_MANUFACTURER_KEY
import time


class ScanWorker(QThread):
    """Background worker thread for scanning"""

    progress_update = pyqtSignal(float, int, bytes)  # progress%, attempts, current_key
    key_found = pyqtSignal(bytes)  # found_key
    scan_complete = pyqtSignal(bool, str)  # success, message
    error_occurred = pyqtSignal(str)  # error_message

    def __init__(self, scanner: ULCScanner, start_key: bytes):
        super().__init__()
        self.scanner = scanner
        self.start_key = start_key
        self.result: Optional[ScanResult] = None

    def run(self):
        """Run scan in background thread"""
        # Set up callbacks
        self.scanner.on_progress = self._on_progress
        self.scanner.on_key_found = self._on_key_found
        self.scanner.on_error = self._on_error

        # Start scan
        self.result = self.scanner.start_scan(self.start_key)

        # Emit completion signal
        self.scan_complete.emit(self.result.success, self.result.message)

    def _on_progress(self, progress: float, attempts: int, current_key: bytes):
        """Progress callback"""
        self.progress_update.emit(progress, attempts, current_key)

    def _on_key_found(self, key: bytes):
        """Key found callback"""
        self.key_found.emit(key)

    def _on_error(self, message: str):
        """Error callback"""
        self.error_occurred.emit(message)

    def stop(self):
        """Stop scanning"""
        self.scanner.stop_scan()


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ULC Finder - 인증 키 검색")
        self.setGeometry(100, 100, 650, 700)

        # Components
        self.serial_manager = SerialManager(baudrate=57600, timeout=1.0)
        self.scanner: Optional[ULCScanner] = None
        self.scan_worker: Optional[ScanWorker] = None

        # Stats
        self.start_time: Optional[float] = None
        self.scan_speed: float = 0.0  # keys per second

        # Setup UI
        self._init_ui()

        # Populate COM ports
        self._refresh_ports()

    def _init_ui(self):
        """Initialize UI components"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Connection Group
        connection_group = self._create_connection_group()
        main_layout.addWidget(connection_group)

        # Scan Settings Group
        scan_group = self._create_scan_group()
        main_layout.addWidget(scan_group)

        # Result Group
        result_group = self._create_result_group()
        main_layout.addWidget(result_group)

        # Progress Group
        progress_group = self._create_progress_group()
        main_layout.addWidget(progress_group)

        main_layout.addStretch()

    def _create_connection_group(self) -> QGroupBox:
        """Create connection settings group"""
        group = QGroupBox("연결 설정")
        layout = QVBoxLayout()

        # Port selection row
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("COM Port:"))

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        port_layout.addWidget(self.port_combo)

        self.refresh_btn = QPushButton("새로고침")
        self.refresh_btn.clicked.connect(self._refresh_ports)
        port_layout.addWidget(self.refresh_btn)

        self.connect_btn = QPushButton("연결")
        self.connect_btn.clicked.connect(self._connect)
        port_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("해제")
        self.disconnect_btn.clicked.connect(self._disconnect)
        self.disconnect_btn.setEnabled(False)
        port_layout.addWidget(self.disconnect_btn)

        port_layout.addStretch()
        layout.addLayout(port_layout)

        # Status row
        self.status_label = QLabel("상태: ● 연결 안 됨  |  57600 8N1")
        self.status_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
        layout.addWidget(self.status_label)

        group.setLayout(layout)
        return group

    def _create_scan_group(self) -> QGroupBox:
        """Create scan settings group"""
        group = QGroupBox("키 스캔 설정")
        layout = QVBoxLayout()

        # Default key input (for authentication when writing keys)
        layout.addWidget(QLabel("디폴트 키 (Hex):"))

        font = QFont("Courier New", 10)
        self.default_key_edit = QPlainTextEdit()
        # Set default manufacturer key: "!NACUOYFIEMKAERB" = "BREAKMEIFYOUCAN!" reversed
        default_key_hex = ' '.join(f'{b:02X}' for b in DEFAULT_MANUFACTURER_KEY)
        self.default_key_edit.setPlainText(default_key_hex)
        self.default_key_edit.setMaximumHeight(60)
        self.default_key_edit.setFont(font)
        layout.addWidget(self.default_key_edit)

        # Start key input
        layout.addWidget(QLabel("시작 키 (Hex):"))

        self.start_key_edit = QPlainTextEdit()
        self.start_key_edit.setPlainText("00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00")
        self.start_key_edit.setMaximumHeight(60)
        self.start_key_edit.setFont(font)
        layout.addWidget(self.start_key_edit)

        # Buttons row 1: Start and Stop
        btn_layout1 = QHBoxLayout()

        self.start_btn = QPushButton("시작")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._start_scan)
        self.start_btn.setStyleSheet("QPushButton { font-size: 14px; padding: 8px; }")
        btn_layout1.addWidget(self.start_btn)

        self.stop_btn = QPushButton("정지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_scan)
        self.stop_btn.setStyleSheet("QPushButton { font-size: 14px; padding: 8px; }")
        btn_layout1.addWidget(self.stop_btn)

        btn_layout1.addStretch()
        layout.addLayout(btn_layout1)

        # Buttons row 2: Generate Key and Write Key
        btn_layout2 = QHBoxLayout()

        self.generate_key_btn = QPushButton("랜덤 인증키 발급")
        self.generate_key_btn.clicked.connect(self._generate_random_key)
        self.generate_key_btn.setStyleSheet("QPushButton { font-size: 12px; padding: 6px; background-color: #4CAF50; color: white; }")
        btn_layout2.addWidget(self.generate_key_btn)

        self.write_key_btn = QPushButton("카드에 인증키 쓰기")
        self.write_key_btn.setEnabled(False)
        self.write_key_btn.clicked.connect(self._write_key_to_card)
        self.write_key_btn.setStyleSheet("QPushButton { font-size: 12px; padding: 6px; background-color: #FF5722; color: white; }")
        btn_layout2.addWidget(self.write_key_btn)

        btn_layout2.addStretch()
        layout.addLayout(btn_layout2)

        group.setLayout(layout)
        return group

    def _create_result_group(self) -> QGroupBox:
        """Create result display group"""
        group = QGroupBox("결과")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("발견된 키 (Hex):"))

        self.result_edit = QPlainTextEdit()
        self.result_edit.setPlainText("")
        self.result_edit.setReadOnly(True)
        self.result_edit.setMaximumHeight(60)
        font = QFont("Courier New", 10)
        self.result_edit.setFont(font)
        self.result_edit.setStyleSheet("QPlainTextEdit { background-color: #f0f0f0; }")
        layout.addWidget(self.result_edit)

        group.setLayout(layout)
        return group

    def _create_progress_group(self) -> QGroupBox:
        """Create progress display group"""
        group = QGroupBox("진행 상태")
        layout = QVBoxLayout()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 10000)  # 0.01% precision
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        # Stats
        self.stats_label = QLabel("시도: 0 / -\n속도: 0.0 keys/sec  |  예상 시간: -\n상태: 대기 중")
        self.stats_label.setStyleSheet("QLabel { font-family: 'Courier New'; }")
        layout.addWidget(self.stats_label)

        group.setLayout(layout)
        return group

    # ========== Slot Handlers ==========

    def _refresh_ports(self):
        """Refresh COM port list"""
        self.port_combo.clear()
        ports = SerialManager.list_ports()
        if ports:
            self.port_combo.addItems(ports)
        else:
            self.port_combo.addItem("No ports found")

    def _connect(self):
        """Connect to selected port"""
        port = self.port_combo.currentText()
        if "No ports" in port:
            QMessageBox.warning(self, "연결 오류", "사용 가능한 포트가 없습니다.")
            return

        print(f"\n=== Connecting to {port} ===")

        # Try to connect
        if self.serial_manager.connect(port):
            print("Serial port opened successfully")
            self.scanner = ULCScanner(self.serial_manager)

            # Connection successful - enable scan
            self.status_label.setText(f"상태: ● 연결됨 ({port})  |  57600 8N1")
            self.status_label.setStyleSheet("QLabel { color: green; font-weight: bold; }")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.start_btn.setEnabled(True)
            self.write_key_btn.setEnabled(True)
            QMessageBox.information(self, "연결 성공", f"{port}에 연결되었습니다.")
        else:
            print("Failed to open serial port")
            error_msg = f"{port} 연결에 실패했습니다.\n\n"
            error_msg += "확인사항:\n"
            error_msg += "- 다른 프로그램에서 포트를 사용 중인지 확인\n"
            error_msg += "- USB 케이블이 올바르게 연결되어 있는지 확인\n"
            error_msg += "- 드라이버가 설치되어 있는지 확인\n"
            error_msg += "- 장치 관리자에서 포트 상태 확인"
            QMessageBox.critical(self, "연결 오류", error_msg)

    def _disconnect(self):
        """Disconnect from port"""
        self.serial_manager.disconnect()
        self.scanner = None
        self.status_label.setText("상태: ● 연결 안 됨  |  57600 8N1")
        self.status_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.write_key_btn.setEnabled(False)

    def _start_scan(self):
        """Start key scanning"""
        # Parse start key
        try:
            hex_str = self.start_key_edit.toPlainText()
            start_key = KeyGenerator.parse_key(hex_str)
        except ValueError as e:
            QMessageBox.critical(self, "입력 오류", f"시작 키 형식이 잘못되었습니다:\n{e}")
            return

        # Clear result
        self.result_edit.setPlainText("")
        self.progress_bar.setValue(0)

        # Disable/enable buttons
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.write_key_btn.setEnabled(False)

        # Start time
        self.start_time = time.time()

        # Create and start worker thread
        self.scan_worker = ScanWorker(self.scanner, start_key)
        self.scan_worker.progress_update.connect(self._on_progress_update)
        self.scan_worker.key_found.connect(self._on_key_found)
        self.scan_worker.scan_complete.connect(self._on_scan_complete)
        self.scan_worker.error_occurred.connect(self._on_error)
        self.scan_worker.start()

    def _stop_scan(self):
        """Stop scanning"""
        if self.scan_worker:
            self.scan_worker.stop()
            self.scan_worker.wait()

    def _generate_random_key(self):
        """Generate and display a random 16-byte authentication key"""
        # Generate cryptographically secure random key
        random_key = generate_random_key()

        # Format as hex with spaces
        key_hex = ' '.join(f'{b:02X}' for b in random_key)

        # Display in start key field
        self.start_key_edit.setPlainText(key_hex)

        # Show confirmation message
        msg = f"새로운 랜덤 인증키가 생성되었습니다:\n\n{key_hex}\n\n"
        msg += "이 키를 안전한 곳에 백업하세요.\n"
        msg += "'카드에 인증키 쓰기' 버튼을 눌러 카드에 기록할 수 있습니다."
        QMessageBox.information(self, "인증키 발급 완료", msg)

    def _write_key_to_card(self):
        """Write authentication key to ULC card"""
        # Parse new key from start key input field
        try:
            hex_str = self.start_key_edit.toPlainText()
            key = KeyGenerator.parse_key(hex_str)
        except ValueError as e:
            QMessageBox.critical(self, "입력 오류", f"새 키 형식이 잘못되었습니다:\n{e}")
            return

        # Parse auth key from default key input field
        try:
            auth_hex_str = self.default_key_edit.toPlainText()
            auth_key = KeyGenerator.parse_key(auth_hex_str)
        except ValueError as e:
            QMessageBox.critical(self, "입력 오류", f"디폴트 키 형식이 잘못되었습니다:\n{e}")
            return

        # Disable buttons during write
        self.write_key_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(False)

        # Progress dialog
        progress = QProgressDialog("카드에 키를 쓰는 중...", "취소", 0, 0, self)
        progress.setWindowTitle("인증키 쓰기")
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)  # No cancel button
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()

        def update_progress(message: str):
            """Update progress dialog"""
            progress.setLabelText(message)
            QApplication.processEvents()

        # Write key to card (use default key for authentication)
        success, message = self.scanner.write_key_to_card(key, auth_key=auth_key, callback=update_progress)

        progress.close()

        # Show result message
        if not success:
            QMessageBox.critical(self, "인증키 쓰기 실패", f"인증키 쓰기에 실패했습니다.\n\n{message}")

        # Re-enable buttons
        self.write_key_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(True)

    def _on_progress_update(self, progress: float, attempts: int, current_key: bytes):
        """Handle progress update"""
        # Update progress bar
        self.progress_bar.setValue(int(progress * 100))

        # Calculate speed
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                self.scan_speed = attempts / elapsed

                # Estimate remaining time
                total_keys = 2 ** 128
                remaining_keys = total_keys - attempts
                if self.scan_speed > 0:
                    remaining_seconds = remaining_keys / self.scan_speed
                    remaining_str = self._format_time(remaining_seconds)
                else:
                    remaining_str = "-"
            else:
                remaining_str = "-"
        else:
            remaining_str = "-"

        # Format current key
        key_hex = ' '.join(f'{b:02X}' for b in current_key)

        # Update stats
        stats_text = f"시도: {attempts:,} / {2**128}\n"
        stats_text += f"속도: {self.scan_speed:.1f} keys/sec  |  예상 시간: {remaining_str}\n"
        # Show FULL key so user sees the changing bytes at the end
        stats_text += f"상태: 스캔 중... (현재 키: {key_hex})"
        self.stats_label.setText(stats_text)

    def _on_key_found(self, key: bytes):
        """Handle key found"""
        print(f"DEBUG: _on_key_found called with {key.hex()}")
        key_hex = ' '.join(f'{b:02X}' for b in key)
        self.result_edit.setPlainText(key_hex)

        # Update stats
        self.stats_label.setText(self.stats_label.text().replace("스캔 중", "성공!"))

    def _on_scan_complete(self, success: bool, message: str):
        """Handle scan completion"""
        print(f"DEBUG: _on_scan_complete called. Success={success}, Message={message}")
        # Re-enable buttons
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.write_key_btn.setEnabled(True)

        # Show message
        if success:
            print("DEBUG: Showing Success MessageBox")
            QMessageBox.information(self, "스캔 완료", message)
            print("DEBUG: Success MessageBox closed")
        else:
            print("DEBUG: Showing Failure MessageBox")
            QMessageBox.information(self, "스캔 종료", message)
            print("DEBUG: Failure MessageBox closed")

    def _on_error(self, message: str):
        """Handle error"""
        print(f"Error: {message}")

        # Show popup for critical errors (Power ON failures)
        if "Power ON 실패" in message or "스캔을 중지" in message:
            print(f"DEBUG: Showing Critical Error MessageBox: {message}")
            QMessageBox.critical(self, "스캔 오류", message)
            print("DEBUG: Critical Error MessageBox closed")

    def _format_time(self, seconds: float) -> str:
        """Format seconds to human readable string"""
        if seconds < 60:
            return f"{int(seconds)}초"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes}분"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}시간 {minutes}분"
        else:
            days = int(seconds / 86400)
            hours = int((seconds % 86400) / 3600)
            return f"{days}일 {hours}시간"

    def closeEvent(self, event):
        """Handle window close"""
        if self.scan_worker and self.scan_worker.isRunning():
            reply = QMessageBox.question(
                self, '종료',
                '스캔이 진행 중입니다. 종료하시겠습니까?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self._stop_scan()
                self.serial_manager.disconnect()
                event.accept()
            else:
                event.ignore()
        else:
            self.serial_manager.disconnect()
            event.accept()
