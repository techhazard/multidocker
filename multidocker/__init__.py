#!/usr/bin/env python3
name = 'multidocker'

from os import path, listdir
from functools import reduce
from subprocess import PIPE, run
import yaml
import sys
import re


class UnreachableCodeException(Exception):
    pass


MULTIDOCKER_MODE = None
SUBCOMMANDS_TEXT = None


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


def open_app(app_dir):
    """
    EXPECTS:
        app_dir: path to a directory containing a docker-compose.yml

    RETURNS:
        a tuple
        - str: name of the directory
        - dict: loaded yaml

    THROWS:
        FileNotFoundError:
            when app_dir does not contain a (readable) compose file
    """
    app_definition = path.join(app_dir, 'docker-compose.yml')
    app_name = path.basename(app_dir)
    with open(app_definition, 'r') as app_file:
        return (app_name, yaml.safe_load(app_file),)


def path_is_absolute(path):
    return path[0] == '/'


def path_is_relative(path):
    return path[0] != '/' and '/' in path


def path_is_volume(path):
    return '/' not in path


def namespace_volume(volume, app_name):
    """

    Absolute mounts on the host

    >>> abs_mount = '/path/to/stuff:/path/to_stuff'
    >>> namespace_volume(abs_mount, 'namespace')
    '/path/to/stuff:/path/to_stuff:ro'

    >>> abs_mount_rw = '/path/to/stuff:/path/to_stuff:rw'
    >>> namespace_volume(abs_mount_rw, 'namespace')
    '/path/to/stuff:/path/to_stuff:rw'

    >>> abs_mount_ro = '/path/to/stuff:/path/to_stuff:ro'
    >>> namespace_volume(abs_mount_ro, 'namespace')
    '/path/to/stuff:/path/to_stuff:ro'


    Relative mounts on the host

    >>> rel_mount = './path/to/stuff:/path/to_stuff'
    >>> namespace_volume(rel_mount, 'namespace')
    './namespace/path/to/stuff:/path/to_stuff:ro'

    >>> rel_mount_rw = './path/to/stuff:/path/to_stuff:rw'
    >>> namespace_volume(rel_mount_rw, 'namespace')
    './namespace/path/to/stuff:/path/to_stuff:rw'

    >>> rel_mount_ro = './path/to/stuff:/path/to_stuff:ro'
    >>> namespace_volume(rel_mount_ro, 'namespace')
    './namespace/path/to/stuff:/path/to_stuff:ro'


    Docker volumes

    >>> vol_mount = 'name_of_volume:/path/to_stuff'
    >>> namespace_volume(vol_mount, 'namespace')
    'namespace_name_of_volume:/path/to_stuff:ro'

    >>> vol_mount_rw = 'name_of_volume:/path/to_stuff:rw'
    >>> namespace_volume(vol_mount_rw, 'namespace')
    'namespace_name_of_volume:/path/to_stuff:rw'

    >>> vol_mount_ro = 'name_of_volume:/path/to_stuff:ro'
    >>> namespace_volume(vol_mount_ro, 'namespace')
    'namespace_name_of_volume:/path/to_stuff:ro'

    """
    volume_parts = volume.split(':')

    # if we have no RO or RW marker
    # we'll defalt to RO
    if len(volume_parts) < 3:
        volume += ":ro"

    host_path = volume_parts[0]

    if path_is_absolute(host_path):
        return volume

    elif path_is_relative(host_path):
        # if the part starts with this we strip it
        if host_path[:2] == "./":
            volume = volume[2:]
        return path.join(f"./{app_name}", volume)

    elif path_is_volume(host_path):
        return f"{app_name}_{volume}"

    else:
        raise UnreachableCodeException()


def get_host_path(volume):
    """
    Get the first part of a docker volume entry.

    >>> docker_volume_string = "./path/on/host:/path/in/container:rw"
    >>> get_host_path(docker_volume_string)
    './path/on/host'
    """
    return volume.split(':')[0]


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

def namespace_app(app_tuple):
    """
    EXPECTS:
        app_tuple: a tuple
        - str: name to use for namespacing
        - dict: app to namespace

    RETURNS:
        dict: namespaced app
    """
    (app_name, app) = app_tuple

    # namespace networks, services and volumes in toplevel dict
    app['networks'] = namespace_or_create_dict(app, 'networks', app_name)
    app['services'] = namespace_or_create_dict(app, 'services', app_name)
    app['volumes']  = namespace_or_create_dict(app, 'volumes',  app_name)

    # namespace the contents of each service
    for svc_name, svc in app['services'].items():

        if 'hostname' not in svc:
            svc['hostname'] = svc_name

        if 'container_name' not in svc:
            svc['container_name'] = svc_name


        # namespace networks
        svc['networks'] = namespace_or_create_list(svc, 'networks', app_name)

        # add networks to toplevel that do not exist yet
        for net_name in svc['networks']:

            # if network is not in app's toplevel yet, we add it
            if net_name not in app['networks']:
                app['networks'][net_name] = {'internal': True }

            # OR if it is and it does not have an 'internal' key, we set it to true
            elif 'internal' not in app['networks'][net_name]:
                app['networks'][net_name]['internal'] = True


        if 'external' in svc and svc['external'] == True:
            del svc['external']
            svc['networks'].append('multidocker')
            app['networks']['multidocker'] = {'internal': False }


        if 'volumes' in svc:
            svc['volumes'] = [ namespace_volume(v, app_name) for v in svc['volumes'] ]
        else:
            svc['volumes'] = []

        for volume in svc['volumes']:
            host_path = volume.split(':')[0]

            if path_is_volume(host_path) and host_path not in app['volumes']:
                app['volumes'][host_path] = None


        if 'depends_on' in svc:
            svc['depends_on'] = [ f"{app_name}_{name}" for name in svc['depends_on'] ]

    return app


def combine_apps(app_list):
    return reduce(merge, app_list, {})


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


def run_doctests():
    import doctest
    doctest.testmod()


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


def get_compose_command():
    # we need to load the dockerfile from stdin if we're in multidocker mode
    if multidocker_mode():
        return ['docker-compose', '-f', '-']
    else:
        return ['docker-compose']


def is_an_app(dirname):
    """
    An app is defined as:
        a directory conaining a 'docker-compose.yml' file
    """
    return path.isfile(path.join(dirname, 'docker-compose.yml'))

def load_compose_file():
    if multidocker_mode():
        apps = [ open_app(directory) for directory in listdir() if is_an_app(directory) ]
        namespaced_apps = [ namespace_app(app) for app in apps ]
        return yaml.dump(combine_apps(namespaced_apps), encoding='utf-8')
    else:
        return None


def testmode():
    """
    we are in testmode when we run it as `multidocker --test`
    """
    return len(sys.argv) == 2 and sys.argv[1] == '--test'


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

def single_run():
    """
    We consider ourselves in single run mode when we were started with arguments.
    e.g. `multidocker ps` instead of `multidocker`
    """
    return len(sys.argv) > 1


def main():
    if testmode():
        run_doctests()
        sys.exit(0)

    compose_file = load_compose_file()

    if single_run():
        command = get_compose_command()
        command.extend(sys.argv[1:])
        run(command, input=compose_file)
        sys.exit(0)

    else:
        subcommands_text = get_subcommands_text()
        valid_subcommands = get_valid_subcommands(subcommands_text)

        print(interactive_helptext())

        while True:
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

            except EOFError:
                sys.exit(0)

    raise UnreachableCodeException()

if __name__ == '__main__':
    main()
