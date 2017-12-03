#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIT License

Copyright (c) 2017 Paweł Kacperski (screamingbox@gmail.com)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


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
import urllib
import io
import urllib.parse

from urllib.parse import urlparse
from wsgiref.handlers import format_date_time
from typing import List, Dict, Union, Optional, Callable
from collections import OrderedDict


class IdeaPy:
    DEBUG_MODE = False
    RELOADER = True
    RELOADER_INTERVAL = 3
    COLLECTOR_INTERVAL = 3
    OWN_IMPORTER = True

    _VERSION = '0.1.6'
    _LOG_SIGN = 'IDEAPY'
    _PYTHON_MIN_VERSION = (3, 4)
    _CHERRYPY_MIN_VERSION = [8, 1]
    _DEFAULT_VIRTUAL_HOST_NAME = '_default_'
    _CACHED_SCOPES_TOTAL = 1024
    _CONF_FILE_NAME = 'ideapy.conf.json'
    _CERT_FILENAME = 'ideapy.' + _VERSION + '.cert.pem'
    _CERT_KEY_FILENAME = 'ideapy.' + _VERSION + '.key.pem'
    _DEFAULT_VENV = 'venv'
    _MAIN_FAVICON = '/favicon.ico'
    _METHODS_WITH_BODIES = ('POST', 'PUT', 'PATCH')
    _CONF_ALLOWED_0_LVL_KEYS = {
        'DEBUG_MODE' : bool,
        'RELOADER': bool,
        'RELOADER_INTERVAL': int,
        'COLLECTOR_INTERVAL': int,
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
        'not_found_document_root': str,
        'secure': bool
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
        self._last_collected = 0
        self._reloading = False
        self._collecting = False
        self._cached_scopes = {}
        self._builtin_modules = []

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
            }
        }

        self._ssl_certificate = self._clean_strings("""
        -----BEGIN CERTIFICATE-----
        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
        -----END CERTIFICATE-----
        """)

        self._ssl_certificate_key = self._clean_strings("""
        -----BEGIN RSA PRIVATE KEY-----
        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
        -----END RSA PRIVATE KEY-----
        """)

        self._log('{version} initializing, _server_main_root_dir={_server_main_root_dir}, _server_name={_server_name}'.format(
            version = IdeaPy._VERSION,
            _server_main_root_dir = self._server_main_root_dir,
            _server_name = self._server_name
        ))

        self._save_self_signed_cert()
        self._fix_sys_path()
        self._parse_conf_json()

        if not self._virtual_hosts:
            self.add_virtual_host()

        self._dump_conf_json()
        self._collect_builtin_modules()

        if venv_dir:
            self._log('using virtualenv {venv_dir}'.format(venv_dir=venv_dir))

        self._log('CherryPy version is {version}'.format(version = cherrypy.__version__))
        self._log('Python version is {version} ({release})'.format(version = IdeaPy._python_version_to_str(), release = sys.version_info.releaselevel))
        self._log('RELOADER is', 'ON' if self.RELOADER else 'OFF')
        self._log('OWN_IMPORTER is', 'ON' if self.OWN_IMPORTER else 'OFF')
        self._log('RELOADER_INTERVAL is', str(self.RELOADER_INTERVAL))
        self._log('COLLECTOR_INTERVAL is', str(self.COLLECTOR_INTERVAL))
        self._log('ready, waiting for start()')


    def _save_self_signed_cert(self):
        tempdir = tempfile.gettempdir()

        self._cert_pathname = os.path.join(tempdir, self._CERT_FILENAME)
        self._key_pathname = os.path.join(tempdir, self._CERT_KEY_FILENAME)

        self._log('saving self-signed SSL certificate in {tempdir}'.format(tempdir=tempdir))
        self._log('{pathname}'.format(pathname=self._cert_pathname))
        self._log('{pathname}'.format(pathname=self._key_pathname))

        if not os.path.exists(self._cert_pathname):
            with open(self._cert_pathname, 'w') as f:
                f.write(self._ssl_certificate)

        if not os.path.exists(self._key_pathname):
            with open(self._key_pathname, 'w') as f:
                f.write(self._ssl_certificate_key)


    def _clean_strings(self, strings:str) -> str:
        result = ''
        for istr in strings.split("\n"):
            result += istr.strip() + "\n"

        return result.strip()


    @staticmethod
    def _python_version_to_str():
        ver_list = [str(sys.version_info.major), str(sys.version_info.minor), str(sys.version_info.micro)]
        return '.'.join(ver_list)


    def _fix_sys_path(self):
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


    def _collect_builtin_modules(self):
        #make them unique
        self._builtin_modules = list(set(list(sys.modules.keys()) + list(sys.builtin_module_names)))


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
                continue

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
                                     not_found_document_root:str = None,
                                     secure:bool = False):
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
        assert isinstance(secure, bool)

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
                         not_found_document_root:str = '/',
                         secure:bool = False
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
            not_found_document_root,
            secure
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
        virtual_host['secure'] = secure

        if secure:
            if not virtual_host['ssl_certificate']:
                virtual_host['ssl_certificate'] = self._cert_pathname
            if not virtual_host['ssl_private_key']:
                virtual_host['ssl_private_key'] = self._key_pathname

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
        if self._collecting:
            return
        self._collecting = True

        now = int(time.time())
        if now - self._last_collected <= self.COLLECTOR_INTERVAL:
            self._collecting = False
            return

        self._last_collected = now

        for module_name, module_object in sys.modules.items():
            if module_name in self._builtin_modules or module_name in sys.builtin_module_names:
                continue

            if hasattr(module_object, '__file__') and module_object.__file__.find('/site-packages/') != -1:
                #new builtin module
                self._builtin_modules.append(module_name)

                if self.DEBUG_MODE:
                    self._log('new builtin module {name} discovered'.format(name=module_name))

                continue

            readable = False

            module_file_full_pathname = module_name.replace('.', os.path.sep)
            if module_file_full_pathname in self._supporting_modules:
                continue

            if os.path.exists(module_file_full_pathname):
                #directory
                readable = True
            else:
                module_file_full_pathname = module_name.replace('.', os.path.sep) + '.py'
                if module_file_full_pathname in self._supporting_modules:
                    continue

                if os.path.exists(module_file_full_pathname):
                    #file
                    readable = True

            if readable:
                if self.DEBUG_MODE:
                    self._log('supporting', module_file_full_pathname)

                self._supporting_modules[module_file_full_pathname] = {
                    'module' : module_name,
                    'mtime' : os.path.getmtime(module_file_full_pathname)
                }

        self._collecting = False


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
            self._log('executing', pathname, 'as', full_pathname)

        cherrypy.response.____ideapy_scope____ = self._build_scope(pathname, full_pathname)

        _locals = locals()

        # inject __file__ so the interpreter will know which file is executing currently
        _locals['__file__'] = full_pathname

        exc = None
        try:
            exec(open(full_pathname).read(), _locals, _locals)
        except BaseException as x:
            exc = x

        if self.RELOADER:
            self._collect_modules()

        if self.DEBUG_MODE:
            self._print_debug_info()

        if exc:
            raise exc

        if 'stream_function' in cherrypy.response.____ideapy_scope____:
            #for Chrome and IE
            cherrypy.response.headers['X-Content-Type-Options'] = 'nosniff'

            cherrypy.response.stream = True

            return cherrypy.response.____ideapy_scope____['stream_function']()
        else:
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


    def _wsgi_start_response(self, status, response_headers, exc_info=None):
        if exc_info is not None:
            raise exc_info[1].with_traceback(exc_info[2])

        cherrypy.response.status = status

        for name, value in response_headers:
            cherrypy.response.headers[name] = value


    def run_wsgi_app(self, wsgi_app:Callable, query_param_name:str = '/?q='):
        request_uri = cherrypy.request.wsgi_environ['REQUEST_URI']

        query_pos = request_uri.find(query_param_name)
        if query_pos != -1:
            new_request_uri = request_uri[query_pos + 4:]
        else:
            new_request_uri = '/'

        if not new_request_uri:
            new_request_uri = '/'

        parsed_url = urllib.parse.urlparse(new_request_uri)

        new_wsgi_environ = cherrypy.request.wsgi_environ.copy()
        new_wsgi_environ['REQUEST_URI'] = new_request_uri
        new_wsgi_environ['PATH_INFO'] = parsed_url.path
        new_wsgi_environ['QUERY_STRING'] = parsed_url.query

        if cherrypy.request.wsgi_environ['REQUEST_METHOD'] in self._METHODS_WITH_BODIES:
            request_body = cherrypy.request.body.read()
        else:
            request_body = None

        if request_body:
            #found raw request body, pass it
            new_wsgi_environ['wsgi.input'] = io.BytesIO(request_body)
        else:
            #hack - convert body_params to raw request body
            new_wsgi_environ['wsgi.input'] = io.StringIO(urllib.parse.urlencode(cherrypy.request.body_params))

        result = wsgi_app(new_wsgi_environ, self._wsgi_start_response)
        if not result:
            result = ''

        if isinstance(result, bytes):
            cherrypy.response.body = result
        elif isinstance(result, list):
            cherrypy.response.body = result
        elif isinstance(result, str):
            cherrypy.response.body = bytes(result, 'utf8')
        else:
            cherrypy.response.body = result


    def stream(self, stream_function):
        cherrypy.response.____ideapy_scope____['stream_function'] = stream_function


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
        idea.start()
        idea.block()


if __name__ == '__main__':
    IdeaPy.main()
