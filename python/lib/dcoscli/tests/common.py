import six


def assert_same_elements(list1, list2):
    """Tests whether the second argument is a rearrangement of the first.

    This method will work even if the list elements are mutable and/or cannot
    be sorted. A common use case is comparing lists of JSON objects, since
    the objects are usually implemented with dicts.

    :param list1: the first list
    :type: list
    :param list2: the second list
    :type: list
    :rtype: None
    """
    list2 = list2.copy()
    for element in list1:
        list2.remove(element)
    assert list2 == []


def file_bytes(path):
    """ Read all bytes from a file

    :param path: path to file
    :type path: str
    :rtype: bytes
    :returns: bytes from the file
    """

    with open(path) as f:
        return six.b(f.read())
