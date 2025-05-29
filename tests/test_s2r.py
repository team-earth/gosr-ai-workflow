import sys
import os
import json
import tempfile
from gosr.main import s2r

def test_main_usage_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["s2r.py"])
    assert s2r.main() == 1
    captured = capsys.readouterr()
    assert "Usage" in captured.out

def test_save_tree_creates_file(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        s2r.path = tmpdir
        # Mock tree.to_json to return a simple JSON string
        class DummyTree:
            def to_json(self, with_data):
                return '{"foo": "bar"}'
        monkeypatch.setattr(s2r, "tree", DummyTree())
        s2r.save_tree()
        with open(os.path.join(tmpdir, "r.json")) as f:
            data = json.load(f)
        assert data == {"foo": "bar"}

def test_save_tree_raises_if_path_none(monkeypatch):
    s2r.path = None
    class DummyTree:
        def to_json(self, with_data):
            return '{"foo": "bar"}'
    monkeypatch.setattr(s2r, "tree", DummyTree())
    try:
        s2r.save_tree()
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "must be set to a valid directory string" in str(e)

def test_save_resources_creates_file(monkeypatch):
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        s2r.path = tmpdir
        s2r.global_resources_list = [{"foo": "bar"}]
        s2r.save_resources()
        with open(os.path.join(tmpdir, "resources-raw.json")) as f:
            data = json.load(f)
        assert data == [{"foo": "bar"}]