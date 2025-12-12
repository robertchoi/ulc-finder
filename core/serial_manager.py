"""
Serial Port Manager
Handles serial port communication with CCID reader
"""

import serial
import serial.tools.list_ports
from typing import List, Optional
import time


class SerialManager:
    """Manages serial port communication"""

    def __init__(self, baudrate: int = 57600, timeout: float = 1.0):
        """
        Initialize serial manager

        Args:
            baudrate: Baud rate (default: 57600)
            timeout: Read timeout in seconds (default: 1.0)
        """
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_port: Optional[serial.Serial] = None
        self.is_connected = False

    @staticmethod
    def list_ports() -> List[str]:
        """
        List available COM ports

        Returns:
            List of port names (e.g., ['COM1', 'COM3'])
        """
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def connect(self, port: str) -> bool:
        """
        Connect to serial port

        Args:
            port: Port name (e.g., 'COM3')

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.is_connected:
                self.disconnect()

            print(f"Attempting to connect to {port}...")
            print(f"Settings: {self.baudrate} baud, 8N1, timeout={self.timeout}s")

            self.serial_port = serial.Serial(
                port=port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                write_timeout=self.timeout,
                xonxoff=False,  # Disable software flow control
                rtscts=False,   # Disable hardware flow control
                dsrdtr=False    # Disable DSR/DTR flow control
            )

            # Verify port is open
            if not self.serial_port.is_open:
                print(f"Failed to open {port}")
                return False

            self.is_connected = True

            # Small delay for port to stabilize
            import time
            time.sleep(0.1)

            # Clear any pending data
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()

            print(f"Successfully connected to {port}")
            return True

        except serial.SerialException as e:
            print(f"Serial port error: {e}")
            if "PermissionError" in str(e) or "Access is denied" in str(e):
                print("Port is already in use by another application")
            elif "FileNotFoundError" in str(e) or "could not open port" in str(e):
                print("Port does not exist or was disconnected")
            self.is_connected = False
            return False
        except Exception as e:
            print(f"Unexpected connection error: {type(e).__name__}: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Disconnect from serial port"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.is_connected = False
        self.serial_port = None

    def send(self, data: bytes) -> bool:
        """
        Send data to serial port

        Args:
            data: Bytes to send

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected or not self.serial_port:
            return False

        try:
            self.serial_port.write(data)
            self.serial_port.flush()
            return True

        except Exception as e:
            print(f"Send error: {e}")
            return False

    def receive(self, expected_length: Optional[int] = None, timeout: Optional[float] = None) -> Optional[bytes]:
        """
        Receive data from serial port (with framing: STX + CCID + ETX + CHECKSUM)

        Args:
            expected_length: Expected number of bytes (None = read what's available)
            timeout: Override default timeout (seconds)

        Returns:
            Received bytes or None if error/timeout
        """
        if not self.is_connected or not self.serial_port:
            print("[RX] Not connected or no serial port")
            return None

        try:
            # Set temporary timeout if provided
            original_timeout = self.serial_port.timeout
            if timeout is not None:
                self.serial_port.timeout = timeout

            # Check how many bytes are waiting
            waiting = self.serial_port.in_waiting
            print(f"[RX] Bytes waiting in buffer: {waiting}")

            if expected_length:
                # Read exact number of bytes
                data = self.serial_port.read(expected_length)
                print(f"[RX] Read {len(data)} bytes (expected {expected_length})")
            else:
                # Read framed message: STX + CCID + ETX + CHECKSUM
                # First, read STX
                print("[RX] Reading STX...")
                stx = self.serial_port.read(1)
                if len(stx) != 1:
                    print(f"[RX] No STX received")
                    return None

                if stx[0] != 0x02:
                    print(f"[RX] Invalid STX: 0x{stx[0]:02X}")
                    return None

                print(f"[RX] STX received: 0x{stx[0]:02X}")

                # Read CCID header (10 bytes after STX)
                print("[RX] Reading 10-byte CCID header...")
                ccid_header = self.serial_port.read(10)
                print(f"[RX] CCID header received: {len(ccid_header)} bytes")

                if len(ccid_header) < 10:
                    print(f"[RX] Incomplete CCID header (got {len(ccid_header)}/10 bytes)")
                    if len(ccid_header) > 0:
                        print(f"[RX] Partial data: {' '.join(f'{b:02X}' for b in ccid_header)}")
                    return None

                # Parse dwLength from CCID header (bytes 1-4, little-endian)
                # Note: ccid_header[0] is bMessageType, ccid_header[1:5] is dwLength
                dw_length = int.from_bytes(ccid_header[1:5], byteorder='little')
                print(f"[RX] Payload length from CCID header: {dw_length} bytes")

                # Read CCID payload if any
                if dw_length > 0:
                    print(f"[RX] Reading {dw_length} bytes CCID payload...")
                    ccid_payload = self.serial_port.read(dw_length)
                    print(f"[RX] CCID payload received: {len(ccid_payload)} bytes")
                else:
                    ccid_payload = b''

                # Read ETX (1 byte)
                print("[RX] Reading ETX...")
                etx = self.serial_port.read(1)
                if len(etx) != 1:
                    print(f"[RX] No ETX received")
                    return None

                print(f"[RX] ETX received: 0x{etx[0]:02X}")

                # Read checksum (1 byte)
                print("[RX] Reading checksum...")
                checksum = self.serial_port.read(1)
                if len(checksum) != 1:
                    print(f"[RX] No checksum received")
                    return None

                print(f"[RX] Checksum received: 0x{checksum[0]:02X}")

                # Assemble complete framed message
                data = stx + ccid_header + ccid_payload + etx + checksum
                print(f"[RX] Total framed message: {len(data)} bytes")

            # Restore original timeout
            if timeout is not None:
                self.serial_port.timeout = original_timeout

            return data if len(data) > 0 else None

        except Exception as e:
            print(f"[RX] Receive error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def send_receive(self, data: bytes, timeout: Optional[float] = None) -> Optional[bytes]:
        """
        Send data and wait for response

        Args:
            data: Bytes to send
            timeout: Receive timeout (seconds)

        Returns:
            Response bytes or None if error/timeout
        """
        if not self.send(data):
            return None

        # Small delay to ensure data is processed
        time.sleep(0.01)

        return self.receive(timeout=timeout)

    def get_port_info(self) -> dict:
        """
        Get current port information

        Returns:
            Dict with port info
        """
        if not self.serial_port:
            return {}

        return {
            'port': self.serial_port.port,
            'baudrate': self.serial_port.baudrate,
            'bytesize': self.serial_port.bytesize,
            'parity': self.serial_port.parity,
            'stopbits': self.serial_port.stopbits,
            'timeout': self.serial_port.timeout,
            'is_open': self.serial_port.is_open
        }

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
