#!/usr/bin/env python3
import re
import sys
import yaml
from os import listdir, path
from subprocess import run, PIPE

from app import is_an_app, open_app
from app import combine as combine_apps
from app import add_namespace as namespace_app


MULTIDOCKER_MODE = None


def multidocker_mode():
    """
    Check for multidocker mode.

    We run in multidocker mode if there's no 'docker-compose.yml' in the current directory
    We cache this with a global value to reduce disk lookups
    """
    global MULTIDOCKER_MODE

    if MULTIDOCKER_MODE is None:
        MULTIDOCKER_MODE = not path.isfile('docker-compose.yml')

    return MULTIDOCKER_MODE


def load_compose_file():

    if multidocker_mode():

        apps = [ open_app(directory) for directory in listdir() if is_an_app(directory) ]

        namespaced_apps = [ namespace_app(app) for app in apps ]

        return yaml.dump(combine_apps(namespaced_apps), encoding='utf-8')

    else:
        return None


def get_compose_command():
    # we need to load the dockerfile from stdin if we're in multidocker mode
    if multidocker_mode():
        return ['docker-compose', '-f', '-']
    else:
        return ['docker-compose']


def single_run():
    """
    We consider ourselves in single run mode when we were started with arguments.
    e.g. `multidocker ps` instead of `multidocker`
    """
    compose_file = load_compose_file()

    command = get_compose_command()
    command.extend(sys.argv[1:])

    run(command, input=compose_file)


def interactive_run():
    compose_file = load_compose_file()

    subcommands_text = get_subcommands_text()
    valid_subcommands = get_valid_subcommands(subcommands_text)

    print(interactive_helptext())

    while True:#
        try:
            input_string = input('multidocker> ')
            input_parts = input_string.split(" ")
            subcommand = input_parts[0]
            if subcommand not in valid_subcommands:
                print(f"'{subcommand}' is not a valid docker-compose subcommand. Valid subcommands are:")
                print(", ".join(valid_subcommands))
                print("press ctrl+d to quit multidocker")
                continue

            if subcommand == 'help':
                print(subcommands_text)
                continue

            command = get_compose_command()
            command.extend(input_parts)
            run(command, input=compose_file)

        except KeyboardInterrupt:
            print("\npress ctrl+d to quit multidocker")
            continue

        # exit on ctrl+d
        except EOFError:
            return


def get_subcommands_text():
    """
    Get the "Commands:" section of `docker-compose help`
    """
    # TODO: upgrade to python 3.7 to replace `.stdout` with `text=True`
    # see https://docs.python.org/3.7/library/subprocess.html#subprocess.run
    helptext = run(['docker-compose', 'help'], encoding='utf-8', stdout=PIPE).stdout

    commands_regex = r"(?:Commands:\n)(?:  (\w+).*\n?)+"
    return re.search(commands_regex, helptext)[0]


def get_valid_subcommands(subcommands_text):
    """
    parse the "Commands:" section of `docker-compose help` and retrieve the commands list
    """
    command_regex = r"^  (\w+)"
    command_matches = re.finditer(command_regex, get_subcommands_text(), re.M)

    return [m.group(1) for m in command_matches]


def interactive_helptext():
    return """Interactive Mode

You can run docker subcommands here, like so:

multidocker> ps
	Name		Command   State   Ports
---------------------------------------
container_name	/init     Up
multidocker>

press ctrl+d to quit interactive mode
"""
