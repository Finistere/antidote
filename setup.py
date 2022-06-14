import os
import pathlib

from setuptools import find_packages, setup

here = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))

with open(str(here / "README.rst"), "r") as f:
    readme = f.read()

setup(
    name="antidote",
    use_scm_version=dict(write_to="src/antidote/_internal/scm_version.py"),
    description="Dependency injection.",
    long_description=readme,
    author="Benjamin Rabier",
    url="https://github.com/Finistere/antidote",
    packages=find_packages("src"),
    package_dir={"": "src"},
    package_data={"antidote": ["py.typed"]},
    include_dirs=["src"],
    ext_modules=[],
    python_requires=">=3.7,<4",
    install_requires=["typing_extensions"],
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable ",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    keywords="dependency injection",
    zip_safe=False,
)
