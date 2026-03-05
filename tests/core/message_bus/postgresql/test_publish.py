import pytest


@pytest.mark.asyncio
async def test_publish_and_receive(topic):

    async with topic.publish() as publish:
        await publish({"x": 1})

    subscriber = topic.subscribe()

    message = await subscriber.__anext__()

    assert message == {"x": 1}
