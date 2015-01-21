def extend_usage_docopt(doc, command_summaries):
    doc += '\nThe dcos commands are:'
    for command, summary in command_summaries:
        doc += '\n\t{:15}\t{}'.format(command, summary.strip())

    return doc
