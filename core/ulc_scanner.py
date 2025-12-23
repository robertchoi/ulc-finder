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
                print("[RX] No response received")
                print("[ERROR] Power ON failed - stopping scan")
                if self.on_error:
                    self.on_error("Power ON 실패: 응답 없음. 스캔을 중지합니다.")
                # Stop scanning on Power ON failure
                self.is_scanning = False
                return False

            print(f"[RX] Response ({len(response)} bytes): {' '.join(f'{b:02X}' for b in response)}")

            msg_type, status, error, payload = self.ccid.parse_response(response)
            print(f"     Message Type: 0x{msg_type:02X}, Status: 0x{status:02X}, Error: 0x{error:02X}")

            if not self.ccid.is_success(status, error):
                print(f"[WARNING] Power ON returned error status (0x{status:02X}, 0x{error:02X}) - attempting to proceed")
                if self.on_error:
                    self.on_error(f"Power ON 경고: status=0x{status:02X} error=0x{error:02X}. 계속 진행합니다.")
                # Continue to Get UID even if Power ON failed


            # Small delay
            time.sleep(0.05)

            # Step 2: Get UID
            cmd = self.ccid.get_uid()
            print(f"[TX] Get UID: {' '.join(f'{b:02X}' for b in cmd)}")
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
            else:
                # Log the UID
                if len(payload) >= 2:
                    uid_bytes = payload[:-2] # Remove SW1 SW2
                    uid_str = ' '.join(f'{b:02X}' for b in uid_bytes)
                    print(f"[INFO] Card UID: {uid_str}")
                    if self.on_error: # Use on_error to send info to GUI log if needed, or just print
                        pass # GUI doesn't have a generic info callback yet, just print to console is fine for now

            # Small delay
            time.sleep(0.05)

            # Step 3: Load Key
            cmd = self.ccid.load_key(key, slot=3)
            print(f"[TX] Load Key: {' '.join(f'{b:02X}' for b in cmd)}")
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
            print(f"[TX] Authenticate: {' '.join(f'{b:02X}' for b in cmd)}")
            response = self.serial.send_receive(cmd, timeout=2.0)
            if not response:
                if self.on_error:
                    self.on_error("Authenticate: No response")
                return False

            msg_type, status, error, payload = self.ccid.parse_response(response)
            
            # Log Authenticate response for debugging
            if len(payload) > 0:
                print(f"[RX] Authenticate Response Payload: {' '.join(f'{b:02X}' for b in payload)}")
            else:
                print(f"[RX] Authenticate Response: Status=0x{status:02X} Error=0x{error:02X} (No Payload)")

            # Check if authentication successful
            if self.ccid.is_auth_success(status, error, payload):
                return True

            # Auth failed
            # print(f"DEBUG: Auth failed for key {key.hex()[:8]}... - Retrying next key")
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

    def write_key_to_card(self, key: bytes, auth_key: Optional[bytes] = None, callback: Optional[Callable] = None) -> tuple[bool, str]:
        """
        Write 16-byte authentication key to ULC card (Pages 44-47)

        IMPORTANT: This operation is IRREVERSIBLE (OTP - One Time Programmable)
        The key can only be written ONCE to a factory-fresh card.

        Args:
            key: 16-byte authentication key to write
            auth_key: 16-byte authentication key to use for card authentication (None = use default manufacturer key)
            callback: Optional callback for progress updates

        Returns:
            Tuple of (success: bool, message: str)
        """
        from datetime import datetime

        start_time = datetime.now()
        print(f"\n{'='*60}")
        print(f"[START] write_key_to_card - {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        print(f"[KEY] Length: {len(key)} bytes")
        print(f"[KEY] Hex: {' '.join(f'{b:02X}' for b in key)}")
        print(f"{'='*60}")

        if len(key) != 16:
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            print(f"\n{'='*60}")
            print(f"[END] write_key_to_card - {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            print(f"[DURATION] {elapsed:.3f} seconds (FAILED - Invalid key length)")
            print(f"[ERROR] Key must be exactly 16 bytes, got {len(key)} bytes")
            print(f"{'='*60}\n")
            return False, f"키는 정확히 16바이트여야 합니다 (현재: {len(key)}바이트)"

        try:
            self.ccid.reset_seq()

            # Step 1: Power ON
            if callback:
                callback("카드 전원 켜는 중...")
            cmd = self.ccid.power_on()
            print(f"[TX] Power ON: {' '.join(f'{b:02X}' for b in cmd)}")
            response = self.serial.send_receive(cmd, timeout=2.0)

            if not response:
                print("[ERROR] Power ON failed - no response")
                return False, "Power ON 실패: 응답 없음"

            msg_type, status, error, payload = self.ccid.parse_response(response)
            print(f"[RX] Power ON: Status=0x{status:02X}, Error=0x{error:02X}")

            # Check if Power ON succeeded
            if not self.ccid.is_success(status, error):
                print(f"[ERROR] Power ON failed - Status=0x{status:02X}, Error=0x{error:02X}")
                return False, f"Power ON 실패: Status=0x{status:02X}, Error=0x{error:02X}"

            time.sleep(0.1)

            # Step 2: Get UID (for verification)
            if callback:
                callback("카드 UID 읽는 중...")
            cmd = self.ccid.get_uid()
            response = self.serial.send_receive(cmd, timeout=1.0)

            if response:
                msg_type, status, error, payload = self.ccid.parse_response(response)
                if self.ccid.is_success(status, error) and len(payload) >= 2:
                    uid_bytes = payload[:-2]
                    uid_str = ' '.join(f'{b:02X}' for b in uid_bytes)
                    print(f"[INFO] Card UID: {uid_str}")

            time.sleep(0.1)

            # Step 3: Load authentication key to reader
            # Use the auth_key from GUI's default key input field (or default manufacturer key if not provided)
            if callback:
                callback("디폴트 인증키 로딩 중...")

            # Use auth_key if provided, otherwise use default manufacturer key
            if auth_key is None or len(auth_key) != 16:
                # Default manufacturer key: "BREAKMEIFYOUCAN!" reversed = "!NACUOYFIEMKAERB"
                # ASCII: ! N A C U O Y F I E M K A E R B
                # Hex:  49 45 4D 4B 41 45 52 42 21 4E 41 43 55 4F 59 46
                from .key_generator import DEFAULT_MANUFACTURER_KEY
                auth_key = DEFAULT_MANUFACTURER_KEY

            cmd = self.ccid.load_key(auth_key, slot=3)
            print(f"[TX] Load Default Key: {' '.join(f'{b:02X}' for b in auth_key)}")
            response = self.serial.send_receive(cmd, timeout=1.0)

            if not response:
                return False, "디폴트 키 로드 실패: 응답 없음"

            msg_type, status, error, payload = self.ccid.parse_response(response)
            print(f"[RX] Load Key: Status=0x{status:02X}, Error=0x{error:02X}")

            if not self.ccid.is_success(status, error):
                # Check if response has SW1 SW2
                if len(payload) >= 2:
                    sw1, sw2 = payload[0], payload[1]
                    if sw1 != 0x90 or sw2 != 0x00:
                        return False, f"디폴트 키 로드 실패: SW1={sw1:02X} SW2={sw2:02X}"

            time.sleep(0.1)

            # Step 4: Authenticate with default key
            if callback:
                callback("카드 인증 중...")

            cmd = self.ccid.authenticate(page=4, key_slot=3)
            print(f"[TX] Authenticate with default key")
            response = self.serial.send_receive(cmd, timeout=2.0)

            if not response:
                return False, "인증 실패: 응답 없음"

            msg_type, status, error, payload = self.ccid.parse_response(response)
            print(f"[RX] Authenticate: Status=0x{status:02X}, Error=0x{error:02X}")

            time.sleep(0.1)

            # Step 5: Load new key (to be written) to reader
            if callback:
                callback("새 인증키 로딩 중...")

            cmd = self.ccid.load_key(key, slot=3)
            print(f"[TX] Load New Key: {' '.join(f'{b:02X}' for b in key)}")
            response = self.serial.send_receive(cmd, timeout=1.0)

            if not response:
                return False, "새 키 로드 실패: 응답 없음"

            msg_type, status, error, payload = self.ccid.parse_response(response)
            print(f"[RX] Load New Key: Status=0x{status:02X}, Error=0x{error:02X}")

            if not self.ccid.is_success(status, error):
                # Check if response has SW1 SW2
                if len(payload) >= 2:
                    sw1, sw2 = payload[0], payload[1]
                    if sw1 != 0x90 or sw2 != 0x00:
                        return False, f"새 키 로드 실패: SW1={sw1:02X} SW2={sw2:02X}"

            time.sleep(0.1)

            # Step 6: Write authentication key to pages 44-47 using FF 87 command
            if callback:
                callback("카드에 인증키 쓰는 중...")

            print(f"[INFO] Writing 16-byte key to pages 44-47 using FF 87 command")

            cmd = self.ccid.write_auth_key()
            print(f"[TX] Write Auth Key (FF 87): {' '.join(f'{b:02X}' for b in cmd)}")
            response = self.serial.send_receive(cmd, timeout=2.0)

            if not response:
                return False, "인증키 쓰기 실패: 응답 없음"

            msg_type, status, error, payload = self.ccid.parse_response(response)
            print(f"[RX] Write Auth Key: Status=0x{status:02X}, Error=0x{error:02X}")
            if len(payload) > 0:
                print(f"[RX] Payload: {' '.join(f'{b:02X}' for b in payload)}")

            # Check for success
            if not self.ccid.is_success(status, error):
                if len(payload) >= 2:
                    sw1, sw2 = payload[0], payload[1]
                    if sw1 != 0x90 or sw2 != 0x00:
                        return False, f"인증키 쓰기 실패: SW1={sw1:02X} SW2={sw2:02X}"
                return False, f"인증키 쓰기 실패: Status=0x{status:02X} Error=0x{error:02X}"

            time.sleep(0.1)

            if callback:
                callback("키 쓰기 완료!")

            # Step 7: Power OFF
            if callback:
                callback("카드 전원 끄는 중...")

            cmd = self.ccid.power_off()
            print(f"[TX] Power OFF: {' '.join(f'{b:02X}' for b in cmd)}")
            response = self.serial.send_receive(cmd, timeout=2.0)

            if response:
                msg_type, status, error, payload = self.ccid.parse_response(response)
                print(f"[RX] Power OFF: Status=0x{status:02X}, Error=0x{error:02X}")

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            print(f"\n{'='*60}")
            print(f"[END] write_key_to_card - {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            print(f"[DURATION] {elapsed:.3f} seconds (SUCCESS)")
            print(f"{'='*60}\n")

            return True, "인증키가 성공적으로 카드에 기록되었습니다"

        except Exception as e:
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            print(f"\n{'='*60}")
            print(f"[END] write_key_to_card - {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            print(f"[DURATION] {elapsed:.3f} seconds (EXCEPTION)")
            print(f"[ERROR] {e}")
            print(f"{'='*60}\n")
            return False, f"키 쓰기 중 오류 발생: {e}"
