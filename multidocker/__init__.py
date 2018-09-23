#!/usr/bin/env python3
name = 'multidocker'

import sys

from multidocker import single_run, interactive_run
from test import testmode, run_doctests


class UnreachableCodeException(Exception):
    pass


def main():
    if testmode():
        run_doctests()
        sys.exit(0)


    if len(sys.argv) > 1:
        single_run()
    else:
        interactive_run()

    sys.exit(0)


if __name__ == '__main__':
    main()
