from datetime import datetime, timedelta

import pytest

from src.models.spatial_temporal_db import SpatialTemporalDB


@pytest.fixture()
def db():
    return SpatialTemporalDB()


def test_crud_and_query(db):
    # Add nodes
    db.add_node("n1", {"type": "character", "name": "Bilbo"})
    db.add_node("n2", {"type": "location", "name": "Rivendell"})
    db.add_node("n3", {"type": "event", "description": "Council of Elrond"})

    assert len(db) == 3
    assert "n1" in db and "n3" in db

    # Update node
    updated = db.update_node("n1", age=50)
    assert updated is True
    assert db.get_node("n1").data["age"] == 50

    # Query by type
    chars = db.query_nodes(node_type="character")
    assert set(chars.keys()) == {"n1"}

    # Query by time range (use creation timestamps)
    now = datetime.utcnow()
    past = now - timedelta(minutes=1)
    future = now + timedelta(minutes=1)
    time_filtered = db.query_nodes(start_time=past, end_time=future)
    assert len(time_filtered) == 3

    # Delete node
    removed = db.delete_node("n2")
    assert removed is True
    assert len(db) == 2
    assert "n2" not in db

    # Delete non-existent node returns False
    assert db.delete_node("unknown") is False 