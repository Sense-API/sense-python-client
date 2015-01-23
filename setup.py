import os
from setuptools import setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='sense-python-client',
    version='0.0.7',
    description='Sen.se API client',
    long_description='',
    url='http://sen.se/api/docs/v2',
    author='Sen.se',
    author_email='api@sen.se',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    # https://caremad.io/2013/07/setup-vs-requirement/
    packages=['sense'],
    include_package_data=True,
    install_requires=["requests", "python-dateutil"],
)
