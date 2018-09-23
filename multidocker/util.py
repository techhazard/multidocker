#!/usr/bin/env python3


def namespace_or_create_dict(dictionary, dict_key, ns):
    """
    Add namespacing to a dict's element's keys

    EXPECTS:
        dictionary: dict who's element's key to add namespacing to
        dict_key  : key in dict to add namespacing to
        ns        : namespace to add

    RETURNS:
        the sub dictionary of dictionary[dict_key] which has been namespaced
        or an empty dictionary if it did not exist

    EXAMPLES:
    >>> d = {"networks": {'some_net': {}, 'other_net': {}}}
    >>> d['networks'] = namespace_or_create_dict(d, 'networks', 'namespace')
    >>> d
    {'networks': {'namespace_some_net': {}, 'namespace_other_net': {}}}

    >>> d = {"networks": {}}
    >>> d['volumes'] = namespace_or_create_dict(d, 'volumes', 'namespace')
    >>> d
    {'networks': {}, 'volumes': {}}

    """
    if dict_key not in dictionary:
        return {}
    else:
        return { f"{ns}_{k}": v for k, v in dictionary[dict_key].items() }


def namespace_or_create_list(dictionary, list_key, ns):
    if list_key not in dictionary:
        return []
    else:
        return [ f"{ns}_{item}" for item in dictionary[list_key] ]


def merge(source, destination):
    """
    https://stackoverflow.com/a/20666342
    Deep merge two dictionaries

    >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> merge(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    True
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge(value, node)
        else:
            destination[key] = value

    return destination
