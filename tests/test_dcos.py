import dcos


def test_extend_usage_docopt():
    command_summaries = [
        ('first', 'first summary'),
        ('second', ' second summary '),
        ('third', 'third summary\n')
    ]

    expected = """
The dcos commands are:
\tfirst          \tfirst summary
\tsecond         \tsecond summary
\tthird          \tthird summary"""

    assert dcos._extend_usage_docopt('', command_summaries) == expected
