"""
ULC Scanner
Main scanning logic for finding ULC authentication keys
"""

from typing import Optional, Callable
import time
from .serial_manager import SerialManager
from .ccid_protocol import CCIDProtocol
from .key_generator import KeyGenerator


class ScanResult:
    """Scan result container"""

    def __init__(self, success: bool, key: Optional[bytes] = None,
                 attempts: int = 0, message: str = ""):
        self.success = success
        self.key = key
        self.attempts = attempts
        self.message = message


class ULCScanner:
    """ULC Key Scanner"""

    def __init__(self, serial_manager: SerialManager):
        """
        Initialize scanner

        Args:
            serial_manager: Serial port manager
        """
        self.serial = serial_manager
        self.ccid = CCIDProtocol()
        self.key_gen: Optional[KeyGenerator] = None
        self.is_scanning = False
        self.found_key: Optional[bytes] = None

        # Callbacks
        self.on_progress: Optional[Callable] = None
        self.on_key_found: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    def start_scan(self, start_key: bytes) -> ScanResult:
        """
        Start key scanning

        Args:
            start_key: 16-byte starting key

        Returns:
            ScanResult
        """
        self.key_gen = KeyGenerator(start_key)
        self.is_scanning = True
        self.found_key = None
        self.ccid.reset_seq()

        try:
            return self._scan_loop()
        except Exception as e:
            self.is_scanning = False
            return ScanResult(False, message=f"Scan error: {e}")

    def stop_scan(self):
        """Stop scanning"""
        self.is_scanning = False

    def _scan_loop(self) -> ScanResult:
        """
        Main scan loop

        Returns:
            ScanResult
        """
        while self.is_scanning:
            # Get current key
            current_key = self.key_gen.get_current_key()

            # Try to authenticate with current key
            auth_result = self._try_authenticate(current_key)

            if auth_result:
                # Success! Found the key
                self.found_key = current_key
                self.is_scanning = False

                if self.on_key_found:
                    self.on_key_found(current_key)

                return ScanResult(
                    success=True,
                    key=current_key,
                    attempts=self.key_gen.get_attempts(),
                    message="Key found!"
                )

            # Update progress
            if self.on_progress:
                progress = self.key_gen.calculate_progress()
                attempts = self.key_gen.get_attempts()
                self.on_progress(progress, attempts, current_key)

            # Increment key
            if not self.key_gen.increment():
                # Reached end (FF...FF)
                self.is_scanning = False
                return ScanResult(
                    success=False,
                    attempts=self.key_gen.get_attempts(),
                    message="Scan completed. Key not found."
                )

        # Stopped by user
        return ScanResult(
            success=False,
            attempts=self.key_gen.get_attempts(),
            message="Scan stopped by user."
        )

    def _try_authenticate(self, key: bytes) -> bool:
        """
        Try to authenticate with given key

        Scan sequence:
        1. Power ON
        2. Get UID
        3. Load Key
        4. Authenticate

        Args:
            key: 16-byte key to try

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Step 1: Power ON
            cmd = self.ccid.power_on()
            print(f"[TX] Power ON: {' '.join(f'{b:02X}' for b in cmd)}")
            response = self.serial.send_receive(cmd, timeout=2.0)

            if not response:
                if self.on_error:
                    self.on_error("Power ON: No response")
                print("[RX] No response received")
                return False

            print(f"[RX] Response ({len(response)} bytes): {' '.join(f'{b:02X}' for b in response)}")

            msg_type, status, error, payload = self.ccid.parse_response(response)
            print(f"     Message Type: 0x{msg_type:02X}, Status: 0x{status:02X}, Error: 0x{error:02X}")

            if not self.ccid.is_success(status, error):
                if self.on_error:
                    self.on_error(f"Power ON failed: status={status:02X} error={error:02X}")
                return False

            # Small delay
            time.sleep(0.05)

            # Step 2: Get UID
            cmd = self.ccid.get_uid()
            response = self.serial.send_receive(cmd, timeout=1.0)
            if not response:
                if self.on_error:
                    self.on_error("Get UID: No response")
                return False

            msg_type, status, error, payload = self.ccid.parse_response(response)
            if not self.ccid.is_success(status, error):
                if self.on_error:
                    self.on_error(f"Get UID failed: status={status:02X} error={error:02X}")
                # Continue anyway - UID not critical for auth

            # Small delay
            time.sleep(0.05)

            # Step 3: Load Key
            cmd = self.ccid.load_key(key, slot=3)
            response = self.serial.send_receive(cmd, timeout=1.0)
            if not response:
                if self.on_error:
                    self.on_error("Load Key: No response")
                return False

            msg_type, status, error, payload = self.ccid.parse_response(response)
            if not self.ccid.is_success(status, error):
                if self.on_error:
                    self.on_error(f"Load Key failed: status={status:02X} error={error:02X}")
                return False

            # Small delay
            time.sleep(0.05)

            # Step 4: Authenticate
            cmd = self.ccid.authenticate(page=4, key_slot=3)
            response = self.serial.send_receive(cmd, timeout=2.0)
            if not response:
                if self.on_error:
                    self.on_error("Authenticate: No response")
                return False

            msg_type, status, error, payload = self.ccid.parse_response(response)

            # Check if authentication successful
            if self.ccid.is_auth_success(status, error, payload):
                return True

            return False

        except Exception as e:
            if self.on_error:
                self.on_error(f"Authentication error: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Test connection to reader by sending Power ON command

        Returns:
            True if successful, False otherwise
        """
        try:
            self.ccid.reset_seq()
            cmd = self.ccid.power_on()
            response = self.serial.send_receive(cmd, timeout=2.0)

            if not response:
                return False

            msg_type, status, error, payload = self.ccid.parse_response(response)
            return self.ccid.is_success(status, error)

        except Exception:
            return False

    def get_card_uid(self) -> Optional[bytes]:
        """
        Get card UID

        Returns:
            UID bytes or None if error
        """
        try:
            cmd = self.ccid.get_uid()
            response = self.serial.send_receive(cmd, timeout=1.0)

            if not response:
                return None

            msg_type, status, error, payload = self.ccid.parse_response(response)

            if self.ccid.is_success(status, error) and len(payload) > 2:
                # Remove SW1 SW2 (last 2 bytes)
                uid = payload[:-2]
                return uid

            return None

        except Exception:
            return None
