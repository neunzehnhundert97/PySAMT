import asyncio
import logging
import sys
from inspect import iscoroutinefunction
from os import path
from typing import Dict, Callable, Any

import aiotask_context as _context
import telepot
import telepot.aio.delegate
import toml
from telepot.aio.loop import MessageLoop

from marvin.helper import User, RegExDict, Message


def _load_configuration(filename: str) -> dict:
    """
    Loads the main configuration file from disk
    :param filename: The name of the user configuration file
    :return: The configuration as a dictionary
    """

    script_path = path.dirname(path.realpath(sys.argv[0]))
    return toml.load("{}/config/{}.toml".format(script_path, filename))


# Wrap the async context
context = _context


class Marvin:
    """
    The main class of this framework
    """

    def __init__(self):
        """
        Initialize the framework using the configuration file(s)
        """

        # Read configuration
        self._config = _load_configuration("Configuration")
        _Session.implicit_routing = self._config_value('bot', 'implicit_routing', default=False)
        _Session.config = self._config['bot']

        # Read language files
        if self._config_value('bot', 'implicit_routing', default=False) or self._config_value('bot', 'language_feature',
                                                                                              default=False):
            _Session.lang = _load_configuration("lang/default")

        # Initialize logger
        self._configure_logger()

        # Initialize bot
        self._create_bot()
        logging.info("Bot started")

    def listen(self) -> None:
        """
        Activates the bot by running it in a neverending asynchronous loop
        """

        # Creates an event loop
        loop = asyncio.get_event_loop()

        # Changes its task factory to use the async context provided by aiotask_context
        loop.set_task_factory(_context.copying_task_factory)

        # Creates the forever running bot listening function as task
        loop.create_task(MessageLoop(self._bot).run_forever(timeout=10))

        # Start the event loop to never end (of itself)
        loop.run_forever()

    def _create_bot(self) -> None:
        """
        Creates the bot using the telpot API
        """

        self._bot = telepot.aio.DelegatorBot(self._config_value('bot', 'token'), [
            telepot.aio.delegate.pave_event_space()(
                telepot.aio.delegate.per_chat_id(types=["private"]),
                telepot.aio.delegate.create_open,
                _Session,
                timeout=self._config_value('bot', 'timeout', default=10)),
        ])

    def _config_value(self, *keys, default: Any = None) -> Any:
        """
        Safely accesses any key in the configuration and returns a default value if it is not found
        :param keys: The keys to the config dictionary
        :param default: The value to return if nothing is found
        :return: Either the desired or the default value
        """

        # Traverse through the dictionaries
        step = self._config
        for key in keys:
            try:

                # Try to go one step deeper
                step = step[key]

            # A keyerror will abort the operation and return the default value
            except KeyError:
                return default

        return step

    def _configure_logger(self) -> None:
        """
        Configures the default python loggin module
        """

        # Convert the written level into the numeric one
        level = {"info": logging.INFO,
                 "debug": logging.DEBUG,
                 "warning": logging.WARNING,
                 "error": logging.ERROR,
                 "critical": logging.CRITICAL
                 }.get(self._config_value('general', 'logging').lower(), logging.WARNING)

        # Configure the logger
        logging.basicConfig(level=level,
                            datefmt="%X",
                            format="[%(asctime)s] %(message)s")

    @staticmethod
    def answer(message: str, regex: bool = False) -> Callable:
        """
        The wrapper for the inner decorator
        :param message: The message to react upon
        :param regex: If the given string should be treated as regular expression
        :return: The decorator itself
        """

        def decorator(func: Callable) -> Callable:
            """
            Adds the given method to the known routes
            :param func: The function to be called
            :return: The function unchanged
            """

            # Add the function keyed by the given message
            if not regex:
                _Session.simple_routes[message] = func
            else:
                _Session.regex_routes[message] = func
            return func

        # Return the decorator
        return decorator

    @staticmethod
    def default_answer(func: Callable) -> Callable:
        """
        A decorator for the function to be called if no other handler matches
        :param func: The function to be registered
        :return: The unchanged function
        """

        # Remember the function
        _Session.default_answer = func
        return func

    @staticmethod
    def default_sticker_answer(func: Callable) -> Callable:
        """
        A decorator for the function to be called if no other handler matches
        :param func: The function to be registered
        :return: The unchanged function
        """

        # Remember the function
        _Session.default_sticker_answer = func
        return func


class _Session(telepot.aio.helper.UserHandler):
    """
    The underlying framework telepot spawns an instance of this class for every conversation its encounters.
    It will be responsilbe for directing the bot's reactions
    """

    # The routing dictionaries
    simple_routes: Dict[str, Callable] = dict()
    regex_routes: RegExDict = RegExDict()

    # Language files
    lang = None

    # The relevant parts of the configuration, will be injected by the main classes constructor
    config = None

    def __init__(self, *args, **kwargs):
        """
        Initialize the session, called by the underlying framework telepot
        :param args: Used by telepot
        :param kwargs: Used by telepot
        """

        # Call superclasses superclass, allowing callback queries to be processed
        super(_Session, self).__init__(include_callback_query=True, *args, **kwargs)

        # Extract the user of the default arguments
        self.user = User(args[0][1]['from'])

        # Create dictionary to use as persistent storage
        self.storage = dict()

        if _Session.config.get('language_feature', False):
            self.language = self.load_language()

        logging.info(
            "User {} connected".format(self.user))

    def load_language(self) -> dict:
        """

        :return:
        """
        return _Session.lang

    async def on_close(self, timeout: int) -> None:
        """
        The function which will be called by telepot when the connection times out. Unused.
        :param timeout: The length of the exceeded timeout
        """

        pass

    async def on_callback_query(self) -> None:
        """
        The function which will be called by telepot if the incomming message is a callback query
        """

        pass

    async def on_chat_message(self, msg: dict) -> None:
        """
        The function which will be called by telepot
        :param msg: The reveived message as dictionary
        """

        # Tests, if it is normal message or something special
        if 'text' in msg:
            await self.handle_text_message(msg)
        elif 'sticker' in msg:
            await self.handle_sticker(msg)

    async def handle_text_message(self, msg: dict) -> None:
        """
        Processes a text message by routing it to the registered handlers and applying formatting
        :param msg: The received message as dictionary
        """

        text = msg['text']

        logging.debug("Message by {}: \"{}\"".format(self.user, text))

        # Prepare context for the user to access if needed
        _context.set('message', Message(msg))
        _context.set('user', self.user)
        _context.set('storage', self.storage)

        # Check, if the message is covered by one of the known simple routes
        if text in _Session.simple_routes:
            func = _Session.simple_routes[text]

        # Check, if the message is covered by one of the known regex routes
        elif text in _Session.regex_routes:
            func = _Session.regex_routes[text]

        # Route implicitly, if allowed
        elif _Session.implicit_routing and text in _Session.lang:
            await self.send(_Session.lang[text])
            return

        # After everything else has not matched, call the default handler
        else:
            func = _Session.default_answer

        # The user of the framework can choose freely between synchronous and asynchronous programming
        # So the program decides upon the signature how to call the function
        if iscoroutinefunction(func):
            answer = await func()
        else:
            answer = func()

        # If the language feature is wanted, it ist now applied
        if _Session.config.get('language_feature', False):

            # Convert answer into an list, if not already, to easy handling
            if not isinstance(answer, (tuple, list)):
                answer = answer,

            # Apply the language
            await self.apply_language(answer[0], *answer[1:] if len(answer) > 1 else [])
        else:
            await self.send(answer)

    async def handle_sticker(self, msg):
        """
        Processes a sticker either by sending a default answer or extracting the corresponding emojis
        :param msg: The received message as dictionary
        """

        # Extract the emojis associated with the sticker
        if _Session.config.get('extract_emojis', False):
            logging.debug("Sticker by {}, will be dismantled".format(self.user))
            msg['text'] = msg['sticker']['emoji']
            await self.handle_text_message(msg)

        # Or call the default handler
        else:
            logging.debug("Message by {}".format(self.user))

    async def apply_language(self, key: str, *format_content) -> None:
        """
        Uses the given key and formatting addition to answer the user the appropiate language
        :param key: the key to the right answer
        :param format_content: The format string contents
        """

        # Try to load the answer string
        try:
            answer: str = self.language[key]

        # Catch the keyerror which might be thrown
        except KeyError as e:

            # In strict mode, raise the error again, which will terminate the application
            if _Session.config.get('strict_mode', False):
                logging.critical('Language key "{}" not found!'.format(key))
                raise e

            # In non-strict mode just send the user the key as answer
            else:
                logging.info('Language key "{}" not found, sending itself instead'.format(key))
                await self.send(key)
                return

        # Apply formatting
        if format_content is not None and len(format_content) > 0:
            answer = answer.format(*format_content)

        # Send back
        await self.send(answer)

    async def send(self, msg: str):
        """
        Sends a message back to the user.
        This either might just be plaintext or another feature like stickers or photos
        :param msg: The message to be sent
        """

        # Check, which kind of sender method is appropiate
        method = {
            'sticker': self.sender.sendSticker,
            'photo': self.send_photo,
            'document': self.send_document,
            'video': self.send_video,
            'audio': self.send_audio,
            'voice': self.send_voice
        }

        command = ""
        payload = None
        if ":" in msg:
            command, payload = msg.split(":", 1)

        func = method.get(command, None)

        if func is not None:
            await method[command](payload)
        else:
            await self.sender.sendMessage(msg, parse_mode=_Session.config.get('markup', None))

    async def send_photo(self, file):
        await self.sender.sendPhoto(open(file, 'rb'))

    async def send_document(self, file):
        await self.sender.sendDocument(open(file, 'rb'))

    async def send_audio(self, file):
        await self.sender.sendAudio(open(file, 'rb'))

    async def send_voice(self, file):
        await self.sender.sendVoice(open(file, 'rb'))

    async def send_video(self, file):
        await self.sender.sendVideo(open(file, 'rb'))

    async def default_answer(self) -> str:
        """
        Sets the default answer function to do nothing if not overwritten
        """

        pass

    async def default_sticker_answer(self) -> str:
        """
        Sets the default sticker answer function to do nothing if not overwritten
        """

        pass
