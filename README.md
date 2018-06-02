# Marvin

This framework ontop of [telepot](https://github.com/nickoala/telepot) is intended to ease the creation of simple Telegram chat bots. With a syntax as seen in web frameworks like [flask](https://github.com/pallets/flask), writing the bot will only be about defining what the bot answer to certain message, skipping the lower levels involved.

## A simple example

./Bot.py

```python
from marvin import Marvin

bot = Marvin()

@bot.answer("/start")
def start():
    return "Hello, new user, how can I help you?"

```

./config/Configuration.toml

```ini
[general]
# Sets the log level for stdout
logging = "DEBUG"

[bot]
# The Bot API token
token = "The token you got by the botfather"
```

## Installation

The package is currently not (yet) available on PyPI, but you may download the repository as zip or by using git clone. Then you can either use the setup.py to install the module locally by typing pip install . or just put the files into your project.

## Notes

The project is currently still under construction, so many things are intended to be added or can change from commit to commit. If encounter bugs (which seems likely to me), want to suggest a new feature or have a general comment, feel free to contact me.
