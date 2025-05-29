import os
import json
import tempfile
import sys
from gosr.main import g2o

def test_save_tree_creates_file(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        g2o.path = tmpdir
        # Mock tree.to_json to return a simple JSON string
        class DummyTree:
            def to_json(self, with_data):
                return '{"foo": "bar"}'
        monkeypatch.setattr(g2o, "tree", DummyTree())
        g2o.save_tree()
        with open(os.path.join(tmpdir, "o.json")) as f:
            data = json.load(f)
        assert data == {"foo": "bar"}

def test_save_tree_raises_if_path_not_set(monkeypatch):
    g2o.path = None
    class DummyTree:
        def to_json(self, with_data):
            return '{"foo": "bar"}'
    monkeypatch.setattr(g2o, "tree", DummyTree())
    try:
        g2o.save_tree()
        assert False, "Expected AssertionError"
    except AssertionError as e:
        assert "path must be a non-empty string" in str(e)

def test_main_returns_1_on_missing_args(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["g2o.py"])
    assert g2o.main() == 1
    captured = capsys.readouterr()
    assert "Usage" in captured.out

def test_print_tree_logs_warning(monkeypatch, caplog):
    # tree.get_node returns None, should log a warning
    class DummyTree:
        def get_node(self, identifier):
            return None
    monkeypatch.setattr(g2o, "tree", DummyTree())
    g2o.print_tree("notfound")
    # Check for the exact warning message
    expected = "Node with identifier 'notfound' not found in tree."
    assert any(expected in record.getMessage() and record.levelname == "WARNING" for record in caplog.records)