def extend_usage_docopt(doc, command_summaries):
    """Extends usage information with sub-command summaries

    :param doc: Usage documentation
    :type doc: str
    :param command_summaries: Commands and their summaries
    :type command_summaries: list of (str, str)
    :returns: Usage documetation with the sub-command summaries
    :rtype: str
    """

    doc += '\nThe dcos commands are:'
    for command, summary in command_summaries:
        doc += '\n\t{:15}\t{}'.format(command, summary.strip())

    return doc
