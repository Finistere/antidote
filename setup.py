import os
import pathlib

from setuptools import Extension, find_packages, setup

here = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))

with open(str(here / 'README.rst'), 'r') as f:
    readme = f.read()

ext_modules = []
setup_requires = []
install_requires = [
    'typing_extensions; python_version < "3.8.0"'
]

if os.environ.get("ANTIDOTE_COMPILED") == "true":
    fastrlock = 'fastrlock>=0.5,<0.6'
    setup_requires.extend([
        'cython==0.29.21',
        fastrlock
    ])
    install_requires.append(fastrlock)


    class LazyExtModules(list):
        """
        Allows setup.py to discover that Cython is needed when checking for setup_requires
        without failing in that stage as defining ext_modules requires Cython to be
        imported.
        """

        def __init__(self):
            self.__initialized = False
            self.__length = sum(filename.endswith('.pyx')
                                for root, _, filenames in os.walk('src')
                                for filename in filenames)
            super().__init__()

        def __len__(self):
            return self.__length

        def __iter__(self):
            if not self.__initialized:
                self.__init()
            return super().__iter__()

        def __init(self):
            from Cython.Build import cythonize
            from Cython.Compiler import Options
            cython_options = set(os.environ.get("ANTIDOTE_CYTHON_OPTIONS", "").split(","))
            extension_extras = {}
            cythonize_extras = {}

            if "annotate" in cython_options:
                Options.annotate = True
                cythonize_extras['annotate'] = True

            if "debug" in cython_options:
                cythonize_extras['gdb_debug'] = True

            if "trace" in cython_options:
                directive_defaults = Options.get_directive_defaults()
                directive_defaults['linetrace'] = True
                directive_defaults['binding'] = True
                extension_extras['define_macros'] = [('CYTHON_TRACE', '1')]

            def generate_extensions():
                extensions = []
                for root, _, filenames in os.walk('src'):
                    for filename in filenames:
                        if filename.endswith('.pyx'):
                            path = os.path.join(root, filename)
                            module = path[4:].replace('/', '.').rsplit('.', 1)[0]
                            extensions.append(Extension(module, [path], language='c++',
                                                        **extension_extras))

                return extensions

            self.__initialized = True
            self.extend(cythonize(generate_extensions(),
                                  compiler_directives=dict(language_level=3,
                                                           boundscheck=False,
                                                           wraparound=False,
                                                           annotation_typing=False),
                                  **cythonize_extras))


    ext_modules = LazyExtModules()

setup(
    name='antidote',
    use_scm_version=True,
    description='Dependency injection.',
    long_description=readme,
    author='Benjamin Rabier',
    url='https://github.com/Finistere/antidote',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={"antidote": ["py.typed"]},
    include_dirs=["src"],
    ext_modules=ext_modules,
    python_requires='>=3.6,<4',
    setup_requires=setup_requires,
    install_requires=install_requires,
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    keywords='dependency injection',
    zip_safe=False,
)
