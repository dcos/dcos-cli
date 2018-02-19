import json

from dcos import recordio
from dcos.errors import DCOSException


def test_encode():
    try:
        encoder = recordio.Encoder(lambda s: bytes(json.dumps(s), "UTF-8"))
    except Exception as exception:
        raise DCOSException("Error instantiating 'RecordIO' encoder: {error}"
                            .format(error=exception))

    try:
        message = {
            "type": "ATTACH_CONTAINER_OUTPUT",
            "containerId": "123456789"
        }

        encoded = encoder.encode(message)

    except Exception as exception:
        raise DCOSException("Error encoding 'RecordIO' message: {error}"
                            .format(error=exception))

    string = json.dumps(message)
    assert encoded == bytes(str(len(string)) + "\n" + string, "UTF-8")


def test_encode_decode():
    total_messages = 10

    try:
        encoder = recordio.Encoder(lambda s: bytes(json.dumps(s), "UTF-8"))
    except Exception as exception:
        raise DCOSException("Error instantiating 'RecordIO' encoder: {error}"
                            .format(error=exception))

    try:
        decoder = recordio.Decoder(lambda s: json.loads(s.decode("UTF-8")))
    except Exception as exception:
        raise DCOSException("Error instantiating 'RecordIO' decoder: {error}"
                            .format(error=exception))

    try:
        message = {
            "type": "ATTACH_CONTAINER_OUTPUT",
            "containerId": "123456789"
        }

        encoded = b""
        for i in range(total_messages):
            encoded += encoder.encode(message)

    except Exception as exception:
        raise DCOSException("Error encoding 'RecordIO' message: {error}"
                            .format(error=exception))

    try:
        all_records = []
        offset = 0
        chunk_size = 5
        while offset < len(encoded):
            records = decoder.decode(encoded[offset:offset + chunk_size])
            all_records.extend(records)
            offset += chunk_size

        assert len(all_records) == total_messages

        for record in all_records:
            assert record == message
    except Exception as exception:
        raise DCOSException("Error decoding 'RecordIO' messages: {error}"
                            .format(error=exception))
