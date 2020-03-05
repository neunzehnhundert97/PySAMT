# SAMT

This framework on top of [telepot](https://github.com/nickoala/telepot) is intended to ease the creation of simple Telegram chat bots. With a syntax as seen in web frameworks like [flask](https://github.com/pallets/flask), writing the bot will only be about defining what the bot will answer to certain messages, skipping the lower levels involved.

## A simple example

Bot.py

```python
from samt import Bot

bot = Bot()

@bot.answer("/start")
def start():
    return "Hello, new user, how can I help you?"
    
if __name__ == "__main__":
    bot.listen()

```

config/config.toml

```ini
[general]
# Sets the log level for stdout
logging = "DEBUG"

[bot]
# The Bot API token
token = "The token you got by the botfather"
```

## Installation

The package is currently not (yet) available on PyPI, but you may download the repository as zip or by using ```git clone```. Then you can use the setup.py to install the module locally by using ```pip install .```. Alternatively, you can use the git integration of pip and combine boths steps into ```pip install git+https://github.com/neunzehnhundert97/samt```.

## Notes

The project is currently still under construction, so many things are intended to be added or can change from commit to commit. If you encounter bugs (which seems likely to me), want to suggest a new feature or have a general comment, feel free to contact me.
