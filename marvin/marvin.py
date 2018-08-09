import asyncio
import logging
import sys
import traceback
from inspect import iscoroutinefunction
from os import path
from typing import Dict, Callable, Any, Tuple

import aiotask_context as _context
import telepot
import telepot.aio.delegate
import toml
from telepot.aio.loop import MessageLoop

from marvin.helper import User, RegExDict, Message, Mode, ParsingDict

logger = logging.getLogger(__name__)


def _load_configuration(filename: str) -> dict:
    """
    Loads the main configuration file from disk
    :param filename: The name of the user configuration file
    :return: The configuration as a dictionary
    """

    script_path = path.dirname(path.realpath(sys.argv[0]))
    return toml.load(f"{script_path}/config/{filename}.toml")


def _config_value(*keys, default: Any = None) -> Any:
    """
    Safely accesses any key in the configuration and returns a default value if it is not found
    :param keys: The keys to the config dictionary
    :param default: The value to return if nothing is found
    :return: Either the desired or the default value
    """

    # Traverse through the dictionaries
    step = _config
    for key in keys:
        try:

            # Try to go one step deeper
            step = step[key]

        # A keyerror will abort the operation and return the default value
        except KeyError:
            return default

    return step


def _handle_exit(signum, frame):
    print(type(signum))
    print(type(frame))


class Marvin:
    """
    The main class of this framework
    """

    def __init__(self):
        """
        Initialize the framework using the configuration file(s)
        """

        # Read configuration
        global _config
        try:
            _config = _load_configuration("Configuration")
        except FileNotFoundError:
            logger.critical("The configuration file could not be found. Please make sure there is a file called " +
                            "Configuration.toml in the directory config.")
            quit(-1)

        # Read language files
        if _config_value('bot', 'implicit_routing', default=False) \
                or _config_value('bot', 'language_feature', default=False):
            _Session.language = _load_configuration("Languages")

        # Initialize logger
        self._configure_logger()

        # Initialize bot
        self._create_bot()
        logger.info("Bot started")

    def listen(self) -> None:
        """
        Activates the bot by running it in a never ending asynchronous loop
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
        Creates the bot using the telepot API
        """

        self._bot = telepot.aio.DelegatorBot(_config_value('bot', 'token'), [
            telepot.aio.delegate.pave_event_space()(
                telepot.aio.delegate.per_chat_id(types=["private"]),
                telepot.aio.delegate.create_open,
                _Session,
                timeout=_config_value('bot', 'timeout', default=31536000)),
        ])

    @staticmethod
    def _configure_logger() -> None:
        """
        Configures the default python logging module
        """

        # Deactivate loggers of imported modules
        log = logging.getLogger("parse")
        log.setLevel(logging.CRITICAL)

        # Convert the written level into the numeric one
        level = {"info": logging.INFO,
                 "debug": logging.DEBUG,
                 "warning": logging.WARNING,
                 "error": logging.ERROR,
                 "critical": logging.CRITICAL
                 }.get(_config_value('general', 'logging', default="error").lower(), logging.WARNING)

        # Configure the logger
        logger.setLevel(level)
        shandler = logging.StreamHandler()
        fhandler = logging.FileHandler(
            f"{path.dirname(path.realpath(sys.argv[0]))}/{_config_value('general', 'logfile', default='Bot.log')}")
        formatter = logging.Formatter("[%(asctime)s] %(message)s", "%X")
        shandler.setFormatter(formatter)
        fhandler.setFormatter(formatter)
        logger.addHandler(shandler)
        logger.addHandler(fhandler)

    @staticmethod
    def answer(message: str, mode: Mode = Mode.DEFAULT) -> Callable:
        """
        The wrapper for the inner decorator
        :param message: The message to react upon
        :param mode: The mode by which to interpret the given string
        :return: The decorator itself
        """

        def decorator(func: Callable) -> Callable:
            """
            Adds the given method to the known routes
            :param func: The function to be called
            :return: The function unchanged
            """

            # Add the function keyed by the given message
            if mode == Mode.REGEX:
                _Session.regex_routes[message] = func
            if mode == Mode.PARSE:
                _Session.parse_routes[message] = func
            else:
                _Session.simple_routes[message] = func

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
    It will be responsible for directing the bot's reactions
    """

    # The routing dictionaries
    simple_routes: Dict[str, Callable] = dict()
    parse_routes: ParsingDict = ParsingDict()
    regex_routes: RegExDict = RegExDict()

    # Language files
    language = None

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

        logger.info(
            "User {} connected".format(self.user))

    async def on_close(self, timeout: int) -> None:
        """
        The function which will be called by telepot when the connection times out. Unused.
        :param timeout: The length of the exceeded timeout
        """
        logger.info("User {} timed out".format(self.user))

        pass

    async def on_callback_query(self) -> None:
        """
        The function which will be called by telepot if the incoming message is a callback query
        """

        pass

    async def on_chat_message(self, msg: dict) -> None:
        """
        The function which will be called by telepot
        :param msg: The received message as dictionary
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
        logger.debug(f"Message by {self.user}: \"{text}\"")

        # Prepare context for the user to access if needed
        _context.set('message', Message(msg))
        _context.set('user', self.user)
        _context.set('_<[storage]>_', self.storage)

        args: Tuple = ()
        kwargs: Dict = {}

        # Check, if the message is covered by one of the known simple routes
        if text in _Session.simple_routes:
            func = _Session.simple_routes[text]

        # Check, if the message is covered by one of the known parse routes
        elif text in _Session.parse_routes:
            func, matching = _Session.parse_routes[text]
            kwargs = matching.named

        # Check, if the message is covered by one of the known regex routes
        elif text in _Session.regex_routes:
            func = _Session.regex_routes[text]

        # After everything else has not matched, call the default handler
        else:
            func = _Session.default_answer

        # The user of the framework can choose freely between synchronous and asynchronous programming
        # So the program decides upon the signature how to call the function
        try:
            if iscoroutinefunction(func):
                answer = await func(*args, **kwargs)
            else:
                answer = func(*args, **kwargs)
        except Exception as e:
            text = e.args[0]
            err = traceback.extract_tb(sys.exc_info()[2])[-1]
            err = "\tError message: {}\n\tFile: {}\n\tFunc: {}\n\tLiNo: {}\n\tLine: {}".format(
                text, err.filename.split("/")[-1], err.name, err.lineno, err.line)
            logger.warning(
                'An error was caused during processing the message "{}" by {}\n{}'.format(text, self.user, err))
            answer = None

        # A none answer wil  be seen as order to stay silent
        if answer is None:
            logger.info("No answer was given")
            return

        # If the language feature is wanted, it ist now applied
        if _config_value('bot', 'language_feature', default=False):

            # Convert answer into an tuple, if not already, to easy handling
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
        if _config_value('bot', 'extract_emojis', default=False):
            logger.debug("Sticker by {}, will be dismantled".format(self.user))
            msg['text'] = msg['sticker']['emoji']
            await self.handle_text_message(msg)

        # Or call the default handler
        else:
            logger.debug("Message by {}".format(self.user))

    async def apply_language(self, key: str, *format_content) -> None:
        """
        Uses the given key and formatting addition to answer the user the appropriate language
        :param key: the key to the right answer
        :param format_content: The format string contents
        :return The formatted answer
        """

        # The language code should be something like de, but could be also like de_DE or non-existent
        lang_code = self.user.language_code.split('_')[0].lower()

        try:
            answer: str = _Session.language[lang_code][key]

        except KeyError:
            # Try to load the answer string
            try:
                answer: str = _Session.language['default'][key]

            # Catch the keyerror which might be thrown
            except KeyError as e:

                # In strict mode, raise the error again, which will terminate the application
                if _config_value('strict_mode', default=False):
                    logger.critical('Language key "{}" not found!'.format(key))
                    raise e

                # In non-strict mode just send the user the key as answer
                else:
                    logger.info('Language key "{}" not found, sending itself instead'.format(key))
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

        # Cast the message to a string to circumvent errors
        if not isinstance(msg, str):
            msg = str(msg)

        # Prepare kwargs according to the configurations
        kwargs = {
            "parse_mode": _config_value('bot', 'markup', default=None),
            "reply_to_message_id": _context.get('message').id if _config_value('bot', 'mark_as_answer',
                                                                               default=False) else None,
        }

        # Create dictionary to switch between functions
        method = {
            'sticker': self.sender.sendSticker,
            'photo': self.send_photo,
            'document': self.send_document,
            'video': self.send_video,
            'audio': self.send_audio,
            'voice': self.send_voice
        }

        # Try to detect a relevant command
        command = ""
        payload = None
        caption = None
        if ":" in msg:
            command, payload = msg.split(":", 1)
            if ";" in payload:
                payload, caption = payload.split(";", 1)

        func = method.get(command, None)

        # Call the appropriate function
        if func is not None:
            await method[command](payload, caption, **kwargs)
        else:
            await self.sender.sendMessage(msg, **kwargs)

    async def send_photo(self, file, caption, **kwargs):
        """
        Sends a photo to the user
        :param file: A path either relative or absolute to the file to send
        """

        await self.sender.sendPhoto(open(file, 'rb'), caption, **kwargs)

    async def send_document(self, file, caption, **kwargs):
        """
        Sends a document to the user
        :param file: A path either relative or absolute to the file to send
        """

        await self.sender.sendDocument(open(file, 'rb'), caption, **kwargs)

    async def send_audio(self, file, caption, **kwargs):
        """
        Sends a audio to the user
        :param file: A path either relative or absolute to the file to send
        """

        await self.sender.sendAudio(open(file, 'rb'), caption, **kwargs)

    async def send_voice(self, file, caption, **kwargs):
        """
        Sends a voice to the user
        :param file: A path either relative or absolute to the file to send
        """

        await self.sender.sendVoice(open(file, 'rb'), caption, **kwargs)

    async def send_video(self, file, **kwargs):
        """
        Sends a video to the user
        :param file: A path either relative or absolute to the file to send
        """

        await self.sender.sendVideo(open(file, 'rb'), **kwargs)

    @staticmethod
    async def default_answer() -> str:
        """
        Sets the default answer function to do nothing if not overwritten
        """

        pass

    @staticmethod
    async def default_sticker_answer() -> str:
        """
        Sets the default sticker answer function to do nothing if not overwritten
        """

        pass
