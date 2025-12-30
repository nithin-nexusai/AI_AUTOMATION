"""Phone number utility functions."""

import re


def normalize_phone(phone: str | None) -> str:
    """Normalize phone number for comparison.

    Removes spaces, dashes, parentheses and ensures consistent format
    with country code for Indian numbers.

    Args:
        phone: Phone number in any format (e.g., "9876543210", "+91-987-654-3210")

    Returns:
        Normalized phone number with country code (e.g., "+919876543210")
        Empty string if phone is None or invalid

    Examples:
        >>> normalize_phone("9876543210")
        '+919876543210'
        >>> normalize_phone("+91-987-654-3210")
        '+919876543210'
        >>> normalize_phone("91 9876543210")
        '+919876543210'
        >>> normalize_phone(None)
        ''
    """
    if not phone:
        return ""

    # Remove all non-digit characters except +
    phone = re.sub(r"[^\d+]", "", phone)

    # Remove any + that's not at the start
    if "+" in phone:
        phone = "+" + phone.replace("+", "")

    # Indian numbers: add +91 prefix if missing
    if len(phone) == 10 and phone.isdigit():
        # 10 digits without country code
        phone = f"+91{phone}"
    elif len(phone) == 11 and phone.startswith("91"):
        # 11 digits starting with 91 (missing +)
        phone = f"+{phone}"
    elif len(phone) == 12 and phone.startswith("+91"):
        # Already correct format
        pass
    elif len(phone) == 13 and phone.startswith("+910"):
        # Has extra 0 after country code (common mistake)
        phone = f"+91{phone[4:]}"

    # Validate final format
    if not phone.startswith("+91") or len(phone) != 13:
        # Invalid format, return as-is for logging
        return phone

    return phone
