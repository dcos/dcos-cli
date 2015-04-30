from dcos import options


def test_extend_usage_docopt():
    command_summaries = [
        ('first', 'first summary'),
        ('second', ' second summary '),
        ('third', 'third summary\n')
    ]

    expected = """
\tfirst          \tfirst summary
\tsecond         \tsecond summary
\tthird          \tthird summary"""

    assert options.make_command_summary_string(command_summaries) == expected


def test_make_generic_usage_message():
    assert (options.make_generic_usage_message('some generic message') ==
            'Unknown option\nsome generic message')
