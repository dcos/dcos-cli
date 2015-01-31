import contextlib
import shutil
import tempfile


@contextlib.contextmanager
def tempdir():
    """A context manager for temporary directories.

    The lifetime of the returned temporary directory corresponds to the
    lexical scope of the returned file descriptor.

    :return: Reference to a temporary directory
    :rtype: file descriptor
    """

    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
