"""Tests for FileSystemService."""

from researcharr.core.services import FileSystemService


def test_filesystem_service_exists(tmp_path):
    """Test exists method."""
    fs = FileSystemService()
    test_file = tmp_path / "test.txt"

    assert not fs.exists(test_file)
    test_file.write_text("content")
    assert fs.exists(test_file)


def test_filesystem_service_read_write_text(tmp_path):
    """Test read_text and write_text methods."""
    fs = FileSystemService()
    test_file = tmp_path / "test.txt"

    fs.write_text(test_file, "hello world")
    assert fs.read_text(test_file) == "hello world"


def test_filesystem_service_read_write_bytes(tmp_path):
    """Test read_bytes and write_bytes methods."""
    fs = FileSystemService()
    test_file = tmp_path / "test.bin"

    fs.write_bytes(test_file, b"binary data")
    assert fs.read_bytes(test_file) == b"binary data"


def test_filesystem_service_mkdir(tmp_path):
    """Test mkdir method."""
    fs = FileSystemService()
    test_dir = tmp_path / "subdir" / "nested"

    fs.mkdir(test_dir)
    assert test_dir.exists()
    assert test_dir.is_dir()


def test_filesystem_service_remove(tmp_path):
    """Test remove method."""
    fs = FileSystemService()
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    assert test_file.exists()
    fs.remove(test_file)
    assert not test_file.exists()


def test_filesystem_service_rmtree(tmp_path):
    """Test rmtree method."""
    fs = FileSystemService()
    test_dir = tmp_path / "subdir"
    test_dir.mkdir()
    (test_dir / "file.txt").write_text("content")

    assert test_dir.exists()
    fs.rmtree(test_dir)
    assert not test_dir.exists()


def test_filesystem_service_listdir(tmp_path):
    """Test listdir method."""
    fs = FileSystemService()
    (tmp_path / "file1.txt").write_text("a")
    (tmp_path / "file2.txt").write_text("b")
    (tmp_path / "subdir").mkdir()

    contents = fs.listdir(tmp_path)
    assert "file1.txt" in contents
    assert "file2.txt" in contents
    assert "subdir" in contents


def test_filesystem_service_copy(tmp_path):
    """Test copy method."""
    fs = FileSystemService()
    src = tmp_path / "source.txt"
    dst = tmp_path / "dest.txt"

    src.write_text("content")
    fs.copy(src, dst)

    assert dst.exists()
    assert fs.read_text(dst) == "content"


def test_filesystem_service_move(tmp_path):
    """Test move method."""
    fs = FileSystemService()
    src = tmp_path / "source.txt"
    dst = tmp_path / "dest.txt"

    src.write_text("content")
    fs.move(src, dst)

    assert not src.exists()
    assert dst.exists()
    assert fs.read_text(dst) == "content"


def test_filesystem_service_get_size(tmp_path):
    """Test get_size method."""
    fs = FileSystemService()
    test_file = tmp_path / "test.txt"

    fs.write_text(test_file, "hello")
    assert fs.get_size(test_file) == 5


def test_filesystem_service_is_file_is_dir(tmp_path):
    """Test is_file and is_dir methods."""
    fs = FileSystemService()
    test_file = tmp_path / "test.txt"
    test_dir = tmp_path / "subdir"

    test_file.write_text("content")
    test_dir.mkdir()

    assert fs.is_file(test_file)
    assert not fs.is_file(test_dir)
    assert fs.is_dir(test_dir)
    assert not fs.is_dir(test_file)


def test_filesystem_service_open_text(tmp_path):
    """Test open method for text files."""
    fs = FileSystemService()
    test_file = tmp_path / "test.txt"

    with fs.open(test_file, "w", encoding="utf-8") as f:
        f.write("hello world")

    with fs.open(test_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == "hello world"


def test_filesystem_service_open_binary(tmp_path):
    """Test open method for binary files."""
    fs = FileSystemService()
    test_file = tmp_path / "test.bin"

    with fs.open(test_file, "wb") as f:
        f.write(b"binary data")

    with fs.open(test_file, "rb") as f:
        content = f.read()

    assert content == b"binary data"


def test_filesystem_service_write_text_creates_parent_dirs(tmp_path):
    """Test that write_text creates parent directories."""
    fs = FileSystemService()
    test_file = tmp_path / "a" / "b" / "c" / "test.txt"

    fs.write_text(test_file, "content")
    assert test_file.exists()
    assert fs.read_text(test_file) == "content"


def test_filesystem_service_write_bytes_creates_parent_dirs(tmp_path):
    """Test that write_bytes creates parent directories."""
    fs = FileSystemService()
    test_file = tmp_path / "a" / "b" / "c" / "test.bin"

    fs.write_bytes(test_file, b"data")
    assert test_file.exists()
    assert fs.read_bytes(test_file) == b"data"
