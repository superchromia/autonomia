from abc import ABC, abstractmethod
import hashlib

class StorageBackend(ABC):
    @abstractmethod
    async def save_image(self, file_bytes: bytes, file_name: str = None) -> str:
        """
        Сохраняет изображение и возвращает путь или URL для хранения в базе.
        """
        pass

    def hash_filename(self, file_bytes: bytes, ext: str = '.jpg') -> str:
        h = hashlib.sha256()
        h.update(file_bytes)
        return h.hexdigest() + ext 