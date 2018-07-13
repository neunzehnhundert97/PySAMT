from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="marvin",
    version=0.2,
    author="neunzehnhundert97",
    packages=["marvin"],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Communications :: Chat"
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    install_requires=['toml', 'telepot', 'aiotask_context', 'parse'],
    url="https://github.com/neunzehnhundert97/marvin-telegram-bot"
)
