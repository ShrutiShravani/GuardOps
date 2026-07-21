"""
Unit tests for the `guardops` CLI.
"""

import json
import os
import sys
import tempfile

import pytest

from guardops.cli import main


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestInitCommand:
    def test_creates_manifest_and_guards(self, tmp_dir):
        exit_code = main(["init", "--dir", tmp_dir])
        assert exit_code == 0
        assert os.path.exists(os.path.join(tmp_dir, "guard_manifest.json"))
        assert os.path.exists(os.path.join(tmp_dir, "custom_guards.py"))

    def test_manifest_is_valid_json(self, tmp_dir):
        main(["init", "--dir", tmp_dir])
        path = os.path.join(tmp_dir, "guard_manifest.json")
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_manifest_contains_starter_node(self, tmp_dir):
        main(["init", "--dir", tmp_dir])
        path = os.path.join(tmp_dir, "guard_manifest.json")
        with open(path) as f:
            data = json.load(f)
        assert "MyAgentNode" in data

    def test_custom_guards_has_check_function(self, tmp_dir):
        main(["init", "--dir", tmp_dir])
        path = os.path.join(tmp_dir, "custom_guards.py")
        content = open(path).read()
        assert "def check_my_condition" in content
        assert "def recover_my_value" in content

    def test_does_not_overwrite_existing_files_by_default(self, tmp_dir):
        # Write a sentinel into the target files
        manifest_path = os.path.join(tmp_dir, "guard_manifest.json")
        guards_path = os.path.join(tmp_dir, "custom_guards.py")
        with open(manifest_path, "w") as f:
            f.write('{"sentinel": true}')
        with open(guards_path, "w") as f:
            f.write("# sentinel")

        main(["init", "--dir", tmp_dir])

        # Files should be unchanged
        assert json.load(open(manifest_path)) == {"sentinel": True}
        assert open(guards_path).read() == "# sentinel"

    def test_force_overwrites_existing_files(self, tmp_dir):
        manifest_path = os.path.join(tmp_dir, "guard_manifest.json")
        with open(manifest_path, "w") as f:
            f.write('{"sentinel": true}')

        main(["init", "--dir", tmp_dir, "--force"])

        data = json.load(open(manifest_path))
        assert "sentinel" not in data
        assert "MyAgentNode" in data

    def test_creates_target_directory_if_missing(self, tmp_dir):
        nested = os.path.join(tmp_dir, "new", "project")
        main(["init", "--dir", nested])
        assert os.path.exists(os.path.join(nested, "guard_manifest.json"))


class TestValidateCommand:
    def test_valid_manifest_exits_zero(self, tmp_dir):
        # Create a valid manifest first
        main(["init", "--dir", tmp_dir])
        manifest = os.path.join(tmp_dir, "guard_manifest.json")
        exit_code = main(["validate", "--manifest", manifest])
        assert exit_code == 0

    def test_missing_manifest_exits_nonzero(self, tmp_dir):
        missing = os.path.join(tmp_dir, "nonexistent.json")
        exit_code = main(["validate", "--manifest", missing])
        assert exit_code == 1

    def test_invalid_manifest_exits_nonzero(self, tmp_dir):
        bad_manifest = os.path.join(tmp_dir, "bad.json")
        with open(bad_manifest, "w") as f:
            # Missing condition_type
            json.dump({"Node": [{"metric_key": "x", "strategy": "INVALID"}]}, f)
        exit_code = main(["validate", "--manifest", bad_manifest])
        assert exit_code == 1


class TestNoCommand:
    def test_no_args_returns_zero(self):
        # Should print help and return 0
        exit_code = main([])
        assert exit_code == 0
