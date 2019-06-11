from setuptools import setup

setup(
    name='bitflyer-rt',
    version='1.0',
    description='Bitflyer Realtime Feed',
    author='Philippe Remy',
    license='MIT',
    long_description_content_type='text/markdown',
    long_description=open('README.md').read(),
    packages=['bitflyer'],
    install_requires=[
        'websocket-client==0.47.0'
    ]
)
