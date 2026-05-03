import os
import uuid
import hashlib

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_file(file_bytes, filename):
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{filename}")

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    return {
        "file_id": file_id,
        "filename": filename,
        "path": file_path,
        "hash": file_hash,
        "size_kb": round(len(file_bytes) / 1024, 2)
    }
