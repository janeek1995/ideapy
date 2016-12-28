from setuptools import setup

readme = open('README.txt').read()

setup(
    name='ideapy',
    version='0.1.3',
    author='Paweł Kacperski',
    author_email='screamingbox@gmail.com',
    description='IdeaPy is a simple WWW server built on top of CherryPy, with Python code execution feature',
    long_description=readme,
    scripts=['ideapy.py'],
    packages=['.'],
    url='https://github.com/skazanyNaGlany/ideapy',
    install_requires=[
        'cherrypy>=8.1.3'
    ],
    license='MIT',
    classifiers=['Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ]
)
