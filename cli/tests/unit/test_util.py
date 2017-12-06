import dcoscli.util as util


def test_prompt_with_choices():
    real_read = util._read_response

    def fake_read():
        return "3"

    util._read_response = fake_read
    result = util.prompt_with_choices(['der', 'die', 'das'])
    util._read_response = real_read

    assert result == 'das'


def test_prompt_with_choices_and_invalid_input():
    real_read = util._read_response

    def fake_read():
        return "invalid"

    util._read_response = fake_read
    result = util.prompt_with_choices(['der', 'die', 'das'])
    util._read_response = real_read

    assert result is None
