"""Tests for tools/mapper.py"""

import json
import shutil
from pathlib import Path

import pytest

from beaver_agent.tools.mapper import generate


@pytest.fixture(autouse=True)
def clean_beaver_dir(tmp_path):
    """Clean .beaver/ before and after each test."""
    beaver_dir = tmp_path / ".beaver"
    if beaver_dir.exists():
        import shutil
        shutil.rmtree(beaver_dir)
    yield
    if beaver_dir.exists():
        import shutil
        shutil.rmtree(beaver_dir)


class TestGenerate:
    def test_creates_beaver_directory(self, tmp_path):
        generate(tmp_path)
        assert (tmp_path / ".beaver").exists()

    def test_creates_three_json_files(self, tmp_path):
        generate(tmp_path)
        assert (tmp_path / ".beaver" / "index.json").exists()
        assert (tmp_path / ".beaver" / "dep_graph.json").exists()
        assert (tmp_path / ".beaver" / "entry_points.json").exists()

    def test_index_contains_files_list(self, tmp_path):
        # Create some Python files
        (tmp_path / "main.py").write_text("def foo(): pass\n")
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "__init__.py").write_text("")
        (tmp_path / "pkg" / "mod.py").write_text("import os\nclass Bar: pass\n")

        result = generate(tmp_path)

        index = json.loads((tmp_path / ".beaver" / "index.json").read_text())
        files = index["files"]
        # Paths should be relative to root
        assert "main.py" in files
        assert "pkg/__init__.py" in files
        assert "pkg/mod.py" in files

    def test_index_parsed_contains_imports_and_exports(self, tmp_path):
        (tmp_path / "mod.py").write_text(
            "import os\nfrom pathlib import Path\n"
            "class Foo: pass\n"
            "def bar(x, y): pass\n"
        )

        generate(tmp_path)

        index = json.loads((tmp_path / ".beaver" / "index.json").read_text())
        parsed = index["parsed"]
        mod = next(m for m in parsed if m["path"] == "mod.py")

        # Imports
        assert any(i["module"] == "os" for i in mod["imports"])
        assert any(i["module"] == "pathlib" and i["name"] == "Path" for i in mod["imports"])

        # Exports
        names = [e["name"] for e in mod["exports"]]
        assert "Foo" in names
        assert "bar" in names

    def test_functions_have_args_and_async_flag(self, tmp_path):
        (tmp_path / "mod.py").write_text(
            "def sync_func(a, b): pass\n"
            "async def async_func(x): pass\n"
        )

        generate(tmp_path)

        index = json.loads((tmp_path / ".beaver" / "index.json").read_text())
        parsed = index["parsed"]
        exports = next(m for m in parsed if "mod.py" in m["path"])["exports"]

        sync = next(e for e in exports if e["name"] == "sync_func")
        assert sync["type"] == "function"
        assert sync["args"] == ["a", "b"]

        async_fn = next(e for e in exports if e["name"] == "async_func")
        assert async_fn["type"] == "async"

    def test_dep_graph_contains_call_edges(self, tmp_path):
        # Create two files with call relationship
        (tmp_path / "caller.py").write_text(
            "from mod import helper\n"
            "def call_helper(): helper()\n"
        )
        (tmp_path / "mod.py").write_text(
            "def helper(): pass\n"
            "def other(): pass\n"
        )

        generate(tmp_path)

        dep_graph = json.loads((tmp_path / ".beaver" / "dep_graph.json").read_text())
        edges = dep_graph["edges"]

        # Should have call from call_helper -> helper
        helper_calls = [e for e in edges if e["to"] == "helper"]
        assert len(helper_calls) >= 1

    def test_entry_points_finds_main_functions(self, tmp_path):
        (tmp_path / "main.py").write_text(
            "def main():\n    pass\n"
            "if __name__ == '__main__':\n    main()\n"
        )
        (tmp_path / "async_main.py").write_text(
            "async def main():\n    pass\n"
        )

        generate(tmp_path)

        entry_points = json.loads((tmp_path / ".beaver" / "entry_points.json").read_text())["entry_points"]

        # Should find both main functions
        mains = [e for e in entry_points if e["type"] == "def main()"]
        assert len(mains) == 1
        assert "main.py" in mains[0]["file"]

        async_mains = [e for e in entry_points if e["type"] == "async def main()"]
        assert len(async_mains) == 1

    def test_entry_points_finds_typer_apps(self, tmp_path):
        (tmp_path / "cli.py").write_text(
            "import typer\n"
            "app = typer.Typer()\n"
            "@app.command()\n"
            "def run(): pass\n"
        )

        generate(tmp_path)

        entry_points = json.loads((tmp_path / ".beaver" / "entry_points.json").read_text())["entry_points"]
        typer_apps = [e for e in entry_points if e["type"] == "typer app"]
        assert len(typer_apps) == 1

    def test_excludes_self_and_beaver_dir(self, tmp_path):
        # Create mapper.py and .beaver/ to confirm they're excluded
        (tmp_path / "mapper.py").write_text("def generate(): pass\n")
        (tmp_path / ".beaver").mkdir()
        (tmp_path / ".beaver" / "old.json").write_text("{}")

        result = generate(tmp_path)

        index = json.loads((tmp_path / ".beaver" / "index.json").read_text())
        files = index["files"]
        assert "mapper.py" not in files
        assert ".beaver/old.json" not in files

    def test_returns_summary_dict(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")

        result = generate(tmp_path)

        assert result["total_files"] == 2
        assert result["parsed_files"] == 2
        assert "output_dir" in result
        assert ".beaver" in result["output_dir"]

    def test_returns_consistent_with_cli_output(self, tmp_path):
        # Regression: ensure the returned dict matches what main.py map() prints
        result = generate(tmp_path)
        # These keys are what main.py accesses:
        assert "parsed_files" in result
        assert "total_files" in result
        assert "entry_points" in result
        assert "output_dir" in result
