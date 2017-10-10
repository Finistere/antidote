from distutils.core import setup

setup(
    name='dependency_manager',
    version='0.1',
    packages=['dependency_manager'],
    author='Benjamin Rabier',
    install_requires=[
        'wrapt'
    ],
    extras_require={
        ":python_version<'3.3'": ["chainmap"],
        "attrs": ["attrs>=17.1"]
    }
)
