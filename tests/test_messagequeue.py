from sacred import messagequeue


def test_messagequeue():
    mq = messagequeue.SacredMQ()
    consumer1 = mq.add_consumer()
    consumer2 = mq.add_consumer()

    assert not consumer1.has_message()
    assert not consumer2.has_message()

    assert consumer1.read_all() == []
    assert consumer2.read_all() == []


    mq.publish("message1")
    assert consumer1.has_message()
    assert consumer2.has_message()

    assert consumer1.read_all() == ["message1"]
    assert consumer2.read_all() == ["message1"]

    assert not consumer1.has_message()
    assert not consumer2.has_message()

    assert consumer1.read_all() == []
    assert consumer2.read_all() == []


    mq.publish("message2")
    mq.publish("message3")

    assert consumer1.has_message()
    assert consumer2.has_message()

    assert consumer1.read_all() == ["message2", "message3"]
    assert consumer2.read_all() == ["message2", "message3"]

    assert consumer1.read_all() == []
    assert consumer2.read_all() == []
