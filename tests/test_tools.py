#!/usr/bin/env python

import os
import tempfile
import pytest
from yaoc.tools import ToolManager, Basic, WebAccess, FileAccess


class TestToolManager:
    def test_no_tools_enabled(self):
        tm = ToolManager({})
        assert tm._tools == {}
        assert tm.specs == []

    def test_basic_tools_enabled(self):
        tm = ToolManager({"basic": True})
        assert "get_time" in tm._tools
        assert len(tm.specs) == 1
        assert tm.specs[0]["function"]["name"] == "get_time"

    def test_web_access_tools_enabled(self):
        tm = ToolManager({"web_access": True})
        assert "web_fetch" in tm._tools
        assert "web_search" in tm._tools
        assert len(tm.specs) == 2

    def test_file_access_tools_enabled(self):
        tm = ToolManager({"file_access": True})
        assert "list_dir" in tm._tools
        assert "read_file" in tm._tools
        assert "write_file" in tm._tools
        assert "find_file" in tm._tools
        assert len(tm.specs) == 4

    def test_multiple_tool_classes(self):
        tm = ToolManager({"basic": True, "file_access": True})
        assert "get_time" in tm._tools
        assert "list_dir" in tm._tools
        assert len(tm.specs) == 5

    def test_tool_spec_structure(self):
        tm = ToolManager({"file_access": True})
        spec = next(s for s in tm.specs if s["function"]["name"] == "write_file")
        assert spec["type"] == "function"
        assert "description" in spec["function"]
        assert "parameters" in spec["function"]
        assert "path" in spec["function"]["parameters"]["properties"]
        assert "content" in spec["function"]["parameters"]["properties"]
        assert "path" in spec["function"]["parameters"]["required"]
        assert "content" in spec["function"]["parameters"]["required"]

    def test_tool_spec_with_optional_param(self):
        tm = ToolManager({"file_access": True})
        spec = next(s for s in tm.specs if s["function"]["name"] == "find_file")
        assert "name" in spec["function"]["parameters"]["required"]
        assert "directory" not in spec["function"]["parameters"]["required"]

    def test_call_tool(self):
        tm = ToolManager({"basic": True})
        result = tm.call("get_time")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_call_nonexistent_tool(self):
        tm = ToolManager({"basic": True})
        with pytest.raises(ValueError, match="Tool 'nonexistent' not found"):
            tm.call("nonexistent")


class TestBasic:
    def test_get_time(self):
        result = Basic.get_time()
        assert isinstance(result, str)
        assert len(result) > 0


class TestFileAccess:
    def test_list_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "subdir"))
            open(os.path.join(tmpdir, "file1.txt"), "w").close()
            open(os.path.join(tmpdir, "file2.txt"), "w").close()

            result = FileAccess.list_dir(tmpdir)
            lines = result.split("\n")
            assert "file1.txt" in lines
            assert "file2.txt" in lines
            assert "subdir" in lines

    def test_read_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            f.flush()
            result = FileAccess.read_file(f.name)
            assert result == "test content"
        os.unlink(f.name)

    def test_write_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
        result = FileAccess.write_file(path, "hello world")
        assert result == "Done"
        with open(path) as f:
            assert f.read() == "hello world"
        os.unlink(path)

    def test_find_file_exact_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "target.txt"), "w").close()
            open(os.path.join(tmpdir, "other.txt"), "w").close()

            result = FileAccess.find_file("target.txt", tmpdir)
            assert "target.txt" in result
            assert "other.txt" not in result

    def test_find_file_substring_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "test_one.py"), "w").close()
            open(os.path.join(tmpdir, "test_two.py"), "w").close()
            open(os.path.join(tmpdir, "main.py"), "w").close()

            result = FileAccess.find_file("test", tmpdir)
            assert "test_one.py" in result
            assert "test_two.py" in result
            assert "main.py" not in result

    def test_find_file_recursive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)
            open(os.path.join(tmpdir, "top.txt"), "w").close()
            open(os.path.join(subdir, "nested.txt"), "w").close()

            result = FileAccess.find_file(".txt", tmpdir)
            assert "top.txt" in result
            assert "nested.txt" in result

    def test_find_file_no_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "file.txt"), "w").close()

            result = FileAccess.find_file("nonexistent", tmpdir)
            assert result == "No files found."

    def test_find_file_default_directory(self):
        # Test that default directory is "."
        result = FileAccess.find_file("nonexistent_pattern_xyz123")
        assert result == "No files found."
