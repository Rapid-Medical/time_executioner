from setuptools import find_packages, setup

from time_executioner import __version__

setup(
    name="time_executioner",
    packages=find_packages(),
    version=__version__,
    description="Common library to time the execution of functions",
    long_description=open("USAGE.md").read(),
    long_description_content_type="text/markdown",
    author="Barclay Loftus / Rapid Medical",
    author_email="barclay.loftus@rmdevmgmt.com",
    install_requires=["pytest"],
    license="MIT",
    python_requires=">=3.7",
)
