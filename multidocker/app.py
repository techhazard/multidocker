#!/usr/bin/env python3
from os import path
from functools import reduce

from ruamel.yaml import safe_load

from multidocker import volume
from multidocker.volume import get_host_path
from multidocker.volume import is_volume as path_is_volume
from multidocker.util import namespace_or_create_dict, namespace_or_create_list, merge


def combine(app_list):
    return reduce(merge, app_list, {})


def is_an_app(dirname):
    """
    An app is defined as:
        a directory conaining a 'docker-compose.yml' file
    """
    return path.isfile(path.join(dirname, 'docker-compose.yml'))


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
        return (app_name, safe_load(app_file),)


def add_namespace(app_tuple):
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
            svc['volumes'] = [ volume.add_namespace(v, app_name) for v in svc['volumes'] ]
        else:
            svc['volumes'] = []

        for vol in svc['volumes']:
            host_path = get_host_path(vol)

            if path_is_volume(host_path) and host_path not in app['volumes']:
                app['volumes'][host_path] = None


        if 'depends_on' in svc:
            svc['depends_on'] = [ f"{app_name}_{name}" for name in svc['depends_on'] ]

    return app
