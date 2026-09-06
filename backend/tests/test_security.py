import pytest
from backend.app.services import safe_project_id

def test_project_id_rejects_path_traversal():
    with pytest.raises(ValueError):
        safe_project_id("../../windows/system32")

def test_project_id_accepts_uuid_shape():
    assert safe_project_id("12345678-abcd") == "12345678-abcd"
