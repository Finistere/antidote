import os
import pathlib
import shutil
import sys

from setuptools import setup, find_packages

here = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))

# 'setup.py publish' shortcut.
if sys.argv[-1] == 'publish':
    print("Removing previous builds...")
    if os.path.exists(os.path.join(here, 'dist')):
        shutil.rmtree(os.path.join(here, 'dist'))

    print("Building distribution...")
    os.system('python setup.py sdist bdist_wheel')

    print("Uploading the package to PyPi with Twine...")
    os.system('twine upload dist/*')

    print("Done !")
    sys.exit()

with open(str(here / 'README.rst'), 'r') as f:
    readme = f.read()

setup(
    name='antidote',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
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
            "pytest-cov",
            "hypothesis"
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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
    ),
    keywords='dependency injection',
    zip_safe=False,
)
