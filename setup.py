import os
import sys
import shutil
from codecs import open

from setuptools import setup, find_packages


here = os.path.dirname(os.path.abspath(__file__))

about = {}
with open(os.path.join(here, 'src', 'antidote', '__version__.py')) as f:
    exec(f.read(), about)

# 'setup.py publish' shortcut.
if sys.argv[-1] == 'publish':
    print("Removing previous builds...")
    if os.path.exists(os.path.join(here, 'dist')):
        shutil.rmtree(os.path.join(here, 'dist'))

    print("Building distribution...")
    os.system('python setup.py sdist bdist_wheel')

    print("Uploading the package to PyPi with Twine...")
    os.system('twine upload dist/*')

    print("Pushing git tags")
    os.system('git tag v{0}'.format(about['__version__']))
    os.system('git push --tags')

    print("Done !")
    sys.exit()


with open('README.rst', 'r') as f:
    readme = f.read()

setup(
    name='antidote',
    version=about['__version__'],
    description='Transparent dependency injection.',
    long_description=readme,
    author='Benjamin Rabier',
    url='https://github.com/Finistere/antidote',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[],
    extras_require={
        ":python_version<'3.5'": ["typing"],
        "docs": [
            "sphinx",
            "sphinx_autodoc_typehints",
            "sphinx-rtd-theme",
            "attrs"
        ],
        "tests": [
            "pytest",
            "pytest-cov"
        ]
    },
    license='MIT',
    classifiers=(
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
    ),
    keywords='dependency injection',
    zip_safe=False,
)
