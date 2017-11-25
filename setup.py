from distutils.core import setup

setup(
    name='antidote',
    version='0.1',
    packages=['antidote'],
    author='Benjamin Rabier',
    install_requires=[
        'wrapt',
        'future'
    ],
    extras_require={
        ":python_version<'3'": ["chainmap"],
        "attrs": ["attrs>=17.1"]
    }
)
