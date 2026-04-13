"""Phone number utility functions."""

import re


def normalize_phone(phone: str | None, for_db: bool = False) -> str:
    """Normalize phone number for comparison and storage.

    CRITICAL: This function now supports two formats:
    - API/Comparison format: "+919876543210" (with + prefix)
    - Database format: "919876543210" (without + prefix)
    
    Use for_db=True when storing/querying database to match existing records.
    Use for_db=False (default) for API calls and comparisons.

    Args:
        phone: Phone number in any format (e.g., "9876543210", "+91-987-654-3210")
        for_db: If True, returns format without + prefix for database compatibility

    Returns:
        Normalized phone number:
        - for_db=False: "+919876543210" (with + prefix)
        - for_db=True: "919876543210" (without + prefix)
        Empty string if phone is None or invalid

    Examples:
        >>> normalize_phone("9876543210")
        '+919876543210'
        >>> normalize_phone("9876543210", for_db=True)
        '919876543210'
        >>> normalize_phone("+91-987-654-3210")
        '+919876543210'
        >>> normalize_phone("+91-987-654-3210", for_db=True)
        '919876543210'
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
    elif len(phone) == 12 and phone.startswith("91") and not phone.startswith("+"):
        # 12 digits starting with 91 (missing +)
        phone = f"+{phone}"
    elif len(phone) == 13 and phone.startswith("+91"):
        # Already correct format (+91 + 10 digits)
        pass
    elif len(phone) == 13 and phone.startswith("+910"):
        # Has extra 0 after country code (common mistake)
        phone = f"+91{phone[4:]}"

    # Validate final format
    if not phone.startswith("+91") or len(phone) != 13:
        # Invalid format, return as-is for logging
        return phone

    # Return database format (without +) if requested
    if for_db:
        return phone.lstrip("+")
    
    return phone
