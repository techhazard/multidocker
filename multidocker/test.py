#!/usr/bin/env python3
import sys

def run_doctests():
    import doctest
    doctest.testmod()


def testmode():
    """
    we are in testmode when we run it as `multidocker --test`
    """
    return len(sys.argv) == 2 and sys.argv[1] == '--test'

