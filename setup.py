import os
import pathlib

from setuptools import Extension, find_packages, setup

here = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))

with open(str(here / 'README.rst'), 'r') as f:
    readme = f.read()


def generate_extensions():
    extensions = []
    for root, _, filenames in os.walk('src'):
        for filename in filenames:
            if filename.endswith('.pyx'):
                path = os.path.join(root, filename)
                module = path[4:].replace('/', '.').rsplit('.', 1)[0]
                extensions.append(Extension(module,
                                            [path],
                                            language='c++'))
    return extensions


ext_modules = []
requires = []
setup_requires = ['setuptools_scm']

try:
    from Cython.Build import cythonize
except ImportError:
    pass
else:
    ext_modules = cythonize(generate_extensions())
    requires.append('fastrlock>=0.4,<0.5')
    setup_requires.append('fastrlock>=0.4,<0.5')

setup(
    name='antidote',
    use_scm_version=True,
    setup_requires=setup_requires,
    description='Transparent dependency injection.',
    long_description=readme,
    author='Benjamin Rabier',
    url='https://github.com/Finistere/antidote',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_dirs=["src"],
    ext_modules=ext_modules,
    install_requires=requires,
    extras_require={
        ":python_version<'3.5'": ["typing"],
    },
    license='MIT',
    classifiers=(
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ),
    keywords='dependency injection',
    zip_safe=False,
)
