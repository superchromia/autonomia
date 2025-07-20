import os
import hashlib
from storage.base import StorageBackend

class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: str = 'images'):
        self.base_dir = base_dir
        self._ensure_dir()

    def _ensure_dir(self):
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def _hash_filename(self, file_bytes: bytes, ext: str = '.jpg') -> str:
        h = hashlib.sha256()
        h.update(file_bytes)
        return h.hexdigest() + ext

    async def save_image(self, file_bytes: bytes, file_name: str = None) -> str:
        hashed_name = self.hash_filename(file_bytes)
        file_path = os.path.join(self.base_dir, hashed_name)
        if os.path.exists(file_path):
            return file_path
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        return file_path 