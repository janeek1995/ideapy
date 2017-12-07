==========================================================
IdeaPy (c) 2017 Paweł Kacperski (screamingbox@gmail.com)
==========================================================

IdeaPy is a simple WWW server built on top of
CherryPy, with Python code execution feature.
Requires Python 3.4+ and CherryPy 8.1+



Features
----------------------------------------------------------
- ability to execute Python code just like
  Apache2 + mod_php
- reloading modified .py files, not need to
  restart the interpreter
- unlimited number of virtual hosts
- one dependency: CherryPy 8.1+



Example: "Hello World" in a IdeaPy
----------------------------------------------------------
python3 ideapy.py

go to http://localhost:8888/examples/default_page/
or http://localhost:8888/ to view directory listing



Own usage
----------------------------------------------------------

import ideapy

IdeaPy.setup_cherrypy()     #optional
idea = IdeaPy()

idea.start()
idea.block()



Advanced usage
----------------------------------------------------------
import ideapy

IdeaPy.setup_cherrypy()     #optional
idea = IdeaPy()

#change CherryPy config, like sessions, etc.

#now add some virtual hosts

#to serve content on http://localhost:8080
#with directory index disabled
idea.add_virtual_host(
    document_root='/',
    listen_ips=['127.0.0.1'],
    listen_port=8080,
    opt_indexes=False)

#to serve content on
#http://localhost:8080, http://api.localhost:8080, http://api:8080
#with directory index disabled
idea.add_virtual_host(
    document_root='/',
    listen_ips=['127.0.0.1'],
    listen_port=8080,
    server_name='localhost',
    server_aliases=['api'],
    opt_indexes=False)

#to serve /jinja2_app/ directory on
#http://virtualbox:8443, http://jinja2_app:8443, http://jinja2_app.virtualbox:8443
#https://virtualbox:8443, https://jinja2_app:8443, https://jinja2_app.virtualbox:8443
#with SSL enabled
idea.add_virtual_host(
    document_root='/jinja2_app/',
    listen_ips=['0.0.0.0'],
    listen_port=8443,
    server_name='virtualbox',
    server_aliases=['jinja2_app'],
    ssl_certificate = '/bundle.crt',
    ssl_private_key = '/private_key.key')

idea.start()
idea.block()



Homepage
----------------------------------------------------------
https://github.com/skazanyNaGlany/ideapy
