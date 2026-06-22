import re

def validate_email(email: str) -> bool:
    """
    Validates an email address according to specific criteria.

    Args:
        email (str): The email address to validate.

    Returns:
        bool: True if the email is valid, False otherwise.
    """
    if not email:
        return False

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    match = re.fullmatch(pattern, email)
    return bool(match)