import os
from setuptools import setup


# Structure of this lifted from and thanks to 
# https://pythonhosted.org/an_example_pypi_project/setuptools.html

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "Nanobot",
    version = "0.5.1",
    author = "Brett g Porter",
    author_email = "bgp@bgporter.net",
    description = "A tiny twitterbot framework.",
    license = "MIT",
    keywords = "twitter twitterbot bot framework",
    url = "https://github.com/bgporter/nanobot",
    packages=['nanobot'],
    install_requires = ['twython>=3.3.0'],
    long_description=read('README.rst'),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "License :: OSI Approved :: MIT License",
    ],
)
