import os
import sys
import shutil
from codecs import open

from setuptools import setup


here = os.path.dirname(os.path.abspath(__file__))

# 'setup.py publish' shortcut.
if sys.argv[-1] == 'publish':
    shutil.rmtree(os.path.join(here, 'dist'))
    os.system('python setup.py sdist bdist_wheel')
    os.system('twine upload dist/*')
    sys.exit()

about = {}
with open(os.path.join(here, 'antidote', '__version__.py'), 'r') as f:
    exec(f.read(), about)

with open('README.rst', 'r') as f:
    readme = f.read()

setup(
    name=about['__title__'],
    version=about['__version__'],
    description=about['__description__'],
    long_description=readme,
    author=about['__author__'],
    url=about['__url__'],
    packages=['antidote'],
    package_data={'': ['LICENSE']},
    include_package_data=True,
    install_requires=[
        'wrapt'
    ],
    extras_require={
        ":python_version<'3'": ["chainmap"],
        "attrs": ["attrs>=17.1"]
    },
    license=about['__license__'],
    classifiers=(
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
    ),
    keywords='dependency injection'
)
