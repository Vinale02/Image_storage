from pathlib import Path
import uuid



ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif'}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


def is_allowed_file(filename: Path) ->  bool:
    """ПРоверяем есть ли расширение в разрешенной коллекции"""
    ext = filename.suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def get_unique_name(filename: Path) -> str:
    ext = filename.suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return unique_name


if __name__ == '__main__':
    print(get_unique_name(Path('test.png')))
    print(get_unique_name(Path('test.mp4')))