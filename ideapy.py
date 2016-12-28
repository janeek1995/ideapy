#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
IdeaPy is a simple WWW server built on top of CherryPy, with Python code execution feature. Example usage:
$ python3 -m ideapy

go to http://localhost:8888/

Homepage: https://github.com/skazanyNaGlany/ideapy
"""

import sys
import cherrypy
import os
import math
import mimetypes
import importlib
import tempfile
import fnmatch
import socket
import binascii

from urllib.parse import urlparse
from wsgiref.handlers import format_date_time

from typing import List, Dict, Union


class IdeaPy:
    _VERSION = '0.1.3'
    _LOG_SIGN = 'IDEAPY'
    _PYTHON_MIN_VERSION = (3, 4)
    _CHERRYPY_MIN_VERSION = [8, 1]

    _DEFAULT_VIRTUAL_HOST_NAME = '_default_'

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
            }
        }

        # self._init_cherrypy(unsubscribe)

        self._log('{version} initialized, _server_main_root_dir={_server_main_root_dir}, _server_name={_server_name}'.format(
            version = IdeaPy._VERSION,
            _server_main_root_dir = self._server_main_root_dir,
            _server_name = self._server_name
        ))


    @staticmethod
    def setup_cherrypy(unsubscribe:bool = True):
        cherrypy.config.update({
            'tools.sessions.on': True,
            'tools.sessions.storage_class': cherrypy.lib.sessions.FileSession,
            'tools.sessions.storage_path': tempfile.gettempdir(),
            'tools.sessions.timeout': 60,
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


    def _init_cherrypy(self, unsubscribe:bool):
        cherrypy.config.update({
            'tools.sessions.on': True,
            'tools.sessions.storage_class': cherrypy.lib.sessions.FileSession,
            'tools.sessions.storage_path': tempfile.gettempdir(),
            'tools.sessions.timeout': 60,
            # we will lock/unlock session manually by cherrypy.session.acquire_lock() and cherrypy.session.release_lock()
            # see http://docs.cherrypy.org/en/latest/pkg/cherrypy.lib.html#locking-sessions
            # 'tools.sessions.locking': 'early',
            'tools.sessions.locking': 'explicit',

            'log.screen': True,
            'engine.autoreload.on': True,

            # #disable response timeout monitor
            # 'engine.timeout_monitor.on': False,
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
        cherrypy_version = cherrypy.__version__.split('.')
        assert int(cherrypy_version[0]) >= IdeaPy._CHERRYPY_MIN_VERSION[0] and int(cherrypy_version[1]) >= IdeaPy._CHERRYPY_MIN_VERSION[1]


    def _log(self, msg:str):
        cherrypy.log('{log_sign} {_id} {msg}'.format(
            log_sign = self._LOG_SIGN,
            _id = self._id,
            msg = msg
        ))


    def set_server_name(self, hostname:str):
        assert isinstance(hostname, str) and str != '', 'hostname must be non-empty string (valid domain name)'

        self._server_name = hostname
        self._log('using _server_name={hostname}'.format(hostname = self._server_name))


    def add_server(self,
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
                                     document_root:str,
                                     server_name:str,
                                     listen_port:Union[int, str],
                                     listen_ips:List[str],
                                     server_aliases:List[str],
                                     directory_index:List[str],
                                     index_ignore:List[str],
                                     ssl_certificate,
                                     ssl_private_key,
                                     ssl_certificate_chain:str,
                                     opt_indexes:bool):
        assert isinstance(document_root, str), 'document_root must be a string'
        assert document_root != '', 'document_root must be non-empty (full pathname)'

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


    def add_virtual_host(self,
                         document_root:str = '/',
                         server_name:str = '',
                         listen_port:Union[int, str] = 8888,
                         listen_ips:List[str] = None,
                         server_aliases:List[str] = None,
                         directory_index:List[str] = None,
                         index_ignore:List[str] = None,
                         ssl_certificate:str = '',
                         ssl_private_key:str = '',
                         ssl_certificate_chain:str = '',
                         opt_indexes:bool = True
                         ) -> dict:
        if not listen_ips:
            listen_ips = ['0.0.0.0']
        if directory_index is None:
            directory_index = ['index.py', 'index.html']
        if index_ignore is None:
            index_ignore = ['__pycache__', '*.pyc', '*.key', '*.crt', '*.pem', '.*']
        if not server_name:
            server_name = self._server_name
        if not server_aliases:
            server_aliases = ['localhost']

        server_name = server_name.lower()

        main_key = server_name + ':' + str(listen_port)
        assert not main_key in self._virtual_hosts, 'virtual host {key} already exists'.format(key = main_key)

        self._check_add_virtual_host_args(
            document_root,
            server_name,
            listen_port,
            listen_ips,
            server_aliases,
            directory_index,
            index_ignore,
            ssl_certificate,
            ssl_private_key,
            ssl_certificate_chain,
            opt_indexes
        )

        #collect listen IPs and merge with listen port (if port does not exists in IP)
        listen_list = self._add_servers(listen_ips, listen_port, ssl_certificate, ssl_private_key, ssl_certificate_chain)
        network_locations = self._build_network_locations(server_name, listen_port, server_aliases)

        virtual_host = {
            'document_root' : document_root,
            'server_name' : server_name,
            'listen_port' : listen_port,
            'listen_list' : listen_list,
            'network_locations' : network_locations,
            'directory_index' : directory_index,
            'index_ignore' : index_ignore,
            'options' : {
                'indexes' : opt_indexes
            },
            'is_default_server' : server_name == IdeaPy._DEFAULT_VIRTUAL_HOST_NAME,
            'is_default_port' : isinstance(listen_port, str) and listen_port == '*'
        }

        self._virtual_hosts[main_key] = virtual_host
        self._log('added virtual host document_root={document_root}, server_name={server_name}, listen_port={listen_port}, listen_list={listen_list}, network_locations={network_locations}, directory_index={directory_index}, index_ignore={index_ignore}, is_default_server={is_default_server}, is_default_port={is_default_port}'.format(
            document_root = virtual_host['document_root'],
            server_name = virtual_host['server_name'],
            listen_port = str(listen_port),
            listen_list = str(virtual_host['listen_list']),
            network_locations = str(virtual_host['network_locations']),
            directory_index = str(virtual_host['directory_index']),
            index_ignore = str(virtual_host['index_ignore']),
            is_default_server = virtual_host['is_default_server'],
            is_default_port = virtual_host['is_default_port']
        ))

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

            server = self.add_server(port, ip, ssl_certificate, ssl_private_key, ssl_certificate_chain)
            if server:
                listen_list.append(server._socket_host + ':' + str(server.socket_port))
            else:
                #server already exists? add prophylactically
                listen_list.append(ip + ':' + str(port))

        return listen_list


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

        if pathname == virtual_host['document_root']:
            #server's root
            parent_pathname = os.path.sep
        else:
            # parent_pathname = os.path.split(os.path.abspath(pathname))[0].replace(self._server_main_root_dir, '', 1)
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


    def _filename_to_module_path(self, module_pathname:str) -> str:
        basename, ext = os.path.splitext(os.path.basename(module_pathname))
        filename = os.path.sep + basename + ext

        server_main_root_dir = self._server_main_root_dir
        if server_main_root_dir.startswith(os.path.sep):
            server_main_root_dir = server_main_root_dir[1:]

        #build module path short
        # 1.remove server main root dir from result
        # 2.remove extension like .py from result
        # 3.replace directory separator with dot (eg. \\ or // to .)
        return module_pathname.replace(server_main_root_dir, '').replace(filename, os.path.sep + basename)[1:].replace(os.path.sep, '.')


    def _import_module_by_full_pathname(self, module_path:str, reload:bool = True):
        module_full_pathname = self._filename_to_module_path(module_path)

        if module_full_pathname in sys.modules:
            #already imported
            imported_module = sys.modules[module_full_pathname]

            if reload:
                importlib.reload(imported_module)

            return imported_module

        return importlib.import_module(module_full_pathname)


    def _execute_python_file(self,
                             virtual_host:dict,
                             full_pathname:str,
                             pathname:str) -> Union[str, bytes]:
        # if not self._is_script_allowed(server, pathname):
        #     raise cherrypy.HTTPError(403, 'Forbidden')

        cherrypy.session.acquire_lock()

        cherrypy.response.headers['Content-Type'] = 'text/plain'
        cherrypy.response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        cherrypy.response.headers['Pragma'] = 'no-cache'
        cherrypy.response.headers['Expires'] = '0'

        importlib.invalidate_caches()

        imported_module = self._import_module_by_full_pathname(full_pathname)

        if hasattr(imported_module, 'stream') and callable(imported_module.stream):
            cherrypy.response.stream = True
            return imported_module.stream()

        # HACK HACK HACK! due to CherryPy bug - don't run cherrypy.session.save() or cherrypy.session.release_lock()
        # CherryPy will call cherrypy.session.save() again at the end of the request
        # and with unlocked session (cherrypy.session.locked=False after save()) it will raise error

        return cherrypy.response.body


    def _stream_binary_file(self,
                            virtual_host:dict,
                            full_pathname:str,
                            pathname:str):
        """
        here comes the magic
        """
        content_type = mimetypes.guess_type(full_pathname)[0]

        try:
            size = os.path.getsize(full_pathname)
            modified = format_date_time(os.path.getmtime(full_pathname))
        except:
            cherrypy.response.status = '500 Internal Server Error'
            return bytes('', 'utf8')

        cherrypy.response.headers['Content-Type'] = content_type
        cherrypy.response.headers['Cache-Control'] = 'max-age=86400'            #cache for 24h
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
        content_type = mimetypes.guess_type(full_pathname)[0]
        # if content_type == 'text/x-python' and not virtual_host.x_view_py_code:
        if content_type == 'text/x-python':
            #python file - eval
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
        #concatenate paths and replace duplicated slashes, like // to /
        full_pathname = self._clean_path(self._server_main_root_dir + virtual_host['document_root'] + pathname)

        if os.path.isfile(full_pathname):
            return self._serve_file(virtual_host, full_pathname, pathname)
        elif os.path.isdir(full_pathname):
            return self._serve_directory(virtual_host, full_pathname, pathname)
        elif pathname == os.path.sep:
            return self._serve_directory(virtual_host, full_pathname, pathname)

        raise cherrypy.NotFound()


    def _serve_by_virtual_host(self, virtual_host:dict, args:tuple, kwargs:dict, path_info:str) -> str:
        if not args:
            # return self._serve(os.path.sep + 'index.py')
            return self._serve_by_virtual_host2(virtual_host, os.path.sep)

        return self._serve_by_virtual_host2(virtual_host, path_info)
        # return self._serve_by_virtual_host2(virtual_host, os.path.sep + os.path.sep.join(args))


    def _find_virtual_host_by_netloc(self, netloc:str, port:int) -> Union[dict, None]:
        netloc = netloc.lower()

        for server_name_port, virtual_host in self._virtual_hosts.items():
            if netloc in virtual_host['network_locations']:
                return virtual_host

        if not port:
            #request port is unknown, skip
            return None

        #virtual host not found? try to find default for such port
        for server_name_port, virtual_host in self._virtual_hosts.items():
            if virtual_host['is_default_server'] and not virtual_host['is_default_port'] and virtual_host['listen_port'] == port:
                    return virtual_host

        for server_name_port, virtual_host in self._virtual_hosts.items():
            if virtual_host['is_default_server'] and virtual_host['is_default_port']:
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
        parsed_url = url = urlparse(cherrypy.request.base)

        virtual_host = self._find_virtual_host_by_netloc(parsed_url.netloc, parsed_url.port)
        if virtual_host:
            # virtual host found
            return self._serve_by_virtual_host(virtual_host, args, kwargs, cherrypy.request.path_info)

        raise cherrypy.NotFound()


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
        self._log('mounted virtual hosts {vhosts} at {root}'.format(
            vhosts = str(vhosts),
            root = self._virtual_host_root
        ))


    def start(self):
        if not self._virtual_hosts:
            self.add_virtual_host()

        self._mount_virtual_hosts()

        cherrypy.engine.start()


    def block(self):
        cherrypy.engine.block()


if __name__ == '__main__':
    IdeaPy.setup_cherrypy()

    idea = IdeaPy()
    idea.start()
    idea.block()
