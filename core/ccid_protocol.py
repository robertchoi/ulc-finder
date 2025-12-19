"""
CCID Protocol Handler
Handles CCID 1.1 protocol message construction and parsing
"""

import struct
from typing import List, Tuple, Optional


class CCIDMessage:
    """CCID Message Types"""
    # PC to Reader
    PC_TO_RDR_ICCPOWERON = 0x62
    PC_TO_RDR_ICCPOWEROFF = 0x63
    PC_TO_RDR_XFRBLOCK = 0x6F

    # Reader to PC
    RDR_TO_PC_DATABLOCK = 0x80
    RDR_TO_PC_SLOTSTATUS = 0x81


class CCIDProtocol:
    """CCID Protocol Handler for ULC Reader"""

    # Framing bytes
    STX = 0x02  # Start of Text
    ETX = 0x03  # End of Text

    def __init__(self):
        self.sequence = 1  # Start from 1, not 0

    def get_next_seq(self) -> int:
        """Get next sequence number and increment"""
        seq = self.sequence
        self.sequence = (self.sequence + 1) & 0xFF
        return seq

    def reset_seq(self):
        """Reset sequence number to 1"""
        self.sequence = 1  # Start from 1, not 0

    def _calculate_checksum(self, data: bytes) -> int:
        """
        Calculate XOR checksum for data

        Args:
            data: Bytes to calculate checksum for

        Returns:
            Checksum byte
        """
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum

    def _frame_message(self, ccid_message: bytes) -> bytes:
        """
        Add STX, ETX, and checksum framing to CCID message

        Args:
            ccid_message: Raw CCID message

        Returns:
            Framed message: STX + CCID + ETX + CHECKSUM
        """
        # Build CCID + ETX for checksum calculation (STX not included)
        data_for_checksum = bytearray(ccid_message)
        data_for_checksum.append(self.ETX)

        # Calculate checksum of CCID + ETX (excluding STX)
        checksum = self._calculate_checksum(data_for_checksum)

        # Build complete frame: STX + CCID + ETX + CHECKSUM
        framed = bytearray([self.STX])
        framed.extend(ccid_message)
        framed.append(self.ETX)
        framed.append(checksum)

        return bytes(framed)

    def _unframe_message(self, framed_data: bytes) -> bytes:
        """
        Remove STX, ETX, and checksum framing from message

        Args:
            framed_data: Framed message (STX + CCID + ETX + CHECKSUM)

        Returns:
            Raw CCID message
        """
        if len(framed_data) < 4:  # Minimum: STX + 1 byte + ETX + CHK
            raise ValueError(f"Framed message too short: {len(framed_data)} bytes")

        if framed_data[0] != self.STX:
            raise ValueError(f"Missing STX: first byte is 0x{framed_data[0]:02X}")

        # Find ETX (second to last byte)
        if framed_data[-2] != self.ETX:
            raise ValueError(f"Missing ETX: byte at -2 is 0x{framed_data[-2]:02X}")

        # Extract CCID message (between STX and ETX)
        ccid_message = framed_data[1:-2]

        # Verify checksum (checksum is calculated on CCID + ETX, excluding STX)
        data_for_checksum = framed_data[1:-1]  # CCID + ETX (skip STX and checksum)
        expected_checksum = self._calculate_checksum(data_for_checksum)
        actual_checksum = framed_data[-1]

        if expected_checksum != actual_checksum:
            print(f"[WARNING] Checksum mismatch: expected 0x{expected_checksum:02X}, got 0x{actual_checksum:02X}")

        return ccid_message

    # ========== Command Construction ==========

    def power_on(self) -> bytes:
        """
        Construct Power ON command
        Returns: Framed CCID message bytes
        """
        seq = self.get_next_seq()
        message = bytearray([
            CCIDMessage.PC_TO_RDR_ICCPOWERON,  # bMessageType
            0x00, 0x00, 0x00, 0x00,             # dwLength (0)
            0x00,                                # bSlot
            seq,                                 # bSeq
            0x00, 0x00, 0x00                    # bSpecific
        ])
        return self._frame_message(bytes(message))

    def power_off(self) -> bytes:
        """
        Construct Power OFF command
        Returns: Framed CCID message bytes
        """
        seq = self.get_next_seq()
        message = bytearray([
            CCIDMessage.PC_TO_RDR_ICCPOWEROFF,  # bMessageType
            0x00, 0x00, 0x00, 0x00,             # dwLength (0)
            0x00,                                # bSlot
            seq,                                 # bSeq
            0x00, 0x00, 0x00                    # bSpecific
        ])
        return self._frame_message(bytes(message))

    def get_uid(self) -> bytes:
        """
        Construct Get UID command (FF CA 00 00 00)
        Returns: Framed CCID message bytes
        """
        seq = self.get_next_seq()
        apdu = [0xFF, 0xCA, 0x00, 0x00, 0x00]

        message = bytearray([
            CCIDMessage.PC_TO_RDR_XFRBLOCK,     # bMessageType
            len(apdu), 0x00, 0x00, 0x00,        # dwLength
            0x00,                                # bSlot
            seq,                                 # bSeq
            0x00, 0x00, 0x00                    # bSpecific
        ])
        message.extend(apdu)
        return self._frame_message(bytes(message))

    def load_key(self, key_bytes: bytes, slot: int = 3) -> bytes:
        """
        Construct Load Authentication Key command (FF 82 00 slot Lc key)

        Args:
            key_bytes: 16-byte 3DES key
            slot: Key slot number (default: 3)

        Returns: Framed CCID message bytes
        """
        if len(key_bytes) != 16:
            raise ValueError("Key must be exactly 16 bytes")

        seq = self.get_next_seq()
        apdu = [0xFF, 0x82, 0x00, slot, 0x10]  # CLA INS P1 P2 Lc
        apdu.extend(key_bytes)

        message = bytearray([
            CCIDMessage.PC_TO_RDR_XFRBLOCK,     # bMessageType
            len(apdu), 0x00, 0x00, 0x00,        # dwLength
            0x00,                                # bSlot
            seq,                                 # bSeq
            0x00, 0x00, 0x00                    # bSpecific
        ])
        message.extend(apdu)
        return self._frame_message(bytes(message))

    def authenticate(self, page: int = 4, key_slot: int = 3) -> bytes:
        """
        Construct General Authenticate command (FF 86 00 00 05 01 00 page 60 slot)

        Args:
            page: Page number to authenticate (default: 4)
            key_slot: Key slot number (default: 3)

        Returns: Framed CCID message bytes
        """
        seq = self.get_next_seq()
        apdu = [
            0xFF, 0x86,              # CLA INS (GENERAL AUTHENTICATE)
            0x00, 0x00,              # P1 P2
            0x05,                    # Lc (5 bytes)
            0x01,                    # Version
            0x00,                    # Address MSB
            page,                    # Address LSB
            0x60,                    # Auth mode (0x60 = Key A for 3DES)
            key_slot                 # Key number
        ]

        message = bytearray([
            CCIDMessage.PC_TO_RDR_XFRBLOCK,     # bMessageType
            len(apdu), 0x00, 0x00, 0x00,        # dwLength
            0x00,                                # bSlot
            seq,                                 # bSeq
            0x00, 0x00, 0x00                    # bSpecific
        ])
        message.extend(apdu)
        return self._frame_message(bytes(message))

    def write_page(self, page: int, data: bytes) -> bytes:
        """
        Construct Write Page command (FF D6 00 page Lc data)

        Args:
            page: Page number to write (0x00-0x2F for ULC)
            data: 4 bytes to write to the page

        Returns: Framed CCID message bytes

        Raises:
            ValueError: If data is not exactly 4 bytes
        """
        if len(data) != 4:
            raise ValueError(f"Page data must be exactly 4 bytes, got {len(data)}")

        seq = self.get_next_seq()
        apdu = [
            0xFF, 0xD6,              # CLA INS (UPDATE BINARY)
            0x00, page,              # P1 P2 (page address)
            0x04                     # Lc (4 bytes)
        ]
        apdu.extend(data)

        message = bytearray([
            CCIDMessage.PC_TO_RDR_XFRBLOCK,     # bMessageType
            len(apdu), 0x00, 0x00, 0x00,        # dwLength
            0x00,                                # bSlot
            seq,                                 # bSeq
            0x00, 0x00, 0x00                    # bSpecific
        ])
        message.extend(apdu)
        return self._frame_message(bytes(message))

    def write_auth_key(self) -> bytes:
        """
        Construct Write Authentication Key command (FF 87 00 00 00)

        This command writes the previously loaded key to pages 44-47.
        The key must be loaded first using load_key().

        Returns: Framed CCID message bytes
        """
        seq = self.get_next_seq()
        apdu = [
            0xFF, 0x87,              # CLA INS (Write Authentication Key)
            0x00, 0x00,              # P1 P2
            0x00                     # Le (0 bytes expected)
        ]

        message = bytearray([
            CCIDMessage.PC_TO_RDR_XFRBLOCK,     # bMessageType
            len(apdu), 0x00, 0x00, 0x00,        # dwLength
            0x00,                                # bSlot
            seq,                                 # bSeq
            0x00, 0x00, 0x00                    # bSpecific
        ])
        message.extend(apdu)
        return self._frame_message(bytes(message))

    # ========== Response Parsing ==========

    def parse_response(self, data: bytes) -> Tuple[int, int, int, bytes]:
        """
        Parse CCID response message (with framing)

        Args:
            data: Framed response bytes (STX + CCID + ETX + CHECKSUM)

        Returns:
            Tuple of (bMessageType, bStatus, bError, payload)
        """
        # Remove framing first
        ccid_data = self._unframe_message(data)

        if len(ccid_data) < 10:
            raise ValueError(f"CCID response too short: {len(ccid_data)} bytes")

        bMessageType = ccid_data[0]
        dwLength = struct.unpack('<I', ccid_data[1:5])[0]
        bSlot = ccid_data[5]
        bSeq = ccid_data[6]
        bStatus = ccid_data[7]
        bError = ccid_data[8]
        bSpecific = ccid_data[9]

        payload = ccid_data[10:10+dwLength] if dwLength > 0 else b''

        return bMessageType, bStatus, bError, payload

    def is_success(self, bStatus: int, bError: int) -> bool:
        """
        Check if response indicates success

        Args:
            bStatus: Status byte from response
            bError: Error byte from response

        Returns:
            True if successful, False otherwise
        """
        return bStatus == 0x00 and bError == 0x00

    def is_auth_success(self, bStatus: int, bError: int, payload: bytes) -> bool:
        """
        Check if authentication was successful

        Args:
            bStatus: Status byte from response
            bError: Error byte from response
            payload: Response payload

        Returns:
            True if authentication successful, False otherwise
        """
        # Check APDU status words (SW1 SW2)
        # Check APDU status words (SW1 SW2)
        if len(payload) >= 2:
            # For General Authenticate with ULC, success should be 90 00.
            # However, some readers return "90 00 90 00" (Card Success + Reader Success).
            # And failure is "63 00 90 00" (Card Fail + Reader Success).
            # So we check if the payload STARTS with 90 00.
            if payload.startswith(b'\x90\x00'):
                return True
            
            # If payload contains more bytes and doesn't start with 90 00, it's a failure.
            # e.g. 63 00 90 00
            return False

        # If no payload (no SW1 SW2), fall back to CCID status
        # But General Authenticate SHOULD return SW1 SW2.
        if bStatus == 0x00 and bError == 0x00:
            return False # Safer to assume failure if no SW1 SW2

        # 0x69 = Authentication error
        if bError == 0x69:
            return False

        # 0x40 = Command failed
        if bStatus == 0x40:
            return False

        return False

    def format_hex(self, data: bytes) -> str:
        """Format bytes as hex string with spaces"""
        return ' '.join(f'{b:02X}' for b in data)

    def parse_hex(self, hex_str: str) -> bytes:
        """
        Parse hex string to bytes

        Args:
            hex_str: Hex string like "00 01 02 03" or "00010203"

        Returns:
            bytes object
        """
        # Remove spaces and convert
        hex_clean = hex_str.replace(' ', '').replace('\n', '')
        return bytes.fromhex(hex_clean)


# Convenience functions
def create_ccid_protocol() -> CCIDProtocol:
    """Create a new CCID protocol handler"""
    return CCIDProtocol()
