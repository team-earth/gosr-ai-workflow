from gosr.main import o2s
import sys
import os
import json
import tempfile
import pytest

def test_main_usage_error(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setattr(sys, "argv", ["o2s.py"])
    assert o2s.main() == 1
    captured = capsys.readouterr()
    assert "Usage" in captured.out

def test_save_tree_creates_file(monkeypatch):
    # Use a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        o2s.path = tmpdir
        # Mock tree.to_json to return a simple JSON string
        class DummyTree:
            def to_json(self, with_data):
                return '{"foo": "bar"}'
        monkeypatch.setattr(o2s, "tree", DummyTree())
        o2s.save_tree()
        # Check that the file was created and contains expected data
        with open(os.path.join(tmpdir, "s.json")) as f:
            data = json.load(f)
        assert data == {"foo": "bar"}

def test_save_tree_raises_if_path_none(monkeypatch):
    o2s.path = None
    # Mock tree.to_json to avoid side effects
    class DummyTree:
        def to_json(self, with_data):
            return '{"foo": "bar"}'
    monkeypatch.setattr(o2s, "tree", DummyTree())
    try:
        o2s.save_tree()
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "Path is not set" in str(e)

def test_add_solutions4_inserts_nodes(monkeypatch):
    class DummyNode:
        identifier = "id"
        data = "Obstacle X"
    node = DummyNode()
    o2s.config = {"locality": "TestTown", "country": "TestLand", "max_items_per_llm_call": 2}
    # Mock call_gpt4 to return a JSON string
    monkeypatch.setattr(o2s, "call_gpt4", lambda msg: '[{"solution": {"title": "A", "description": "desc"}}, {"solution": {"title": "B", "description": "desc"}}]')
    # Mock normalize_data to parse the JSON string
    monkeypatch.setattr(o2s, "normalize_data", lambda text: json.loads(text))
    # Mock insert_nodes to capture calls
    called = {}
    def fake_insert_nodes(identifier, data, tag):
        called["identifier"] = identifier
        called["data"] = data
        called["tag"] = tag
    monkeypatch.setattr(o2s, "insert_nodes", fake_insert_nodes)
    o2s.add_solutions4(node)
    assert called["identifier"] == "id"
    assert called["tag"] == "solution"
    assert len(called["data"]) == 2

def test_add_solutions4_raises_if_config_none():
    o2s.config = None
    class DummyNode:
        identifier = "id"
        data = "Obstacle X"
    node = DummyNode()
    try:
        o2s.add_solutions4(node)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "Configuration not loaded" in str(e)

def test_main_malformed_config(monkeypatch, tmp_path):
    import sys
    import yaml
    from gosr.main import o2s
    # Create a malformed config.yaml
    config_path = tmp_path / "config.yaml"
    config_path.write_text("not: valid: yaml: [")
    monkeypatch.setattr(sys, "argv", ["o2s.py", str(tmp_path)])
    # Create a minimal o.json
    (tmp_path / "o.json").write_text("{}")
    with pytest.raises(yaml.YAMLError):
        o2s.main()