import re

PAN_RE = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
GSTIN_RE = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9][Z][A-Z0-9]$')

def validate_pan(pan: str) -> bool:
    """Validate Indian PAN format (e.g., ABCDE1234F)."""
    if not pan:
        return False
    return bool(PAN_RE.match(pan.strip().upper()))

def validate_aadhaar(aadhaar: str) -> bool:
    """Validate Indian Aadhaar format (12 numeric digits)."""
    if not aadhaar:
        return False
    digits = re.sub(r'\D', '', str(aadhaar))
    return len(digits) == 12

def validate_gstin(gstin: str) -> bool:
    """Validate 15-character Indian GSTIN format."""
    if not gstin:
        return False
    return bool(GSTIN_RE.match(gstin.strip().upper()))

def validate_phone(phone: str) -> bool:
    """Validate Indian phone number (10 digits)."""
    if not phone:
        return False
    digits = re.sub(r'\D', '', str(phone))
    return len(digits) >= 10
