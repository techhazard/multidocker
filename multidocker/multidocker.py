#!/usr/bin/env python3
import re
import sys
from ruamel import yaml
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


def get_external_command():
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

    command = get_external_command()
    command.extend(sys.argv[1:])

    run(command, input=compose_file)


def get_command_input():
    # TODO: add readline support
    input_string = input('multidocker> ')
    return input_string.split(" ")


def write_composefile(compose_file):
    with open('multidocker.yml', 'w') as f:
        f.write(load_compose_file())


VALID_SUBCOMMANDS = None
VALID_MULTIDOCKER_COMMANDS = ['cat', 'exit', 'help', 'reload', 'write', 'quit']
def is_valid_dockercommand(subcommand):
    global VALID_SUBCOMMANDS

    if VALID_SUBCOMMANDS is None:
        subcommands_text = get_subcommands_text()
        VALID_SUBCOMMANDS = get_valid_subcommands(subcommands_text)
        VALID_SUBCOMMANDS.remove('help')

    if subcommand not in VALID_SUBCOMMANDS:
        print(f"'{subcommand}' is not a valid docker-compose or multidocker subcommand.")
        print("\nValid docker-compose subcommands are:")
        print("\t" + ", ".join(VALID_SUBCOMMANDS))
        print("\nValid multidocker subcommands are:")
        print("\t" + ", ".join(VALID_MULTIDOCKER_COMMANDS))
        print("\npress ctrl+d to quit multidocker")
        return False

    return True


def interactive_run():
    compose_file = load_compose_file()

    print(interactive_helptext())

    while True:#
        try:
            input_parts = get_command_input()
            subcommand = input_parts[0]

            if subcommand == 'cat':
                print(compose_file)

            elif subcommand == 'write':
                write_composefile(compose_file)

            elif subcommand == 'help':
                print(interactive_helptext())

            elif subcommand == 'reload':
                compose_file = load_compose_file()

            elif subcommand in ['exit', 'quit']:
                return

            elif is_valid_dockercommand(subcommand):
                command = get_external_command()
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
    # TODO: upgrade to python 3.7 to replace `PIPE` and `.stdout` with `text=True`
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


INTERACTIVE_HELPTEXT = None
def interactive_helptext():
    global INTERACTIVE_HELPTEXT

    if INTERACTIVE_HELPTEXT == None:
        subcommands_text = get_subcommands_text()
        INTERACTIVE_HELPTEXT = f"""Interactive Mode

You can run docker subcommands here, like so:
\t------------------------------------------
\t| multidocker> ps                        |
\t|     Name        Command  State   Ports |
\t| ---------------------------------------|
\t| container_name  /init    Up            |
\t| multidocker>                           |
\t------------------------------------------

{subcommands_text}
Multidocker Commands:
  cat                Output combined compose file to disk
  help               Show this help text
  reload             Reload the compose files from disk
  write              Write the combined compsose file to disk
  quit, exit         Exit interactive mode (ctrl+d also works)
"""
    return INTERACTIVE_HELPTEXT
