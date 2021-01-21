from setuptools import setup

setup(
    name='bitflyer-rt',
    version='2.20',
    python_requires='>=3.6',
    description='Bitflyer Realtime and Rest API',
    author='Philippe Remy',
    license='MIT',
    long_description_content_type='text/markdown',
    long_description=open('README.md').read(),
    packages=['bitflyer'],
    install_requires=[
        'websocket-client==0.47.0',
        'pybitflyer==0.1.9',
        'aiodns==1.1.1',
        'aiohttp==3.6.2',
        'async-timeout==3.0.1',
        'python-dateutil==2.8.1',
        'python-engineio==3.13.2',
        'python-socketio==4.6.0',
        'attrs',
        'iso8601',
        'sortedcontainers',
        'numpy'
    ]
)
