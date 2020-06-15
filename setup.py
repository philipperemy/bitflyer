from setuptools import setup

setup(
    name='bitflyer-rt',
    version='2.2',
    description='Bitflyer Realtime and Rest API',
    author='Philippe Remy',
    license='MIT',
    long_description_content_type='text/markdown',
    long_description=open('README.md').read(),
    packages=['bitflyer'],
    install_requires=[
        'websocket-client==0.47.0',
        'pybitflyer==0.1.9',
        'attrs',
        'iso8601',
        'sortedcontainers'
    ]
)
