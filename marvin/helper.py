import re
from datetime import datetime
from typing import Hashable, Any

import aiotask_context


class User:
    """
    A wrapper around the user information which are by default contained in a dictionary
    """

    def __init__(self, user: dict):
        # Safe all usefull information as attributes
        self.id = user.get("id")
        self.is_bot = user.get('is_bot')
        self.first_name = user.get('first_name')
        self.last_name = user.get('last_name', "")
        self.username = user.get('username', "")
        self.language_code = user.get('language_code', "")

    def __str__(self):
        return "{} {}".format(self.first_name, self.last_name)

    def __repr__(self):
        return "{} ({} {} [{}])".format(self.username, self.first_name, self.last_name, self.id)


class Message:
    """
    A wrapper around the message information which are by default contained in a dictionary
    """

    def __init__(self, msg: dict):
        # Safe all usefull information as attributes
        self.date = datetime.fromtimestamp(msg['date'])
        self.text = msg.get('text', None)


class Sticker:
    """
    A wrapper around the sticker information which are by default contained in a dictionary
    """

    def __init__(self, sticker: dict):
        # Safe all usefull information as attributes
        self.emoji = sticker['emoji']
        self.file_id = sticker['file_id']
        self.file_size = sticker['file_size']
        self.heigth = sticker['height']
        self.set_name = sticker['set_name']


class Context:
    """
    A wrapper around the aiotask_context to use additional functions
    """

    @staticmethod
    def get(key: Hashable, default=None) -> Any:
        """
        Retrieves an value of the async context or the session storage in this order
        :param key: The key to get
        :param default: The value to return, if nothing is found
        :return:
        """

        # First try to find the value in the context
        value = aiotask_context.get(key)

        # If not found, try to find it in the session storage
        if value is None:
            value = aiotask_context.get('_<[storage]>_').get(key, default)

        return value

    @staticmethod
    def set(key: Hashable, value: Any) -> None:
        """
        Puts the given key value pair into the session storage
        :param key: The key for the value to be associated with
        :param value: The value to be inserted
        """

        # Check for a conflict
        if aiotask_context.get(key) is not None:
            raise KeyError("This key is occupied by the framework")
        else:
            aiotask_context.get('_<[storage]>_')[key] = value


# Source: https://djangosnippets.org/snippets/309/
class RegExDict(object):
    """A dictionary-like object for use with regular expression keys.
    Setting a key will map all strings matching a certain regex to the
    set value.

    One caveat: the order of the iteration over items is unspecified,
    thus if a lookup matches multiple keys, it is unspecified which
    value will be returned - still, one such value will be returned.
    """

    def __init__(self):
        self._regexes = {}

    def __getitem__(self, name):
        for regex, value in self._regexes.items():
            m = regex.match(name)
            if m is not None:
                return value
        raise KeyError('Key does not match any regex')

    def __contains__(self, item):
        try:
            self[item]
        except KeyError:
            return False
        else:
            return True

    def __setitem__(self, regex, value):
        self._regexes[re.compile(regex)] = value
