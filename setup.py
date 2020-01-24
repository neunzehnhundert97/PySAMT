from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="samt",
    version=0.4,
    author="neunzehnhundert97",
    packages=["samt"],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Communications :: Chat"
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    install_requires=['toml', 'telepot', 'aiotask_context', 'more-itertools'],
    extras_require={
        "Easy parsing": ["parse"],
        "Persistent storage": ["tinydb"]
    },
    url="https://github.com/neunzehnhundert97/SAMT"
)
