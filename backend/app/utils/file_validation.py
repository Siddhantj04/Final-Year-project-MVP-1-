import imghdr
from pathlib import Path

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SIGNATURE_CHECKS = {
    "jpeg": {b"\xff\xd8\xff"},
    "png": {b"\x89PNG\r\n\x1a\n"},
}


def validate_image_file(filename: str, content: bytes) -> tuple[bool, str]:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, "Only JPG and PNG images are allowed."

    if len(content) < 12:
        return False, "File is too small to be a valid image."

    kind = imghdr.what(None, h=content[:32])
    if kind not in ("jpeg", "png"):
        return False, "File content does not match a valid JPG or PNG image."

    if kind == "jpeg":
        if not content.startswith(b"\xff\xd8\xff"):
            return False, "Invalid JPEG file signature."
    elif kind == "png":
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            return False, "Invalid PNG file signature."

    return True, ""
