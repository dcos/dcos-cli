from dcos import options


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

    assert options.extend_usage_docopt('', command_summaries) == expected
