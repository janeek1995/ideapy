import cherrypy

#to run this example, make sure CherryPy's session is initialized
#by setting:
# 'tools.sessions.on': True,
# 'tools.sessions.storage_class': cherrypy.lib.sessions.FileSession,
# 'tools.sessions.storage_path': tempfile.gettempdir(),
#or simply run BerryPy.setup_cherrypy()

if not 'test_var' in cherrypy.session:
    cherrypy.session['test_var'] = 0

cherrypy.session['test_var'] += 1

session_data = 'session: ' + str(cherrypy.session.items())
cherrypy.response.body = bytes(session_data, 'utf8')
