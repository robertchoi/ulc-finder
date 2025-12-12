"""
Key Generator
Handles 16-byte key generation and incrementation
"""

from typing import Optional


class KeyGenerator:
    """16-byte key generator with increment functionality"""

    def __init__(self, start_key: bytes):
        """
        Initialize key generator

        Args:
            start_key: Starting 16-byte key
        """
        if len(start_key) != 16:
            raise ValueError("Key must be exactly 16 bytes")

        self.start_key = start_key
        self.current_key = start_key
        self.end_key = b'\xFF' * 16
        self.attempts = 0

    def increment(self) -> bool:
        """
        Increment current key by 1

        Returns:
            True if successful, False if overflow (reached FF...FF)
        """
        # Convert to integer (big-endian)
        key_int = int.from_bytes(self.current_key, byteorder='big')

        # Increment
        key_int += 1

        # Check overflow
        if key_int > 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:
            return False

        # Convert back to bytes
        self.current_key = key_int.to_bytes(16, byteorder='big')
        self.attempts += 1
        return True

    def get_current_key(self) -> bytes:
        """Get current key"""
        return self.current_key

    def get_attempts(self) -> int:
        """Get number of attempts (keys tried)"""
        return self.attempts

    def calculate_progress(self) -> float:
        """
        Calculate progress percentage

        Returns:
            Progress from 0.0 to 100.0
        """
        start_int = int.from_bytes(self.start_key, byteorder='big')
        current_int = int.from_bytes(self.current_key, byteorder='big')
        end_int = int.from_bytes(self.end_key, byteorder='big')

        if end_int == start_int:
            return 100.0

        progress = ((current_int - start_int) / (end_int - start_int)) * 100.0
        return min(100.0, max(0.0, progress))

    def format_key(self, key: Optional[bytes] = None) -> str:
        """
        Format key as hex string with spaces

        Args:
            key: Key to format (None = current key)

        Returns:
            Formatted hex string
        """
        if key is None:
            key = self.current_key

        return ' '.join(f'{b:02X}' for b in key)

    @staticmethod
    def parse_key(hex_str: str) -> bytes:
        """
        Parse hex string to 16-byte key

        Args:
            hex_str: Hex string like "00 01 02 ... 0F" or "000102...0F"

        Returns:
            16-byte key

        Raises:
            ValueError: If invalid format or not 16 bytes
        """
        # Remove spaces and newlines
        hex_clean = hex_str.replace(' ', '').replace('\n', '').strip()

        # Convert to bytes
        try:
            key_bytes = bytes.fromhex(hex_clean)
        except ValueError as e:
            raise ValueError(f"Invalid hex string: {e}")

        # Check length
        if len(key_bytes) != 16:
            raise ValueError(f"Key must be 16 bytes, got {len(key_bytes)}")

        return key_bytes

    def reset(self, new_start_key: Optional[bytes] = None):
        """
        Reset to start key

        Args:
            new_start_key: New start key (None = use original start key)
        """
        if new_start_key:
            if len(new_start_key) != 16:
                raise ValueError("Key must be exactly 16 bytes")
            self.start_key = new_start_key

        self.current_key = self.start_key
        self.attempts = 0

    def is_at_end(self) -> bool:
        """Check if current key is at the end (FF...FF)"""
        return self.current_key == self.end_key


# Default manufacturer key for ULC
DEFAULT_MANUFACTURER_KEY = bytes.fromhex('494545444B414552422145414355554659')
# ASCII: "IEMKAERB!NACUOYF" = "BREAKMEIFYOUCAN!" reversed


def create_key_generator(start_key_hex: str) -> KeyGenerator:
    """
    Create key generator from hex string

    Args:
        start_key_hex: Hex string of start key

    Returns:
        KeyGenerator instance
    """
    start_key = KeyGenerator.parse_key(start_key_hex)
    return KeyGenerator(start_key)
