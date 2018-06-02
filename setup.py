from setuptools import setup, find_packages

setup(
    name="marvin",
    version=0.1,
    author="neunzehnhundert97",
    packages=["marvin"],
    classifiers=["Development Status :: 2 - Pre-Alpha"],
    license="MIT",
    install_requires=['toml', 'telepot', 'aiotask_context']
)
