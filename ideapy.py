#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
IdeaPy is a simple WWW server built on top of CherryPy, with Python code execution feature. Example usage:
$ python3 -m ideapy

go to http://localhost:8080/

Homepage: https://github.com/skazanyNaGlany/ideapy
"""

import os

#activate default Virtualenv if exists
venv_activate_script = os.path.join('venv', 'bin', 'activate_this.py')
venv_dir = None
if os.path.exists(venv_activate_script):
    with open(venv_activate_script) as f:
        code = compile(f.read(), venv_activate_script, 'exec')
        exec(code, {'__file__' : venv_activate_script})
        venv_dir = os.path.realpath(os.path.dirname(venv_activate_script)).replace(os.path.sep + 'bin', '')


import sys
import cherrypy
import math
import mimetypes
import importlib
import tempfile
import fnmatch
import socket
import binascii
import resource
import builtins
import time
import json
import pprint
import gc

from urllib.parse import urlparse
from wsgiref.handlers import format_date_time
from typing import List, Dict, Union, Optional
from collections import OrderedDict


class IdeaPy:
    DEBUG_MODE = False
    RELOADER = True
    RELOADER_INTERVAL = 3
    OWN_IMPORTER = True

    _VERSION = '0.1.6'
    _LOG_SIGN = 'IDEAPY'
    _PYTHON_MIN_VERSION = (3, 4)
    _CHERRYPY_MIN_VERSION = [8, 1]
    _DEFAULT_VIRTUAL_HOST_NAME = '_default_'
    _CACHED_SCOPES_TOTAL = 1024
    _CONF_FILE_NAME = 'ideapy.conf.json'
    _DEFAULT_VENV = 'venv'
    _MAIN_FAVICON = '/favicon.ico'
    _CONF_ALLOWED_0_LVL_KEYS = {
        'DEBUG_MODE' : bool,
        'RELOADER': bool,
        'RELOADER_INTERVAL': int,
        'OWN_IMPORTER': bool,
        '_virtual_hosts': False
    }
    _CONF_ALLOWED_VHOST_KEYS = {
        'document_roots': list,
        'server_name': str,
        'listen_port': int,
        'listen_ips': list,
        'server_aliases': list,
        'directory_index': list,
        'index_ignore': list,
        'ssl_certificate': str,
        'ssl_private_key': str,
        'ssl_certificate_chain': str,
        'opt_indexes': bool,
        'not_found_document_root': str
    }


    """
    :type _servers: Dict[str, cherrypy._cpserver.Server]
    :type _virtual_hosts: Dict[str, dict]
    """
    def __init__(self):
        assert sys.version_info >= IdeaPy._PYTHON_MIN_VERSION
        self._assert_cherrypy_version()

        self._servers = {}
        self._virtual_hosts = {}
        self._virtual_host_root = '/'
        self._server_main_root_dir = self._clean_path(os.path.realpath(os.getcwd()) + os.path.sep)
        self._server_name = socket.gethostname().lower()
        self._id = hex(id(self))
        self._supporting_modules = {}
        self._pid = os.getpid()
        self._org___import__ = None
        self._org_import_module = None
        self._last_reloaded = int(time.time())
        self._reloading = False
        self._cached_scopes = {}

        self._list_html_template = """
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
        <html>
            <head>
                <title>Index of {pathname}</title>

                <style>
                    table {{
                        border-collapse: collapse;
                    }}

                    td {{
                        padding-left: 25px;
                        padding-right: 25px;
                    }}

                    a {{
                        text-decoration: none;
                        vertical-align: middle;
                    }}

                    img {{
                        vertical-align: middle;
                        margin-top: 5px;
                        margin-bottom: 5px;
                    }}

                    a:hover {{
                        text-decoration: underline;
                    }}
                </style>
            </head>

            <body>
                <h1>Index of {pathname}</h1>

                <pre>
                    <table>
                        <thead>
                            <tr>
                                <th><a href="?C=N;O=A">Name</a></th>
                                <th><a href="?C=M;O=D">Last modified</a></th>
                                <th><a href="?C=S;O=A">Size</a></th>
                            </tr>

                            <tr>
                                <th colspan="3"><hr></th>
                            </tr>
                        </thead>

                        <tbody>
                            <tr>
                                <td>
                                    <img src="/server_statics/go_back.png"/> <a href="{parent_pathname}">Parent Directory</a>
                                </td>
                                <td></td>
                                <td></td>
                            </tr>

                            <tr><td colspan="3">&nbsp;</td></tr>

                            {entries}
                        </tbody>
                    </table>
                </pre>
            </body>
        </html>
        """

        self._list_html_template_file = """
        <tr>
            <td><img src="/server_statics/{type}.png"/> <a href="{full_pathname}">{pathname}</a></td>
            <td>{modified}</td>
            <td>{size}</td>
        </tr>
        """

        self._statics = {
            'folder.png' : {
                'content_type' : 'image/png',
                'data' : binascii.a2b_base64('iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEwAACxMBAJqcGAAAAPRJREFUSIntlb1OAlEQRr877JoYNNDgM6ANJD6FdiRQ0NBt4wtYUAiVVpbE2NEaG0t8CDqgMbGGbRaWDXHXO0OBdPy4yd7unnrmnOkGMIwCgHJ3UIPwiwJd7BsU8PuvK3df7Vs/TYA224flm0uo7sa50VX3s5EmoADgsjOQNEtHEfgg9iYPNx8OAFRKDprlU5ydqEz8YSKlt/GqPwGKqvo8fCqc5+8jTZnIt+RzjCBcPKrr3lgrcrO1/yGcMJmSA4Ail4zJt9iADdiADfwnIKyNyYU16Gc+W8BARFhjNfcDR8dRazn7fj32k9PCwlMQeVk6d7IG1N5P4ApKfBMAAAAASUVORK5CYII=')
            },
            'file.png': {
                'content_type': 'image/png',
                'data': binascii.a2b_base64('iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEwAACxMBAJqcGAAAAPdJREFUSInt1rFKBDEQBuDvPPUQfJ+rhLWxsj57n8FWuMrOJ9HGSi0EsfIQC5/Bxv464U6LnBLi7iZ7arc/LCEz/84/kwlJBn5ijAMMa3wprjFrI2zUBL/CTkHwCnfYK+B+4xRnhdwpbvDWJpJWMMR7h4QeMcFFk0gqsA4ecITLOpHfClTCUu3jRWj6OCakO6VajfcFwecYRfNXbGMr/n+zNNUaPK++GNOU9Bc9aMW/C+SW6AS7Gc4c503OXAUfGT8s25y5ChozK0XfA/oe6HuQzJfCkbsuRljEhrSCW+HSp9vV+RX8GIexcVBD7PJsibEQHgFPsfETWgYrD24yukcAAAAASUVORK5CYII=')
            },
            'go_back.png': {
                'content_type': 'image/png',
                'data': binascii.a2b_base64('iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAACk0lEQVR4XuWUT2gTQRTGv9nZbrNpYrX/jCVNN2u1rV6EWsRTxYtNGrzYs1AR9CSIl/YiUtBtLgURDx6KIHjxz01boSK2PQkVKXhSSVKloK2haW23SbM7o5FZCCXZJlC8+IOPGXZ23vfeDG/wf6JFjeuoEAlVwYkWi98FML7nBj09D2q0gfiz5gP+yxDsmcHxM7d86cDq22CgMXK6t9uLKpCxC+Hztw+aNp0NB5u1ru6wwiWKaiBw4fA5o4PJZK5Db21uC7XSlUwWwRYfpl+/g8VY1uWqzNTkcKNrBXq/0cskMt11NORvammSfmS2wBiw+iuHvr4egMNTKl3bZpiZeS+7HlF7ZCzCKXl6rFOr8++vR/pPUM7xl7XNbaybKAkhQEu9x/0O9AHjkiSRe12dutdT58WamcdOhFnJ75bNyxu0R4yzjPOJziMaSI2C9HoWHAIOEMLBxdyBi0UCUhiw7ZHKGyxOjbwJx8bGk6lvV3Vd89p5C2bOQjXsU6l7HyRfDN/I5qz4p89JU6GAt1ZGNVg2270PUi+HR7VoPJNILBpt7W1ej0KR3bZRoFahUBUZhJS4ZBDkLVZ5H+ixO0Mc9P6hYKtKJBm5vA2fWoPFRIJxBo7ysNTkiCIM3AlF4oOU8kdNgYBKZQWUEiwlU4CZU1EGWW3gX6au5VAhJNQ/GtWiY5snLk7wU1cecy1qcAAeoVoAijhuWuljRwDIYrP69dXNufzG8mAmvWxumSYEviLVCalCimMmuwQvFl2aHf8QODk0CI4nIqhftIFdJMsZnblUyqCEpML4ff7hx82l+Qucs5+OsZBU/J+jchUw4V6ACzERyFpZeL7QwBEDsFG8XqKSvMh2VyQnS0fOvhIGTIjjX/Eb/Bru7c4wfowAAAAASUVORK5CYII=')
            },
            'favicon.ico': {
                'content_type': 'image/x-icon',
                'data': binascii.a2b_base64('AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/AAAA/3QAAP/YAAD/9AAA//QAAP/aAAD/lAAA/w4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/1IAAP//AAD//wAA//8AAP//AAD/ugAA/8YAAP9yAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP90AAD//wAA//8AAP//AAD//wAA/2gAAP+AAAD/hAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/CgAA/yoAAP8oAAD/dgAA//8AAP//AAD/7AAA/8YAAP/GAAD/xgAA/2oAAAAAAAAAAAAAAAAAAAAAAAD/JAAA/+YAAP//AAD/2gAA/3QAAP//AAD//wAA/9YAAP9+AAD/fgAA/34AAP9+AAD/fgAA/3wAAP84AAAAAAAA/5oAAP//AAD//wAA/94AAP9yAAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//AAA/1IAAP/YAAD//wAA//8AAP/wAAD/SgAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP/CAAD/7AAA//8AAP//AAD//wAA/4YAAP9aAAD/ngAA/6QAAP+mAAD/qAAA/8YAAP//AAD//wAA//8AAP//AAD/7gAA/+IAAP//AAD//wAA//8AAP//AAD/0gAA/64AAP+qAAD/pgAA/6IAAP9qAAD/dAAA//8AAP//AAD//wAA//YAAP+wAAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA/1gAAP/kAAD//wAA//8AAP/iAAD/QAAA//oAAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP+EAAD/0AAA//8AAP//AAD/pAAAAAAAAP8sAAD/dAAA/3oAAP96AAD/fAAA/3wAAP9+AAD/0gAA//8AAP//AAD/hAAA/84AAP//AAD/6AAA/yoAAAAAAAAAAAAAAAAAAAAAAAD/aAAA/9AAAP/QAAD/0AAA/+4AAP//AAD//wAA/4QAAP8eAAD/JAAA/wgAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/3oAAP+IAAD/VgAA//8AAP//AAD//wAA//8AAP+CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP9kAAD/0gAA/7oAAP//AAD//wAA//8AAP//AAD/WgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/CAAA/4gAAP/QAAD/7gAA//IAAP/SAAD/dAAA/wAAAAAAAAAAAAAAAAAAAAAA/B8AAPgfAAD4TwAA+B8AAIj/AAAIAQAACAAAAAQAAAAAMAAAABAAAIAAAAD/AQAA+A8AAPoPAAD4HwAA+D8AAA==')
                # 'data': binascii.a2b_base64(
                #     'AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAFsAAACzAAAA3QAAAN4AAAC1AAAAYAAAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAAAD/AAAA/wAAAP8AAAD/AAAAvAAAAI8AAACIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADCAAAA/wAAAP8AAAD/AAAA/wAAAKcAAABwAAAAyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAwwAAAP8AAAD/AAAA/wAAAMAAAAC/AAAAvwAAAJYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHgAAADCAAAAlQAAAMMAAAD/AAAA/wAAAP8AAADFAAAAxAAAAMQAAADEAAAAxAAAAMMAAACFAAAAAAAAAE8AAAD/AAAA/wAAAMIAAADDAAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAFAAAACeAAAA/wAAAP8AAADZAAAApAAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAACqAAAAxgAAAP8AAAD/AAAA/wAAAIMAAACwAAAA0wAAANMAAADTAAAA0wAAAOsAAAD/AAAA/wAAAP8AAAD/AAAA1QAAAMkAAAD/AAAA/wAAAP8AAAD+AAAAzQAAALAAAACwAAAAsAAAALAAAACUAAAAmAAAAP8AAAD/AAAA/wAAANIAAAClAAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAJ8AAADeAAAA/wAAAP8AAACsAAAAWQAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAADIAAAAvAAAAP8AAAD/AAAAZgAAAAAAAAB/AAAA3QAAAOYAAADmAAAA5gAAAOYAAADmAAAA/gAAAP8AAAD/AAAAyQAAAKoAAADlAAAAqQAAAAYAAAAAAAAAAAAAAAAAAAAAAAAAeAAAAJ0AAACdAAAAnQAAAP0AAAD/AAAA/wAAAMkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMMAAACRAAAAtwAAAP8AAAD/AAAA/wAAAP8AAADJAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACuAAAAdgAAAKMAAAD/AAAA/wAAAP8AAAD/AAAAngAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIQAAAKEAAADXAAAA7QAAAO0AAADXAAAAlwAAAA8AAAAAAAAAAAAAAAAAAAAA/D8AAPAPAADwLwAA8A8AAMABAACAAQAAAAAAAAAAAAAAAAAAAAAAAIABAADAAQAA+A8AAPAPAAD0DwAA+B8AAA==')
            }
        }

        self._log('{version} initializing, _server_main_root_dir={_server_main_root_dir}, _server_name={_server_name}'.format(
            version = IdeaPy._VERSION,
            _server_main_root_dir = self._server_main_root_dir,
            _server_name = self._server_name
        ))

        self._fix_sys_path()
        self._parse_conf_json()

        if not self._virtual_hosts:
            self.add_virtual_host()

        self._dump_conf_json()

        if venv_dir:
            self._log('using virtualenv {venv_dir}'.format(venv_dir=venv_dir))

        self._log('CherryPy version is {version}'.format(version = cherrypy.__version__))
        self._log('Python version is {version} ({release})'.format(version = IdeaPy._python_version_to_str(), release = sys.version_info.releaselevel))
        self._log('RELOADER is', 'ON' if self.RELOADER else 'OFF')
        self._log('OWN_IMPORTER is', 'ON' if self.OWN_IMPORTER else 'OFF')
        self._log('ready, waiting for start()')


    @staticmethod
    def _python_version_to_str():
        ver_list = [str(sys.version_info.major), str(sys.version_info.minor), str(sys.version_info.micro)]
        return '.'.join(ver_list)


    def _fix_sys_path(self):
        # site_packs = os.path.sep + 'site-packages'
        libs = os.path.sep + 'lib' + os.path.sep

        for index, ipath in enumerate(sys.path):
            if ipath.startswith(self._server_main_root_dir) and ipath != self._server_main_root_dir and ipath.find(libs) == -1:
                del sys.path[index]
                self._log('removed', ipath, 'from sys.path')

        if not self._server_main_root_dir in sys.path:
            sys.path.append(self._server_main_root_dir)
            self._log('added', self._server_main_root_dir, 'to sys.path')


    def _dump_conf_json(self):
        if os.path.exists(IdeaPy._CONF_FILE_NAME):
            return

        conf_data = {}
        for ikey, ivalue in IdeaPy._CONF_ALLOWED_0_LVL_KEYS.items():
            conf_data[ikey] = getattr(self, ikey)

        conf_data['_virtual_hosts'] = []
        for ikey, ivalue in self._virtual_hosts.items():
            vhost = {}
            for vkey, vvalue in ivalue.items():
                if vkey in IdeaPy._CONF_ALLOWED_VHOST_KEYS:
                    vhost[vkey] = vvalue

            conf_data['_virtual_hosts'].append(vhost)

        self._log('dumping {conf_name}'.format(conf_name=IdeaPy._CONF_FILE_NAME))
        open(IdeaPy._CONF_FILE_NAME, 'w').write(json.dumps(conf_data, indent=4, sort_keys=True))


    def _parse_conf_json(self):
        if not os.path.exists(IdeaPy._CONF_FILE_NAME):
            self._log('no {conf_name}'.format(conf_name = IdeaPy._CONF_FILE_NAME))
            return

        self._log('parsing {conf_name}'.format(conf_name=IdeaPy._CONF_FILE_NAME))

        json_conf = json.loads(open(IdeaPy._CONF_FILE_NAME).read())
        assert isinstance(json_conf, dict), 'config must be valid JSON, got {got}'.format(got = str(json_conf))

        for ikey, ivalue in json_conf.items():
            if not ikey in IdeaPy._CONF_ALLOWED_0_LVL_KEYS:
                self._log('unknown level 0 key {key}'.format(key = ikey))

            if IdeaPy._CONF_ALLOWED_0_LVL_KEYS[ikey] is not False:
                assert isinstance(ivalue, IdeaPy._CONF_ALLOWED_0_LVL_KEYS[ikey]), '{key} must be {type_name}'.format(key = ikey, type_name = str(IdeaPy._CONF_ALLOWED_0_LVL_KEYS[ikey]))

                setattr(self, ikey, ivalue)

        if '_virtual_hosts' in json_conf:
            assert isinstance(json_conf['_virtual_hosts'], list), '_virtual_hosts must be a list, got {got}'.format(got = str(json_conf['_virtual_hosts']))

            new_count = 0
            for ivirtual_host in json_conf['_virtual_hosts']:
                assert isinstance(ivirtual_host, dict), 'virtual host must be a dict, got {got}'.format(got = str(ivirtual_host))
                for ikey, ivalue in ivirtual_host.items():
                    assert isinstance(ivalue, IdeaPy._CONF_ALLOWED_VHOST_KEYS[ikey]), '{key} must be {type_name}'.format(key=ikey, type_name=str(IdeaPy._CONF_ALLOWED_VHOST_KEYS[ikey]))

                self.add_virtual_host(**ivirtual_host)
                new_count += 1

                self._log('found', str(new_count), 'virtual host(s)')


    @staticmethod
    def setup_cherrypy(unsubscribe:bool = True):
        cherrypy.config.update({
            'tools.sessions.on': True,
            'tools.sessions.storage_class': cherrypy.lib.sessions.FileSession,
            'tools.sessions.storage_path': tempfile.gettempdir(),

            #one year
            'tools.sessions.timeout': 525600,

            # we will lock/unlock session manually by cherrypy.session.acquire_lock() and cherrypy.session.release_lock()
            # see http://docs.cherrypy.org/en/latest/pkg/cherrypy.lib.html#locking-sessions
            # 'tools.sessions.locking': 'early',
            'tools.sessions.locking': 'explicit',

            'log.screen': True,
            # 'engine.autoreload.on': True,

            # #disable response timeout monitor
            # 'engine.timeout_monitor.on': False,

            'environment': 'production'
        })

        if unsubscribe:
            cherrypy.server.unsubscribe()


    def _clean_path(self, path:str) -> str:
        """
        will return path without additional slashes
        """
        double_slash = os.path.sep + os.path.sep
        while path.find(double_slash) != -1:
            path = path.replace(double_slash, os.path.sep)

        return path


    def _convert_size(self, size:int) -> str:
        """
        source http://stackoverflow.com/questions/5194057/better-way-to-convert-file-sizes-in-python (5 post)
        """
        if (size == 0):
            return '0B'

        size_name = ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')

        i = int(math.floor(math.log(size, 1024)))
        p = math.pow(1024, i)
        s = round(size / p, 2)

        return '%s %s' % (s, size_name[i])


    def _assert_cherrypy_version(self):
        msg = 'CherryPy {major}.{minor} or newer required (current {current})'.format(
            major = IdeaPy._CHERRYPY_MIN_VERSION[0],
            minor = IdeaPy._CHERRYPY_MIN_VERSION[1],
            current = cherrypy.__version__
        )

        cherrypy_version = [int(i) for i in cherrypy.__version__.split('.')]

        assert cherrypy_version[0] >= IdeaPy._CHERRYPY_MIN_VERSION[0], msg

        if cherrypy_version[0] == IdeaPy._CHERRYPY_MIN_VERSION[0]:
            #check revision
            assert cherrypy_version[1] >= IdeaPy._CHERRYPY_MIN_VERSION[1], msg


    def _log(self, *objects):
        cherrypy.log('{log_sign} {_id} {msg}'.format(
            log_sign = self._LOG_SIGN,
            _id = self._id if self.DEBUG_MODE else '',
            msg = ' '.join(objects)
        ))


    def _add_server(self,
                   port:int,
                   ip:str = '127.0.0.1',
                   ssl_certificate:str = '',
                   ssl_private_key:str = '',
                   ssl_certificate_chain:str = ''
                   ) -> Union[cherrypy._cpserver.Server, None]:
        main_key = ip + ':' + str(port)
        if main_key in self._servers:
            self._log('server {key} already exists, skipping'.format(key = main_key))
            return

        key2 = '0.0.0.0:' + str(port)
        if key2 in self._servers:
            self._log('server {key} already exists (for {ip}), skipping'.format(key = key2, ip = ip))
            return

        if ip == '0.0.0.0':
            #user want to add server for 0.0.0.0
            #check if there is another server that listen on other ip than 0.0.0.0
            #on the same port
            port_sign = ':' + str(port)
            servers_keys = list(self._servers.keys())
            for key in servers_keys:
                if key.endswith(port_sign):
                    self._log('server {key} already exists (for {ip}), removing'.format(key=key, ip=ip))

                    self._servers[key].unsubscribe()
                    del self._servers[key]

        server = cherrypy._cpserver.Server()
        server._socket_host = ip
        server.socket_port = port

        if ssl_certificate:
            server.ssl_module = 'builtin'
            server.ssl_certificate = ssl_certificate
        if ssl_private_key:
            server.ssl_private_key = ssl_private_key
        if ssl_certificate_chain:
            server.ssl_certificate_chain = ssl_certificate_chain

        server.subscribe()

        self._servers[main_key] = server

        if self.DEBUG_MODE:
            self._log('added server {key}'.format(key = main_key))

        return server


    def _parse_ip(self, ip:str, default_port:int) -> dict:
        """
        parse IP to ip and port
        """
        parts = ip.split(':')
        if len(parts) < 2:
            parts.append(default_port)

        return {
            'ip' : parts[0],
            'port' : int(parts[1])
        }


    def _check_add_virtual_host_args(self,
                                     document_roots:List[str],
                                     server_name:str,
                                     listen_port:Union[int, str],
                                     listen_ips:List[str],
                                     server_aliases:List[str],
                                     directory_index:List[str],
                                     index_ignore:List[str],
                                     ssl_certificate,
                                     ssl_private_key,
                                     ssl_certificate_chain:str,
                                     opt_indexes:bool,
                                     not_found_document_root:str = None):
        assert isinstance(document_roots, list), 'document_roots must be a list of strings'
        assert document_roots, 'document_roots must be non-empty (full pathname)'

        for idocument_root in document_roots:
            assert isinstance(idocument_root, str), 'document_roots must be a list of strings'

        assert isinstance(server_name, str), 'server_name must be a string, got={server_name}'.format(server_name = str(server_name))
        assert server_name != '', 'server_name must be non-empty (domain name)'

        correct_listen_port = True
        if isinstance(listen_port, int):
            correct_listen_port = listen_port >= 1 and listen_port <= 65535
        elif isinstance(listen_port, str):
            correct_listen_port = listen_port == '*'

        assert correct_listen_port, 'listen_port must be >= 1 and <= 65535 or *, got={listen_port}'.format(listen_port=listen_port)

        assert isinstance(listen_ips, list), 'listen_ips must be a list, got={listen_ips}'.format(listen_ips = str(listen_ips))
        assert len(listen_ips) > 0, 'listen_ips must be non-empty (list of IPs)'

        if server_aliases:
            assert isinstance(server_aliases, list), 'server_aliases must be a list of strings, got={server_aliases}'.format(server_aliases = str(server_aliases))

            for alias in server_aliases:
                assert isinstance(alias, str), 'server alias must be non-empty string, got={alias}'.format(alias = str(alias))

        if directory_index:
            assert isinstance(directory_index, list), 'directory_index must be a list of strings, got={directory_index}'.format(directory_index = str(directory_index))

            for index in directory_index:
                assert isinstance(index, str), 'directory index must be non-empty string, got={index}'.format(index = str(index))

        if index_ignore:
            assert isinstance(index_ignore, list), 'index_ignore must be a list of strings, got={index_ignore}'.format(index_ignore = str(index_ignore))

            for index in index_ignore:
                assert isinstance(index, str), 'directory index must be non-empty string, got={index}'.format(index = str(index))

        assert isinstance(ssl_certificate, str)
        assert isinstance(ssl_private_key, str)
        assert isinstance(ssl_certificate_chain, str)
        assert isinstance(opt_indexes, bool)

        if not_found_document_root:
            assert isinstance(not_found_document_root, str), 'not_found_document_root must be a string, got={not_found_document_root}'.format(not_found_document_root = str(not_found_document_root))


    def _check_remove_virtual_host_args(self, server_name:str, listen_port:int):
        assert isinstance(server_name, str), 'server_name must be a non-empty string, got={server_name}'.format(server_name = server_name)
        assert server_name != '', 'server_name must be non-empty'

        assert isinstance(listen_port, int), 'listen_port must be a int, got={listen_port}'.format(listen_port = listen_port)

        main_key = server_name + ':' + str(listen_port)
        assert main_key in self._virtual_hosts, 'virtual host {key} not found'.format(key = main_key)

        del self._virtual_hosts[main_key]
        self._log('virtual host {key} removed'.format(key = main_key))


    def remove_virtual_host(self, server_name:str, listen_port:int):
        self._check_remove_virtual_host_args(server_name, listen_port)


    def _locate_file(self, pathname:str, virtual_host:dict, throw_exception:bool = False) -> dict:
        result = {
            'pathname' : pathname,
            'real_pathname' : '',
            'type' : '',
            'exists' : False
        }

        if pathname.startswith('.' + os.path.sep):
            pathname = pathname[2:]

        for idocument_root in virtual_host['document_roots']:
            real_pathname = os.path.realpath(self._clean_path(self._server_main_root_dir + os.path.sep + idocument_root + os.path.sep + pathname))

            if os.path.exists(real_pathname):
                result['real_pathname'] = real_pathname
                result['exists'] = True

                if os.path.isfile(real_pathname):
                    result['type'] = 'file'
                elif os.path.isdir(real_pathname):
                    result['type'] = 'dir'

                break

        if not result['exists'] and throw_exception:
            raise FileNotFoundError(pathname)

        return result


    def add_virtual_host(self,
                         document_roots:List[str] = None,           # type: List[str] = ['/index', '/']
                         server_name:str = '',                      # type: str = self._server_name
                         listen_port:Union[int, str] = 8080,
                         listen_ips:List[str] = None,               # type: List[str] = ['0.0.0.0']
                         server_aliases:List[str] = None,           # type: List[str] = ['localhost', 'www', 'm', 'm.www']
                         directory_index:List[str] = None,          # type: List[str] = ['index.py', 'index.html']
                         index_ignore:List[str] = None,             # type: List[str] = ['__pycache__', '*.pyc', '*.key', '*.crt', '*.pem', '.*']
                         ssl_certificate:str = '',
                         ssl_private_key:str = '',
                         ssl_certificate_chain:str = '',
                         opt_indexes:bool = False,
                         not_found_document_root:str = '/'
                         ) -> dict:
        #setup defaults
        if not document_roots:
            document_roots = ['/index', '/']
        if not listen_ips:
            listen_ips = ['0.0.0.0']
        if directory_index is None:
            directory_index = ['index.py', 'index.html']
        if index_ignore is None:
            index_ignore = ['__pycache__', '*.pyc', '*.key', '*.crt', '*.pem', '.*']
        if not server_name:
            server_name = self._server_name
        if not server_aliases:
            server_aliases = ['localhost', 'www', 'm', 'm.www']

        server_name = server_name.lower()

        #virtual host name (host:port)
        main_key = server_name + ':' + str(listen_port)
        assert not main_key in self._virtual_hosts, 'virtual host {key} already exists'.format(key = main_key)

        #validate args
        self._check_add_virtual_host_args(
            document_roots,
            server_name,
            listen_port,
            listen_ips,
            server_aliases,
            directory_index,
            index_ignore,
            ssl_certificate,
            ssl_private_key,
            ssl_certificate_chain,
            opt_indexes,
            not_found_document_root
        )

        #collect listen IPs and merge with listen port (if port does not exists in IP)
        network_locations = self._build_network_locations(server_name, listen_port, server_aliases)

        virtual_host = OrderedDict()
        virtual_host['document_roots'] = document_roots
        virtual_host['server_name'] = server_name
        virtual_host['listen_port'] = listen_port
        virtual_host['directory_index'] = directory_index
        virtual_host['index_ignore'] = index_ignore
        virtual_host['options'] = {'indexes' : opt_indexes}
        virtual_host['network_locations'] = network_locations
        virtual_host['ssl_certificate'] = self._locate_file(ssl_certificate, virtual_host, True)['real_pathname'] if ssl_certificate else ''
        virtual_host['ssl_private_key'] = self._locate_file(ssl_private_key, virtual_host, True)['real_pathname'] if ssl_private_key else ''
        virtual_host['ssl_certificate_chain'] = self._locate_file(ssl_certificate_chain, virtual_host)['real_pathname'] if ssl_certificate_chain else ''
        virtual_host['not_found_document_root'] = not_found_document_root

        #subscribe servers (ip:port)
        self._add_servers(
            listen_ips,
            listen_port,
            virtual_host['ssl_certificate'],
            virtual_host['ssl_private_key'],
            virtual_host['ssl_certificate_chain']
        )

        self._virtual_hosts[main_key] = dict(virtual_host)

        self._log('added virtual host', main_key, os.linesep, pprint.pformat(virtual_host))

        return virtual_host


    def _build_network_locations(self, server_name:str, listen_port:int, server_aliases:List[str] = None):
        network_locations = []

        listen_port_str = str(listen_port)
        global_server_name = '.' + server_name

        network_locations.append(server_name + ':' + listen_port_str)

        if server_aliases:
            for alias in server_aliases:
                if alias.endswith(global_server_name) and alias != server_name:
                    assert not hasattr(self, alias), 'server alias name {name} is reserved'.format(name = alias)

                    network_locations.append(alias + ':' + listen_port_str)
                else:
                    full_alias = alias + global_server_name
                    assert not hasattr(self, alias), 'server alias name {name} is reserved'.format(name = alias)

                    network_locations.append(full_alias + ':' + listen_port_str)

                alias_port = alias + ':' + listen_port_str
                if not alias_port in network_locations:
                    network_locations.append(alias_port)

        return network_locations


    def _add_servers(self,
                     listen_ips:List[str],
                     listen_port:Union[int, str],
                     ssl_certificate:str = '',
                     ssl_private_key:str = '',
                     ssl_certificate_chain:str = '') -> List[str]:
        """
        will subscribe and add all required servers, and return processed ip:port (even if server already exists)
        :return: list of processed ip:port
        """
        listen_list = []

        if isinstance(listen_port, str) and listen_port == '*':
            return listen_list

        for ip in listen_ips:
            port = listen_port

            if ip.find(':') != -1:
                parsed_ip = self._parse_ip(ip, listen_port)

                ip = parsed_ip['ip']
                port = parsed_ip['port']

            server = self._add_server(port, ip, ssl_certificate, ssl_private_key, ssl_certificate_chain)
            if server:
                listen_list.append(server._socket_host + ':' + str(server.socket_port))
            else:
                #server already exists? add prophylactically
                listen_list.append(ip + ':' + str(port))

        return listen_list


    def _remove_prefix(self, text:str, prefix:str) -> str:
        if text.startswith(prefix):
            return text[len(prefix):]

        return text


    def _replace_last(self, source_string:str, replace_what:str, replace_with:str) -> str:
        """
        replace string with another string at the end
        source: http://stackoverflow.com/questions/3675318/how-to-replace-the-some-characters-from-the-end-of-a-string (2 post)
        """
        head, sep, tail = source_string.rpartition(replace_what)
        return head + replace_with + tail


    def _virtual_hosts_to_dict(self) -> dict:
        result = {}

        for key, virtual_host in self._virtual_hosts.items():
            server_port = virtual_host['server_name'] + ':' + str(virtual_host['listen_port'])
            dot_server_port = '.' + server_port

            for network_location in virtual_host['network_locations']:
                if network_location == server_port:
                    continue

                result[network_location] = self._virtual_host_root + self._replace_last(network_location, dot_server_port, '')

        return result


    def _should_skip_directory_entry(self, virtual_host:dict, pathname:str) -> bool:
        """
        return True if file/directory should be ommitted in directory listing, you can affect this
        by editing server.x_skip_directory_files list; by default __pycache__ and *.pyc files are omitted
        """
        for pattern in virtual_host['index_ignore']:
            if fnmatch.fnmatch(pathname, pattern):
                return True

        return False


    def _render_directory_listing(self,
                                  virtual_host:dict,
                                  full_pathname:str,
                                  pathname:str) -> str:
        #disable cache
        cherrypy.response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        cherrypy.response.headers['Pragma'] = 'no-cache'
        cherrypy.response.headers['Expires'] = '0'

        parent_pathname = None
        for idocument_root in virtual_host['document_roots']:
            if pathname == idocument_root:
                # server's root
                parent_pathname = idocument_root
                break

        #TODO test
        if not parent_pathname:
            parent_pathname = os.path.split(os.path.abspath(pathname))[0]
            if not parent_pathname:
                parent_pathname = os.path.sep

        # if pathname == virtual_host['document_root']:
        #     #server's root
        #     parent_pathname = os.path.sep
        # else:
        #     # parent_pathname = os.path.split(os.path.abspath(pathname))[0].replace(self._server_main_root_dir, '', 1)
        #     parent_pathname = os.path.split(os.path.abspath(pathname))[0]
        #     if not parent_pathname:
        #         parent_pathname = os.path.sep

        entries = []
        for entry_pathname in os.listdir(full_pathname):
            if self._should_skip_directory_entry(virtual_host, entry_pathname):
                continue

            entry_full_pathname = self._clean_path(full_pathname + os.path.sep + entry_pathname)
            view_full_pathname = self._clean_path(pathname + os.path.sep + entry_pathname)

            size = '-'
            modified = '?'
            entry_type = 'file'

            try:
                modified = format_date_time(os.path.getmtime(entry_full_pathname))
                size = self._convert_size(os.path.getsize(entry_full_pathname))
            except FileNotFoundError: pass

            if os.path.isdir(entry_full_pathname):
                entry_full_pathname = self._clean_path(entry_full_pathname + os.path.sep)
                entry_pathname = self._clean_path(entry_pathname + os.path.sep)
                view_full_pathname += '/'
                size = '-'
                entry_type = 'folder'

            entries.append(self._list_html_template_file.format(
                type = entry_type,
                full_pathname = view_full_pathname.replace('\\', '/'),
                pathname = entry_pathname.replace('\\', '/'),
                modified = modified,
                size = size
            ))

        html = self._list_html_template.format(
            pathname=pathname.replace('\\', '/'),
            parent_pathname=parent_pathname.replace('\\', '/'),
            entries=''.join(entries)
        )

        return html


    def _reload_modules(self):
        if self._reloading:
            return
        self._reloading = True

        now = int(time.time())
        if now - self._last_reloaded <= self.RELOADER_INTERVAL:
            self._reloading = False
            return

        self._last_reloaded = now

        need_reload = False
        for module_file_full_pathname in list(self._supporting_modules.keys()):
            try:
                if not os.path.exists(module_file_full_pathname):
                    del self._supporting_modules[module_file_full_pathname]
                    continue

                if self._supporting_modules[module_file_full_pathname]['mtime'] != os.path.getmtime(module_file_full_pathname):
                    self._log('changed', module_file_full_pathname)

                    need_reload = True
                    break
            except: pass

        if need_reload:
            for module_file_full_pathname in list(self._supporting_modules.keys()):
                if self.DEBUG_MODE:
                    self._log('reloading', module_file_full_pathname)

                try:
                    del sys.modules[self._supporting_modules[module_file_full_pathname]['module']]
                except: pass

            try:
                self._supporting_modules.clear()
            except: pass
        self._reloading = False


    def _collect_modules(self):
        for module_name in list(sys.modules.keys()):
            readable = False

            module_file_full_pathname = module_name.replace('.', os.path.sep)
            if os.path.exists(module_file_full_pathname):
                #directory
                readable = True
            else:
                module_file_full_pathname = module_name.replace('.', os.path.sep) + '.py'
                if os.path.exists(module_file_full_pathname):
                    #file
                    readable = True

            if readable and not module_file_full_pathname in self._supporting_modules:
                if self.DEBUG_MODE:
                    self._log('supporting', module_file_full_pathname)

                self._supporting_modules[module_file_full_pathname] = {
                    'module' : module_name,
                    'mtime' : os.path.getmtime(module_file_full_pathname)
                }


    def _print_debug_info(self):
        peak_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        self._log('peak memory usage', str(peak_memory))


    def _pathname_to_module(self, pathname:str) -> str:
        if pathname.endswith('.py'):
            return self._replace_last(pathname.replace(os.path.sep, '.'), '.py', '')
        else:
            return pathname.replace(os.path.sep, '.')


    def _module_to_pathname(self, module_name:str) -> str:
        pathname = module_name.replace('.', os.path.sep)
        if os.path.exists(pathname):
            return pathname
        else:
            return pathname + '.py'


    def _module_to_parent(self, module_name:str) -> str:
        parts = module_name.split('.')
        if parts:
            parts.pop()
            return '.'.join(parts)

        return module_name


    def _build_scope(self, pathname:str, full_pathname:str) -> dict:
        try:
            if full_pathname in self._cached_scopes:
                return self._cached_scopes[full_pathname]
        except: pass

        short_pathname = self._remove_prefix(full_pathname, self._server_main_root_dir)
        module_name = self._pathname_to_module(short_pathname)
        parent_module_name = self._module_to_parent(module_name)

        scope_data = {
            '__builtins__': {
                '__import__': self._my__import__ if self.OWN_IMPORTER else self._org___import__
            },
            '____ideapy____': self,
            '____ideapy_file____': pathname,
            '____ideapy_module____': module_name,
            '____ideapy_module_parent____': parent_module_name,
            '____ideapy_file_full_pathname____': full_pathname,
            '____ideapy_file_short_pathname____': short_pathname,
            '____ideapy_file_full_dirname____': os.path.dirname(full_pathname),
            '____ideapy_file_short_dirname____': os.path.dirname(short_pathname)
        }

        try:
            if len(self._cached_scopes) >= self._CACHED_SCOPES_TOTAL:
                self._cached_scopes.clear()
        except: pass

        self._cached_scopes[full_pathname] = scope_data

        return scope_data


    def _execute_python_file(self,
                             virtual_host:dict,
                             full_pathname:str,
                             pathname:str) -> Union[str, bytes]:
        full_pathname = os.path.realpath(full_pathname)

        cherrypy.session.acquire_lock()

        cherrypy.response.headers['Content-Type'] = 'text/plain'
        cherrypy.response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        cherrypy.response.headers['Pragma'] = 'no-cache'
        cherrypy.response.headers['Expires'] = '0'

        if self.RELOADER:
            self._reload_modules()

        if self.DEBUG_MODE:
            self._log('executing', full_pathname)

        cherrypy.response.____ideapy_scope____ = self._build_scope(pathname, full_pathname)

        try:
            _locals = locals()

            # inject __file__ so the interpreter will know which file is executing currently
            _locals['__file__'] = full_pathname

            # exec(open(full_pathname).read(), locals(), locals())
            exec(open(full_pathname).read(), _locals, _locals)
        except BaseException as x:
            raise x
        finally:
            self._clear_garbage()

            if self.RELOADER:
                self._collect_modules()

            if self.DEBUG_MODE:
                self._print_debug_info()

        return cherrypy.response.body


    def _clear_garbage(self):
        count_unreachable = gc.collect()

        #hack for gc
        #https://stackoverflow.com/questions/20489585/python-is-not-freeing-memory (second post)
        len(gc.get_objects())

        if count_unreachable and self.DEBUG_MODE:
            self._log('gc', str(count_unreachable), 'unreachable objects found')


    def _profiler_to_file(self, pathname:str):
        org_stdout = sys.stdout
        sys.stdout = open(pathname, 'w')

        self._profiler.print_stats(sort='time')

        sys.stdout = org_stdout


    def _guess_file_mime_type(self, pathname:str) -> str:
        content_type = mimetypes.guess_type(pathname)[0]
        if not content_type:
            #to avoid None
            content_type = 'text/plain'

        return content_type


    def _stream_binary_file(self,
                            virtual_host:dict,
                            full_pathname:str,
                            pathname:str):
        """
        here comes the magic
        """
        content_type = self._guess_file_mime_type(full_pathname)

        try:
            size = os.path.getsize(full_pathname)
            modified = format_date_time(os.path.getmtime(full_pathname))
        except:
            cherrypy.response.status = '500 Internal Server Error'
            return bytes('', 'utf8')

        if self.DEBUG_MODE:
            self._log('streaming', full_pathname, content_type)

        cherrypy.response.headers['Content-Type'] = content_type
        cherrypy.response.headers['Cache-Control'] = 'max-age=3600'            #cache for 1h
        cherrypy.response.headers['Accept-Ranges'] = 'bytes'
        cherrypy.response.headers['Last-Modified'] = modified
        cherrypy.response.headers['Connection'] = 'close'

        fd = open(full_pathname, 'rb')

        # cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="{basename}"'.format(basename = os.path.basename(pathname))

        content_length = size

        cherrypy.response.headers['Content-Length'] = content_length
        cherrypy.response.stream = True

        offset = 0
        if 'Range' in cherrypy.request.headers:
            cherrypy.response.status = '206 Partial Content'

            range = self._parse_http_Range()
            offset = range['start']

            if range['start'] != -1 and range['end'] == -1:
                #just offset
                cherrypy.response.headers['Content-Range'] = 'bytes {offset}-{size_minus}/{size}'.format(offset = offset, size_minus= size - 1, size = size)
            elif range['start'] != -1 and range['end'] != -1:
                #offset and length
                content_length = range['end'] - range['start'] + 1
                cherrypy.response.headers['Content-Length'] = content_length

                cherrypy.response.headers['Content-Range'] = 'bytes {offset}-{size_minus}/{size}'.format(offset=offset, size_minus=size - 1, size=size)

            # cherrypy.response.headers['X-Content-Duration'] = '2054.53'
            # cherrypy.response.headers['Content-Duration'] = '2054.53'

        if offset > size or content_length > size:
            cherrypy.response.status = '416 Requested range not satisfiable'
            return bytes('', 'utf8')

        fd.seek(offset)

        BUF_SIZE = 1024 * 5

        read_length = 0
        def stream(content_length:int, read_length:int):
            data = fd.read(BUF_SIZE)
            while len(data) > 0 and read_length < content_length:
                read_length = read_length + len(data)

                yield data
                data = fd.read(BUF_SIZE)

        return stream(content_length, read_length)


    def _parse_http_Range(self) -> dict:
        range = {
            'start' : -1,
            'end' : -1
        }

        range_str = cherrypy.request.headers['Range']
        if range_str.startswith('bytes='):
            range_str = range_str.replace('bytes=', '', 1)

        range_parts = range_str.split('-')
        len_range_parts = len(range_parts)

        if len_range_parts >= 1 and range_parts[0]:
            range['start'] = int(range_parts[0])

        if len_range_parts >= 2 and range_parts[1]:
            range['end'] = int(range_parts[1])

        return range


    def _serve_file(self,
                    virtual_host:dict,
                    full_pathname:str,
                    pathname:str):
        content_type = self._guess_file_mime_type(full_pathname)
        if content_type == 'text/x-python':
            #python file - execute
            return self._execute_python_file(virtual_host, full_pathname, pathname)

        return self._stream_binary_file(virtual_host, full_pathname, pathname)


    def _serve_directory(self, virtual_host:dict, full_pathname:str, pathname:str):
        for index_file in virtual_host['directory_index']:
            index_full_pathname = self._clean_path(full_pathname + os.path.sep + index_file)
            if os.path.isfile(index_full_pathname):
                # index file exists
                pathname = self._clean_path(pathname + os.path.sep + index_file)
                return self._serve_file(virtual_host, index_full_pathname, pathname)

        if not virtual_host['options']['indexes']:
            raise cherrypy.HTTPError(403, 'Forbidden')

        #directory, serve as listing
        return self._render_directory_listing(virtual_host, full_pathname, pathname)


    def _serve_by_virtual_host2(self, virtual_host:dict, pathname:str) -> str:
        """
        serve file or directory listing by self._server_root_dir + server.x_document_root + pathname
        """
        file_data = self._locate_file(pathname, virtual_host)
        if file_data['exists']:
            if file_data['type'] == 'file':
                return self._serve_file(virtual_host, file_data['real_pathname'], file_data['pathname'])
            elif file_data['type'] == 'dir':
                return self._serve_directory(virtual_host, file_data['real_pathname'], file_data['pathname'])

        if pathname == IdeaPy._MAIN_FAVICON:
            return self._serve_server_static_file(pathname)

        # not found? try to "redirect" call to not_found_document_root if set
        if virtual_host['not_found_document_root']:
            file_data = self._locate_file(virtual_host['not_found_document_root'], virtual_host)
            if file_data['exists']:
                if file_data['type'] == 'file':
                    return self._serve_file(virtual_host, file_data['real_pathname'], file_data['pathname'])
                elif file_data['type'] == 'dir':
                    return self._serve_directory(virtual_host, file_data['real_pathname'], file_data['pathname'])

        raise cherrypy.NotFound()


    def _serve_by_virtual_host(self, virtual_host:dict, args:tuple, kwargs:dict, path_info:str) -> str:
        if not args:
            return self._serve_by_virtual_host2(virtual_host, os.path.sep)

        return self._serve_by_virtual_host2(virtual_host, path_info)


    def _find_virtual_host_by_netloc(self, netloc:str, port:int) -> Optional[dict]:
        netloc = netloc.lower()
        netloc_and_port = netloc + ':' + str(port)

        for server_name_port, virtual_host in self._virtual_hosts.items():
            if netloc in virtual_host['network_locations'] or netloc_and_port in virtual_host['network_locations']:
                return virtual_host

        return None


    def _render_server_static_file(self, static_data:dict):
        cherrypy.response.headers['Content-Type'] = static_data['content_type']
        cherrypy.response.headers['Cache-Control'] = 'max-age=86400'  # cache for 24h
        cherrypy.response.headers['Connection'] = 'close'
        cherrypy.response.headers['Content-Length'] = len(static_data['data'])

        return static_data['data']


    def _serve_server_static_file(self, req_static_pathname:str):
        req_static_basename = os.path.basename(req_static_pathname)

        if req_static_basename in self._statics:
            return self._render_server_static_file(self._statics[req_static_basename])

        raise cherrypy.NotFound()


    @cherrypy.expose
    def default(self, *args, **kwargs):
        if cherrypy.request.path_info.startswith('/server_statics/'):
            return self._serve_server_static_file(cherrypy.request.path_info)

        #try to find proper virtual host using request data
        parsed_url = urlparse(cherrypy.request.base)
        if parsed_url.port:
            target_port = parsed_url.port
        else:
            target_port = cherrypy.request.local.port

        virtual_host = self._find_virtual_host_by_netloc(parsed_url.netloc, target_port)
        if not virtual_host:
            raise cherrypy.NotFound()

        if self.DEBUG_MODE:
            http_host = (cherrypy.request.wsgi_environ['HTTP_HOST'] if 'HTTP_HOST' in cherrypy.request.wsgi_environ else '<no HTTP_HOST>')
            http_user_agent = (cherrypy.request.wsgi_environ['HTTP_USER_AGENT'] if 'HTTP_USER_AGENT' in cherrypy.request.wsgi_environ else '<no HTTP_USER_AGENT>')

            self._log(
                'got',
                cherrypy.request.wsgi_environ['REQUEST_METHOD'],
                http_host,
                cherrypy.request.wsgi_environ['REQUEST_URI'],
                http_user_agent,
                'serving by',
                str(virtual_host['network_locations'][0])
            )

        return self._serve_by_virtual_host(virtual_host, args, kwargs, cherrypy.request.path_info)


    def _mount_virtual_hosts(self):
        vhosts = self._virtual_hosts_to_dict()
        conf = {
            self._virtual_host_root : {
                'request.dispatch': cherrypy.dispatch.VirtualHost(
                    **vhosts
                )
            }
        }

        cherrypy.tree.mount(self, self._virtual_host_root, conf)

        if self.DEBUG_MODE:
            self._log('mounted virtual hosts {vhosts} at {root}'.format(
                vhosts = str(vhosts),
                root = self._virtual_host_root
            ))


    def _module_real_path_from_scope(self, module_name:str, ____ideapy_scope____:dict) -> str:
        module_pathname = ____ideapy_scope____['____ideapy_file_short_dirname____'] + os.path.sep + self._module_to_pathname(module_name)
        if os.path.exists(module_pathname):
            return ____ideapy_scope____['____ideapy_module_parent____'] + '.' + module_name

        return module_name


    def _my__import__(self, name, globals=None, locals=None, fromlist=(), level=0):
        if not hasattr(cherrypy.response, '____ideapy_scope____'):
            return self._org___import__(name, globals, locals, fromlist, level)

        processed_name = self._module_real_path_from_scope(name, cherrypy.response.____ideapy_scope____)

        if self.DEBUG_MODE:
            self._log('importing', name, 'as', processed_name)

        return self._org___import__(processed_name, globals, locals, fromlist, level)


    def _my_import_module(self, name, package=None):
        if not hasattr(cherrypy.response, '____ideapy_scope____'):
            return self._org_import_module(name, package)

        name = self._module_real_path_from_scope(name, cherrypy.response.____ideapy_scope____)

        return self._org_import_module(name, package)


    def _install_own_importer(self):
        #needed by scope
        self._org___import__ = builtins.__import__
        self._org_import_module = importlib.import_module

        if not self.OWN_IMPORTER:
            return

        builtins.__import__ = self._my__import__
        importlib.import_module = self._my_import_module


    def start(self):
        self._log('starting')

        self._mount_virtual_hosts()
        cherrypy.engine.start()
        self._install_own_importer()

        self._log('started')


    def block(self):
        self._log('blocking')
        cherrypy.engine.block()


    @staticmethod
    def main():
        IdeaPy.setup_cherrypy()

        idea = IdeaPy()
        # idea.add_virtual_host(listen_port=8080)
        # idea.add_virtual_host(listen_port=8081, ssl_certificate='./certs/wildcard.dealsnoffers.net/bundle.crt', ssl_private_key='./certs/wildcard.dealsnoffers.net/dealsnoffers.net.key')
        idea.start()
        idea.block()


if __name__ == '__main__':
    IdeaPy.main()
