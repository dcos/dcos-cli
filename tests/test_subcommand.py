from dcos import subcommand


def test_noun():
    assert subcommand.noun("some/path/to/dcos-command") == "command"


def test_hyphen_noun():
    assert subcommand.noun("some/path/to/dcos-sub-command") == "sub-command"


def test_rewrite_binary_url_with_incorrect_scheme():
    binary_url = ("http://dcos.example.com/package/resource"
                  "?url=https://binary.example.com")

    dcos_url = "https://dcos.example.com"

    rewritten_url = subcommand._rewrite_binary_url(binary_url, dcos_url)

    assert rewritten_url == ("https://dcos.example.com/package/resource"
                             "?url=https://binary.example.com")


def test_rewrite_binary_url_with_correct_scheme():
    binary_url = ("https://dcos.example.com/package/resource"
                  "?url=https://binary.example.com")

    dcos_url = "https://dcos.example.com"

    rewritten_url = subcommand._rewrite_binary_url(binary_url, dcos_url)

    assert rewritten_url == binary_url


def test_rewrite_binary_url_with_external_url():
    binary_url = ("https://not-dcos.example.com/package/resource"
                  "?url=https://binary.example.com")

    dcos_url = "https://dcos.example.com"

    rewritten_url = subcommand._rewrite_binary_url(binary_url, dcos_url)

    assert rewritten_url == binary_url
