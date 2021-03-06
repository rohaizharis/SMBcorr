import os
from setuptools import setup, find_packages

# get long_description from README.md
with open("README.md", "r") as fh:
    long_description = fh.read()

# get install requirements
with open('requirements.txt') as fh:
    install_requires = [line.split().pop(0) for line in fh.read().splitlines()]

# get version
with open('version.txt') as fh:
    version = fh.read()

# list of all scripts to be included with package
scripts=[os.path.join('scripts',f) for f in os.listdir('scripts') if f.endswith('.py')]

setup(
    name='SMBcorr',
    version=version,
    description='Python-based tools for correcting altimetry data for surface mass balance and firn processes',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/tsutterley/SMBcorr',
    author='Tyler Sutterley',
    author_email='tsutterl@uw.edu',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Physics',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='Surface Mass Balance, firn height, ICESat, ICESat-2, Operation IceBridge',
    packages=find_packages(),
    install_requires=install_requires,
    scripts=scripts,
    include_package_data=True,
)
