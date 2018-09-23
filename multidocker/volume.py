#!/usr/bin/env python3
from os import path


def is_absolute(path):
    return path[0] == '/'


def is_relative(path):
    return path[0] != '/' and '/' in path


def is_volume(path):
    return '/' not in path


def add_namespace(volume, app_name):
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
    # if we have no RO or RW marker
    # we'll defalt to RO
    if len(volume.split(':')) < 3:
        volume += ":ro"

    host_path = get_host_path(volume)

    if is_absolute(host_path):
        return volume

    elif is_relative(host_path):
        # if the host_path starts with this we strip it
        if host_path[:2] == "./":
            volume = volume[2:]
        return path.join(f"./{app_name}", volume)

    elif is_volume(host_path):
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
