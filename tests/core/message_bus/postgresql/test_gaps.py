import pytest


@pytest.mark.asyncio
async def test_gap_detected_and_late_message_processed(topic, db):

    # insert 1
    db.insert_message("public.test", {"v": "a"})

    # simulate missing 2 by inserting id=3 manually
    db.messages["public.test"].append({"id": 3, "payload": {"v": "c"}})

    subscriber = topic.subscribe("test")

    first = await subscriber.__anext__()
    assert first["v"] == "a"

    # insert missing message
    db.messages["public.test"].append({"id": 2, "payload": {"v": "b"}})

    second = await subscriber.__anext__()
    third = await subscriber.__anext__()

    assert [m["v"] for m in [first, second, third]] == ["a", "b", "c"]
