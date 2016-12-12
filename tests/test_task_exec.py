# from base64 import b64encode, b64decode
# from dcos import recordio
from dcos.errors import DCOSException
from dcos.mesos import TaskIO

# import json
# from queue import Queue
# from tempfile import TemporaryFile
# import sys
# import threading

# task_id = "1"
# taskIO = TaskIO(task_id)
# taskIO.encoder = recordio.Encoder(lambda s: bytes(json.dumps(s, ensure_ascii=False), "UTF-8"))
# taskIO.decoder = recordio.Decoder(lambda s: json.loads(s.decode("UTF-8")))


# def test_attach_output_stream():
#     #Not functional yet
#     taskIO.output_queue = Queue()
#     msg = {}
#     msg['type'] = 'DATA'
#     msg['data'] = 'Test'
#     encoded_msg = taskIO.encoder.encode(msg)
#     file = TemporaryFile()
#     chunk = '%X\r\n%s\r\n' % (len(encoded_msg), encoded_msg.decode('utf-8'))

#     try:
#         file.write(bytes(chunk, 'utf-8'))
#         file.seek(0)
#     except Exception as exception:
#         raise DCOSException(
#             "Error writing to {filename} in test_attach_output_stream: \
#             {error}".format(filename=file, error=exception))

#     thread = threading.Thread(
#         target=taskIO._attach_output_stream(file.fileno()))
#     thread.daemon = True
#     thread.start()

#     assert taskIO.decoder.decode(taskIO.output_queue.get()) == msg


# def test_attach_input_stream():
#     #Needs a server to accept the http posts
#     taskIO.input_queue = Queue()
#     taskIO.agent_url = "http://invalidAddress.notARealSite"
#     test_msg = b"abc123"
#     taskIO.input_queue.put(test_msg)


# def test_input_thread():
#     msg_data = 'abcd'
#     message = {
#     'type': 'ATTACH_CONTAINER_INPUT',
#     'attach_container_input': {
#         'type': 'PROCESS_IO',
#         'process_io': {
#             'type': 'DATA',
#             'data': {
#                 'type': 'STDIN',
#                 'data': msg_data}}}}

#     thread = threading.Thread(
#         target=taskIO._input_thread())
#     thread.daemon = True
#     thread.start()

#     os.write(sys.stdin.fileno(), base64.b64encode(msg_data))
#     input_message = taskIO.input_queue.get()
#     assert encoder.encde(message) == input_message


# def test_output_thread():
#     stdout = sys.stdout
#     sys.stdout.buffer = TemporaryFile()

#     taskIO.output_queue = Queue()
#     taskIO.output_queue.put(
#         {
#             'data': b64encode(b'test\n'), 
#             'type': 'STDOUT'
#         }
#     )

#     thread = threading.Thread(
#         target=taskIO._output_thread())
#     thread.daemon = True
#     thread.start()

# ------------------------------------------------------------------------------

def test_task_io_with_invalid_task_id():
    import uuid
    id = str(uuid.uuid4())
    try:
        taskIO = TaskIO(id)
    except DCOSException as e:
        assert e.args[0] == \
            "No container found for the specified task." \
            " It might still be spinning up." \
            " Please try again later."


# def test_task_io_with_invalid_cmd():
#     # Needs a real task id
#     try:
#         taskIO = TaskIO()
#     except DCOSException as e:
#         assert e.args[0] == "Failed to execute command: No such file or directory"


# def test_task_io_with_interactive_false_tty_false():
#     # Needs a real task id
#     taskIO = TaskIO(id, "echo "hello world" | cat", False, False)
#     assert output == "hello world"


# def test_task_io_with_interactive_true_tty_false():
#     import os
#     # Needs a real task id
#     taskIO = TaskIO(id, "cat", True, False)
#     os.write(sys.stdin.fileno(), "hello world")
#     assert output == "hello world"


# def test_task_io_with_valid_args():
#     # Needs a real task id
#     taskIO = TaskIO(id, "cat", True, False, ["-n"])
#     os.write(sys.stdin.fileno(), "hello world")
#     assert output == "     1    hello world"


# def test_run_with_tty_true_outside_of_tty():
#     # Needs a real task id
#     try:
#         taskIO = taskIO(id, "vi", True, True)
#     except Exception as e:
#         assert e.args[0] == "Must be running in a tty to pass the '--tty flag'." \
#         " Exiting"


# def test_task_io_thread_wrapper_with_normal_termination():
#     def normal_termination():
#         return True
    
#     # Needs a real task id
#     taskIO = TaskIO(id, "cat", False, False)
#     taskIO._thread_wrapper(normal_termination)
#     assert not taskIO.exception
#     taskIO.exit_event.set()


# def test_task_io_thread_wrapper_with_no_termination():
#     def no_termination():
#         while True:
#             pass

#     # Needs a real task id
#     taskIO = TaskIO(id, "cat", False, False)
#     taskIO._thread_wrapper(no_termination)
#     assert not taskIO.exception
#     taskIO.exit_event.set()


# def test_task_io_thread_wrapper_with_exception():
#     def raise_exception():
#         raise Exception("Exception")

#     # Needs a real task id
#     taskIO = TaskIO(id, "cat", False, False)
#     taskIO._thread_wrapper(raise_exception)
#     assert taskIO.exception


# def test_task_io_launch_nested_container_session_with_tty_false():
#     # Needs a real task id
#     # Needs a running http server
#     taskIO = TaskIO(id, "cat", False, False)


# def test_task_io_launch_nested_container_session_with_tty_true():
#     # Needs a real task id
#     # Needs a running http server
#     taskIO = TaskIO(id, "cat", False, False)


# def test_task_io_process_output_stream_valid_response():
#     # Needs a real task id
#     taskIO = TaskIO(id, "cat", False, False)
#     taskIO._process_output_stream(valid response)
#     #Check output_queue
#     assert taskIO.outout_queue.get() == thing I put on queue










