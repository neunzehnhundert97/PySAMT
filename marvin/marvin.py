import asyncio
import logging
import sys
import traceback
import types
from inspect import iscoroutinefunction
from os import path
from typing import Dict, Callable, Any, Tuple, Iterable, Union

import aiotask_context as _context
import telepot
import telepot.aio.delegate
import toml
from telepot.aio.loop import MessageLoop
from telepot.exception import TelegramError

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

        # Config Answer class
        Answer.load_defaults()

        # Initialize bot
        self._create_bot()
        logger.info("Bot started")

    def listen(self) -> None:
        """
        Activates the bot by running it in a never ending asynchronous loop
        """

        # Creates an event loop
        global loop
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


class Answer(object):
    """
    An object to describe more complex answering behavior
    """

    def __init__(self, msg: str, *format_content: Any, delay: int = 0):
        """
        :param msg: The message included in this answer
        """

        self._msg = msg
        self.format_content = format_content
        self.delay = delay

    def _apply_language(self) -> str:
        """
        Uses the given key and formatting addition to answer the user the appropriate language
        :param key: the key to the right answer
        :param format_content: The format string contents
        :return The formatted answer
        """

        # The language code should be something like de, but could be also like de_DE or non-existent
        lang_code = _context.get('user').language_code.split('_')[0].lower()
        answer = None

        try:
            answer: str = _Session.language[lang_code][self._msg]

        except KeyError:
            # Try to load the answer string
            try:
                answer: str = _Session.language['default'][self._msg]

            # Catch the key error which might be thrown
            except KeyError as e:

                # In strict mode, raise the error again, which will terminate the application
                if self.strict_mode:
                    logger.critical('Language key "{}" not found!'.format(self._msg))
                    raise e

                # In non-strict mode just send the user the key as answer
                else:
                    return self._msg

        # Apply formatting
        if self.format_content is not None and len(self.format_content) > 0:
            answer = answer.format(*self.format_content)

        # Write back
        return answer

    @property
    def msg(self) -> str:
        """
        Returns either the message directly or the formatted one
        :return: The final message to be sent
        """

        if self.language_feature:
            return self._apply_language()
        else:
            return self._msg

    def get_config(self) -> Dict[str, Any]:
        """

        :return: kwargs for the sending of the answer
        """

        return {
            "parse_mode": self.markup,
            "reply_to_message_id": _context.get('message').id if self.mark_as_answer else None
        }

    @classmethod
    def load_defaults(cls) -> None:
        """
        Load default values from config
        """

        cls.mark_as_answer = _config_value('bot', 'mark_as_answer', default=False)
        cls.markup = _config_value('bot', 'markup', default=None)
        cls.language_feature = _config_value('bot', 'language_feature', default=False)
        cls.strict_mode = _config_value('bot', 'strict_mode')


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
        log = f'Message by {self.user}: "{text}"'

        # Prepare the context
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
            func, matching = _Session.regex_routes[text]
            kwargs = matching.groupdict()

        # After everything else has not matched, call the default handler
        else:
            func = _Session.default_answer

        # Call the matching function to process the message and catch any exceptions
        try:

            # The user of the framework can choose freely between synchronous and asynchronous programming
            # So the program decides upon the signature how to call the function
            if iscoroutinefunction(func):
                answer = await func(*args, **kwargs)
            else:
                answer = func(*args, **kwargs)

        except Exception as e:

            # Depending of the exceptions type, the specific message is on a different index
            if isinstance(e, OSError):
                msg = e.args[1]
            else:
                msg = e.args[0]
            err = traceback.extract_tb(sys.exc_info()[2])[-1]
            err = "\n\tDuring the processing occured an error\n\t\tError message: {}\n\t\tFile: {}\n\t\tFunc: {}" \
                  "\n\t\tLiNo: {}\n\t\tLine: {}\n\tNothing was returned to the user" \
                .format(msg, err.filename.split("/")[-1], err.name, err.lineno, err.line)
            logger.warning(log + err)

            # Send error message, if configured
            await self.handle_error()

        else:
            await self.prepare_answer(answer, log)

    async def prepare_answer(self, answer: Union[Answer, Iterable], log: str = "") -> None:
        """

        :param answer:
        :param log:
        :return:
        """

        try:

            # None as return will result in no answer being sent
            if answer is None:
                logger.info(log + "\nNo answer was given")
                return

            # Convert into a complex answer to unify processing
            if not isinstance(answer, (Answer, list, tuple, types.GeneratorType)):
                answer = Answer(str(answer))
            elif isinstance(answer, (tuple, list)) and not isinstance(answer[0], Answer):
                answer = Answer(str(answer[0]), *answer[1:])

            # Handle complex answer
            if isinstance(answer, Answer):
                await self.handle_complex_answer((answer,))

            # Handle multiple complex answers
            elif isinstance(answer, (tuple, list, types.GeneratorType)):
                await self.handle_complex_answer(answer)

        except FileNotFoundError as e:
            err = '\n\tThe request could not be fulfilled as the file "{}" could not be found'.format(e.filename)
            logger.warning(log + err)

            # Send error message, if configured
            await self.handle_error()
            return

        except TelegramError as e:
            err = '\n\tThe request could not be fulfilled as an API error occured:' \
                  '\n\t\t{}' \
                  '\n\tNothing was returned to the user'.format(e.args[0])
            logger.warning(log + err)

            # Send error message, if configured
            await self.handle_error()
            return

        except Exception as e:

            # Depending of the exceptions type, the specific message is on a different index
            if isinstance(e, OSError):
                msg = e.args[1]
            else:
                msg = e.args[0]
            err = traceback.extract_tb(sys.exc_info()[2])[-1]
            err = "\n\tDuring the sending of the bot's answer occured an error\n\t\tError message: {}\n\t\tFile: {}" \
                  "\n\t\tFunc: {}\n\t\tLiNo: {}\n\t\tLine: {}\n\tNothing was returned to the user" \
                  "\n\tYou may report this bug as it either should not have occured" \
                  "or should have been properly caught" \
                .format(msg, err.filename.split("/")[-1], err.name, err.lineno, err.line)
            logger.warning(log + err)

            # Send error message, if configured
            await self.handle_error()

        else:

            if log is not None and len(log) > 0:
                logger.info(log)

    async def handle_sticker(self, msg: Dict) -> None:
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
        answer = await self.default_sticker_answer()
        self.prepare_answer(answer)

    async def handle_error(self) -> None:
        """
        Informs the connected user that an exception occured, if enabled
        """

        if _config_value('bot', 'error_reply', default=None) is not None:
            await self.prepare_answer(Answer(_config_value('bot', 'error_reply')))

    async def handle_complex_answer(self, answers: Iterable[Answer]) -> None:
        """
        Handle Answer objects
        :param answers: Answer objects to be sent
        """

        answer: Answer = None
        for answer in answers:
            await self.send(answer.msg, **answer.get_config(), delay=answer.delay)

    async def send(self, msg: str, delay: int = 0, **kwargs) -> None:
        """
        Sends a message back to the user.
        This either might just be plaintext or another feature like stickers or photos
        :param msg: The message to be sent
        :param delay: Time in seconds the message may be delayed
        """

        # Delay sending
        if delay > 0:

            # Define a function to delay a recursive call
            async def wait(x: int):
                await asyncio.sleep(x)
                await self.send(msg, **kwargs)

            loop.create_task(wait(delay))
            return

        # Cast the message to a string to circumvent errors
        if not isinstance(msg, str):
            msg = str(msg)

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

        func: Callable = method.get(command, None)

        # Call the appropriate function
        if func is not None:
            await method[command](payload, caption, **kwargs)
        else:
            await self.sender.sendMessage(msg, **kwargs)

    async def send_photo(self, file: str, caption: str, **kwargs) -> None:
        """
        Sends a photo to the user
        :param file: A path either relative or absolute to the file to send
        :param caption: The caption to be shown on the media
        """

        await self.sender.sendPhoto(open(file, 'rb'), caption, **kwargs)

    async def send_document(self, file: str, caption: str, **kwargs) -> None:
        """
        Sends a document to the user
        :param file: A path either relative or absolute to the file to send
        :param caption: The caption to be shown on the media
        """

        await self.sender.sendDocument(open(file, 'rb'), caption, **kwargs)

    async def send_audio(self, file: str, caption: str, **kwargs) -> None:
        """
        Sends a audio to the user
        :param file: A path either relative or absolute to the file to send
        :param caption: The caption to be shown on the media
        """

        await self.sender.sendAudio(open(file, 'rb'), caption, **kwargs)

    async def send_voice(self, file: str, caption: str, **kwargs) -> None:
        """
        Sends a voice to the user
        :param file: A path either relative or absolute to the file to send
        :param caption: The caption to be shown on the media
        """

        await self.sender.sendVoice(open(file, 'rb'), caption, **kwargs)

    async def send_video(self, file: str, caption: str, **kwargs) -> None:
        """
        Sends a video to the user
        :param file: A path either relative or absolute to the file to send
        :param caption: The caption to be shown on the media
        """

        await self.sender.sendVideo(open(file, 'rb'), caption=caption, **kwargs)

    @staticmethod
    async def default_answer() -> Union[str, Answer, Iterable[str], None]:
        """
        Sets the default answer function to do nothing if not overwritten
        """

        pass

    @staticmethod
    async def default_sticker_answer() -> Union[str, Answer, Iterable[str], None]:
        """
        Sets the default sticker answer function to do nothing if not overwritten
        """

        pass
