from dcos.errors import DCOSException
from dcos.mesos import TaskIO
from tempfile import TemporaryFile

def test_get_chunked_msg():
    """Tests getting a chunked message
    """

    msg = b'Test Message.'
    file = TemporaryFile()
    chunk = '%X\r\n%s\r\n' % (len(msg), msg.decode('utf-8'))
    import pdb; pdb.set_trace()

    try:
        file.write(bytes(chunk, 'utf-8'))
        file.seek(0)
    except Exception as exception:
        raise DCOSException(
            "Error writing to {filename} in test_get_chunked_msg: \
            {error}".format(filename=file, error=exception))

    try:
        taskIO = TaskIO("1")
        chunked_msg = taskIO.get_chunked_msg(file.fileno())
    except Exception as exception:
        raise DCOSException(
            "Error reading from {filename} in test_get_chunked_msg: \
            {error}".format(filename=file, error=exception))


    assert chunked_msg == msg

if __name__ == '__main__':
    test_get_chunked_msg()