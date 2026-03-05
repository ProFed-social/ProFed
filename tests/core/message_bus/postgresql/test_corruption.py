import pytest


@pytest.mark.asyncio
async def test_corruption_detected(topic, db):

    db.insert_message("public.test", {"v": "a"})
    db.insert_gap("test.test_gaps", 1)

    subscriber = topic.subscribe()

    with pytest.raises(RuntimeError):
        await subscriber.__anext__()
