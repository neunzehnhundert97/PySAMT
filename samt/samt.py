import asyncio
import logging
import math
import platform
import signal
import sys
import traceback
import types
from collections import deque
from inspect import iscoroutinefunction, isgenerator, isasyncgen
from os import path, system
from typing import Dict, Callable, Tuple, Iterable, Union, Collection

import aiotask_context as _context
import collections
import telepot
import telepot.aio.delegate
import toml
from telepot.aio.loop import MessageLoop
from telepot.exception import TelegramError
from telepot.namedtuple import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, \
    ReplyKeyboardRemove
from more_itertools import flatten, first_true

from samt.helper import *

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

        # A key error will abort the operation and return the default value
        except KeyError:
            return default

    return step


class Bot:
    """
    The main class of this framework
    """

    _on_termination = lambda: None

    def __init__(self):
        """
        Initialize the framework using the configuration file(s)
        """

        # Read configuration
        global _config
        try:
            _config = _load_configuration("config")
        except FileNotFoundError:
            logger.critical("The configuration file could not be found. Please make sure there is a file called " +
                            "config.toml in the directory config.")
            quit(-1)

        # Initialize logger
        self._configure_logger()

        # Read language files
        if _config_value('bot', 'language_feature', default=False):
            try:
                _Session.language = _load_configuration("lang")
            except FileNotFoundError:
                logger.critical("The language file could not be found. Please make sure there is a file called " +
                                "lang.toml in the directory config or disable this feature.")
                quit(-1)

        signal.signal(signal.SIGINT, Bot.signal_handler)

        # Prepare empty stubs
        self._on_startup = None

        # Create access level dictionary
        self.access_checker = dict()

        # Config Answer class
        Answer._load_defaults()

        # Load database
        if _config_value('general', 'persistent_storage', default=False):
            name = _config_value('general', 'storage_file', default="db.json")
            args = _config_value('general', 'storage_args', default=" ").split(" ")
            _Session.database = self._initialize_persistent_storage(name, *args)
        else:
            _Session.database = None

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
        loop.create_task(MessageLoop(self._bot).run_forever(timeout=None))

        # Create the startup as a separated task
        loop.create_task(self.schedule_startup())

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
        formatter = logging.Formatter("[%(asctime)s] %(message)s", "%x %X")
        shandler.setFormatter(formatter)
        fhandler.setFormatter(formatter)
        logger.addHandler(shandler)
        logger.addHandler(fhandler)

    @staticmethod
    def _initialize_persistent_storage(*args):
        """
        Creates the default database
        :param args: The file name to be used
        :return: The database connection
        """
        return TinyDB(args[0])

    @staticmethod
    def init_storage(func: Callable):
        """
        Decorator to replace the default persistent storage
        :param func: The function which initializes the storage
        :return: The unchanged function
        """
        Bot._initialize_persistent_storage = func
        return func

    @staticmethod
    def load_storage(func: Callable):
        """
        Decorator to replace the default load method for the persistent storage
        :param func: The function which loads the user date
        :return: The unchanged function
        """
        _Session.load_user_data = func

    @staticmethod
    def update_storage(func: Callable):
        """
        Decorator to replace the default update method for the persistent storage
        :param func: The function which updates the user data
        :return: The unchanged function
        """
        _Session.update_user_data = func

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

    async def schedule_startup(self):
        """
        If defined, executes the startup generator and processes the yielded answers
        """

        class Dummy:
            pass

        dummy = Dummy()
        dummy.user_id = None
        dummy.bot = self._bot

        if self._on_startup is None:
            return

        gen = self._on_startup()

        if isinstance(gen, types.AsyncGeneratorType):
            async for answer in gen:
                # answer.language_feature = False
                await answer._send(dummy)

    def on_startup(self, func: types.CoroutineType):
        """
        A decorator for a function to be awaited on the program's startup
        :param func:
        """

        # Remember the function
        self._on_startup = func

    @classmethod
    def on_termination(cls, func):
        """
        A decorator for a function to be called on the program's termination
        :param func:
        """

        cls._on_termination = func

    @classmethod
    def on_message_overflow(cls, func):
        """
        A decorator for a function to be called when a message exceeds the maximal length
        :param func:
        """

        cls._on_message_overflow = func

    @staticmethod
    def _on_message_overflow(answer):
        """

        :param answer: The answer which exceeded the maximal length
        :return: A tuple with a new message, media type, and media
        """

        with open("Temp" + str(hash(answer)) + ".txt", "w") as f:
            f.write(answer.msg + "\n")

        # Schedule removal of the temp file after 5 seconds
        if platform.system() == "Windows":
            system('start /B cmd /C "sleep 5 && del Temp' + str(hash(answer)) + '.txt"')
        else:
            system('bash -c "sleep 5; rm Temp' + str(hash(answer)) + '.txt" &')

        return "", Media.DOCUMENT, "Temp" + str(hash(answer)) + ".txt"

    @staticmethod
    def signal_handler(sig, frame):
        """
        A signal handler to catch a termination via CTR-C
        """

        Bot._on_termination()
        logger.info("Bot shuts down")
        quit(0)

    @staticmethod
    def before_processing(func: Callable):
        """
        A decorator for a function, which shall be called before each message procession
        :param func:
        """

        Bot._before_function = func

    def check_access_level(self, level: str):
        """
        The wrapper for the inner decorator
        :param level: The access level that is evaluated by the decorated function
        :return: The decorator
        """

        def decorator(func: Callable):
            """

            :param func: The function to be registered
            :return: The unchanged function
            """

            self.access_checker[level] = func

            return func

        return decorator

    def access_level(self, *levels: str):
        """
        The wrapper for the inner decorator
        :param levels: The access levels that grant permission for the decorated function.
        :return: The decorator
        """

        def decorator(func: Callable):
            """
            Wrapper for the decorating function
            :param func: The function to be protected
            :return: The decorated function
            """

            async def inner(**kwargs):
                """
                Checks all given access levels and calls the given function if one of them evaluated to true
                :return: The message handler's usual output or None
                """

                # Iterate through all given levels
                for level in levels:
                    if self.access_checker.get(level, lambda: False)():

                        # If one level evaluated to True, call the function as usual
                        if iscoroutinefunction(func):
                            return await func(**kwargs)
                        else:
                            return func(**kwargs)

                # If no level evaluated to True, raise error
                raise AuthorizationError()

            return inner

        return decorator

    def ensure_parameter(self, name: str, phrase: str, choices: Collection[str] = None):
        """
        The wrapper for the inner decorator
        :param name: The name of the parameter to provide
        :param phrase: The phrase to use when asking the user for the parameter
        :param choices: The choices to show the user as callback
        :return: The decorator
        """

        def decorator(func: Callable):
            """
            Wrapper for the decorating function
            :param func: The function to be protected
            :return: The decorated function
            """

            async def inner(**kwargs):
                """
                Checks if the requested parameter exists and aks the user to provide it, if it misses
                :return: The message handler's usual output
                """

                # Check if the parameter exists
                if name not in kwargs:
                    # If not, ask the user for it
                    temp = (yield Answer(phrase, choices=choices))
                    kwargs[name] = temp

                # If one level evaluated to True, call the function as usual
                if iscoroutinefunction(func):
                    yield await func(**kwargs)
                else:
                    yield func(**kwargs)

            return inner

        return decorator

    @staticmethod
    def _before_function():
        return True


class Answer(object):
    """
    An object to describe the message behavior
    """

    media_commands = {
        'sticker': Media.STICKER,
        'voice': Media.VOICE,
        'audio': Media.AUDIO,
        'photo': Media.PHOTO,
        'video': Media.VIDEO,
        'document': Media.DOCUMENT,
    }

    def __init__(self, msg: str = None,
                 *format_content: Any,
                 choices: Collection = None,
                 callback: Callable = None,
                 keyboard: Collection = None,
                 media_type: Media = None,
                 media: str = None,
                 caption: str = None,
                 receiver: Union[str, int, User] = None,
                 edit_id: int = None):
        """
        Initializes the answer object
        :param msg: The message to be sent, this can be a language key or a command for a media type
        :param format_content: If the message is a language key, the format arguments might be supplied here
        :param choices: The choices to be presented the user as a query, either as Collection of strings, which will
            automatically be aligned or as a Collection of Collection of strings to control the alignment. This argument
            being not None is the indicator of being a query
        :param callback: The function to be called with the next incoming message by this user. The message will be
            propagated as parameter.
        :param keyboard: A keyboard to be sent, either as Collection of strings, which will
            automatically be aligned or as a Collection of Collection of strings to control the alignment.
        :param media_type: The media type of this answer. Can be used instead of the media commands.
        :param media: The path to the media to be sent. Can be used instead of the media commands.
        :param caption: The caption to be sent. Can be used instead of the media commands.
        :param receiver: The user ID or a user object of the user who should receiver this answer. Will default to the
            user who sent the triggering message.
        :param edit_id: The ID of the message whose text shall be updated.
        """

        self._msg = msg
        self.receiver = receiver
        self.format_content = format_content
        self.choices = choices
        self.callback = callback
        self.keyboard = keyboard
        self.media_type: Media = media_type
        self.media = media
        self.caption = caption
        self.edit_id = edit_id

    async def _send(self, session) -> Dict:
        """
        Sends this instance of answer to the user
        :param session: The user's instance of _Session
        :return : The send message as dictionary
        """

        # Load the recipient's id
        if self.receiver is None:
            ID = session.user_id
        else:
            ID = self.receiver
            self.mark_as_answer = False

            if isinstance(ID, User):
                ID = ID.id

        sender = session.bot
        msg = self.msg
        kwargs = self._get_config()

        # Catch a to long message text
        if self.media_type == Media.TEXT and len(msg) > 4096:
            msg, self.media_type, self.media = Bot._on_message_overflow(self)

        # Check for a request for editing
        if self.edit_id is not None:
            return await sender.editMessageText((ID, self.edit_id), msg,
                                                **{key: kwargs[key] for key in kwargs if key in ("parse_mode",
                                                                                                 "disable_web_page_preview",
                                                                                                 "reply_markup")}
                                                )

        # Call the correct method for sending the desired media type and filter the relevant kwargs
        if self.media_type == Media.TEXT:
            return await sender.sendMessage(ID, msg,
                                            **{key: kwargs[key] for key in kwargs if key in ("parse_mode",
                                                                                             "disable_web_page_preview",
                                                                                             "disable_notification",
                                                                                             "reply_to_message_id",
                                                                                             "reply_markup")})

        elif self.media_type == Media.STICKER:
            return await sender.sendSticker(ID, self.media,
                                            **{key: kwargs[key] for key in kwargs if key in ('disable_notification',
                                                                                             'reply_to_message_id',
                                                                                             'reply_markup')})

        elif self.media_type == Media.VOICE:
            return await sender.sendVoice(ID, open(self.media, "rb"),
                                          **{key: kwargs[key] for key in kwargs if key in ("caption",
                                                                                           "parse_mode",
                                                                                           "duration",
                                                                                           "disable_notification",
                                                                                           "reply_to_message_id",
                                                                                           "reply_markup")})

        elif self.media_type == Media.AUDIO:
            return await sender.sendAudio(ID, open(self.media, "rb"),
                                          **{key: kwargs[key] for key in kwargs if key in ("caption",
                                                                                           "parse_mode",
                                                                                           "duration",
                                                                                           "performer",
                                                                                           "title",
                                                                                           "disable_notification",
                                                                                           "reply_to_message_id",
                                                                                           "reply_markup")})

        elif self.media_type == Media.PHOTO:
            return await sender.sendPhoto(ID, open(self.media, "rb"),
                                          **{key: kwargs[key] for key in kwargs if key in ("caption",
                                                                                           "parse_mode",
                                                                                           "disable_notification",
                                                                                           "reply_to_message_id",
                                                                                           "reply_markup")})

        elif self.media_type == Media.VIDEO:
            return await sender.sendVideo(ID, open(self.media, "rb"),
                                          **{key: kwargs[key] for key in kwargs if key in ("duration",
                                                                                           "width",
                                                                                           "height",
                                                                                           "caption",
                                                                                           "parse_mode",
                                                                                           "supports_streaming",
                                                                                           "disable_notification",
                                                                                           "reply_to_message_id",
                                                                                           "reply_markup")})

        elif self.media_type == Media.DOCUMENT:
            return await sender.sendDocument(ID, open(self.media, "rb"),
                                             **{key: kwargs[key] for key in kwargs if key in ("caption",
                                                                                              "parse_mode",
                                                                                              "disable_notification",
                                                                                              "reply_to_message_id",
                                                                                              "reply_markup")})

    def _apply_language(self) -> str:
        """
        Uses the given key and formatting addition to answer the user the appropriate language
        :return The formatted text
        """

        # The language code should be something like de, but could be also like de_DE or non-existent
        usr = _context.get('user')
        lang_code = usr.language_code.split('_')[0].lower() if usr is not None else "en"

        try:
            # Try to load the string with the given language code
            answer: str = _Session.language[lang_code][self._msg]

        except KeyError:

            # Try to load the answer string in the default segment
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

    def is_query(self) -> bool:
        """
        Determines if the answer contains/is a query
        :return: A boolean answering the call
        """

        return self.choices is not None

    @property
    def msg(self) -> str:
        """
        Returns either the message directly or the formatted one
        :return: The final message to be sent
        """

        # Retrieve message
        if self.language_feature:
            msg = self._apply_language()
        else:
            msg = self._msg

        # If unset, determine media type
        if self.media_type is None:

            # Try to detect a relevant command
            command = ""
            if ":" in msg:
                command, payload = msg.split(":", 1)
                if command in ("sticker", "audio", "voice", "document", "photo", "video"):
                    if ";" in payload:
                        self.media, self.caption = payload.split(";", 1)
                    else:
                        self.media = payload

                    msg = None
                    self._msg = msg

            self.media_type = self.media_commands.get(command, Media.TEXT)

        return msg

    def _get_config(self) -> Dict[str, Any]:
        """
        Gets the kwargs for the sending methods.
        :return: kwargs for the sending of the answer
        """

        if self.choices is not None:

            # In the case of 1-dimensional array
            # align the options in pairs of 2
            if isinstance(self.choices[0], (str, tuple)):
                self.choices = [[y for y in self.choices[x * 2:(x + 1) * 2]] for x in
                                range(int(math.ceil(len(self.choices) / 2)))]

            # Prepare button array
            buttons = []

            # Loop over all rows
            for row in self.choices:
                r = []
                # Loop over each entry
                for text in row:
                    # Append the text as a new button
                    if isinstance(text, str):
                        r.append(InlineKeyboardButton(
                            text=text, callback_data=text))
                    else:
                        r.append(InlineKeyboardButton(
                            text=text[0], callback_data=text[1]))

                # Append the button row to the list
                buttons.append(r)

            # Assemble keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        elif self.keyboard is not None:

            # For anything except a collection, any previous sent keyboard is deleted
            if not isinstance(self.keyboard, collections.Iterable):
                keyboard = ReplyKeyboardRemove()

            else:

                # In the case of 1-dimensional array
                # align the options in pairs of 2
                if isinstance(self.keyboard[0], str):
                    self.keyboard = [[y for y in self.keyboard[x * 2:(x + 1) * 2]] for x in
                                     range(int(math.ceil(len(self.keyboard) / 2)))]

                # Prepare button array
                buttons = []

                # Loop over all rows
                for row in self.keyboard:
                    r = []
                    # Loop over each entry
                    for text in row:
                        # Append the text as a new button
                        r.append(KeyboardButton(
                            text=text))
                    # Append the button row to the list
                    buttons.append(r)

                # Assemble keyboard
                keyboard = ReplyKeyboardMarkup(keyboard=buttons, one_time_keyboard=True)
        else:
            keyboard = None

        return {
            'parse_mode': self.markup,
            'reply_to_message_id': _context.get('init_message').id if self.mark_as_answer and _context.get(
                'message') is not None else None,
            'disable_web_page_preview': self.disable_web_preview,
            'disable_notification': self.disable_notification,
            'reply_markup': keyboard,
            'caption': self.caption
        }

    @classmethod
    def _load_defaults(cls) -> None:
        """
        Load default values from config
        """

        cls.mark_as_answer = _config_value('bot', 'mark_as_answer', default=False)
        cls.markup = _config_value('bot', 'markup', default=None)
        cls.language_feature = _config_value('bot', 'language_feature', default=False)
        cls.strict_mode = _config_value('bot', 'strict_mode', default=False)
        cls.disable_web_preview = _config_value('bot', 'disable_web_preview', default=False)
        cls.disable_notification = _config_value('bot', 'disable_notification', default=False)


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
        # Load data from persistent storage
        if _Session.database is not None:

            self.storage = _Session.load_user_data(self.user_id)

        else:
            self.storage = dict()

        self.callback = None
        self.query_callback = {}
        self.query_id = None
        self.last_sent = None
        self.gen = None
        self.gen_is_async = None

        # Prepare dequeue to store sent messages' IDs
        _context.set("history", deque(maxlen=_config_value("bot", "max_history_entries", default=10)))

        logger.info(
            "User {} connected".format(self.user))

    @staticmethod
    def load_user_data(user):
        """

        :param user:
        :return:
        """

        storage = _Session.database.search(Query().user == user)

        if len(storage) == 0:
            _Session.database.insert({"user": user, "storage": {}})
            return dict()
        else:
            return storage[0]["storage"]

    @staticmethod
    def update_user_data(user, storage):
        """

        :param user:
        :param storage:
        :return:
        """

        _Session.database.update({"storage": storage}, Query().user == user)

    def is_allowed(self):
        """
        Tests, if the current session's user is white listed
        :return: If the user is allowed
        """

        ids = _config_value("general", "allowed_ids")

        # If no IDs are defined, the user is allowed
        if ids is None:
            return True
        else:
            return self.user_id in ids

    async def on_close(self, timeout: int) -> None:
        """
        The function which will be called by telepot when the connection times out. Unused.
        :param timeout: The length of the exceeded timeout
        """
        logger.info("User {} timed out".format(self.user))

        pass

    async def on_callback_query(self, query: Dict) -> None:
        """
        The function which will be called by telepot if the incoming message is a callback query
        """

        # Acknowledge the received query
        # (The waiting circle in the user's application will disappear)
        await self.bot.answerCallbackQuery(query['id'])

        # Replace the query to prevent multiple activations
        if _config_value('query', 'replace_query', default=True):
            lastMessage: Answer = self.last_sent[0]
            choices = lastMessage.choices

            # Find the right replacement text
            # This is either directly the received answer or the first element of the choice tuple
            if not isinstance(choices[0][0], tuple) or len(choices[0][0]) == 1:
                replacement = query['data']
            else:
                # Flatten the choices to a list containing the tuples
                choices = flatten(choices)
                replacement = first_true(choices, pred=lambda x: str(x[1]) == query['data'], default=("", ""))[0]

            # Edit the message
            await self.bot.editMessageText((self.user.id, query['message']['message_id']),
                                           # The message and chat ids are inquired in this way to prevent an error when
                                           # the user clicks on old queries
                                           text=("{}\n<b>{}</b>" if lastMessage.markup == "HTML" else "{}\n**{}**")
                                           .format(lastMessage.msg, replacement),
                                           parse_mode=lastMessage.markup)

        # Look for a matching callback and execute it
        answer = None
        func = self.query_callback.pop(query['message']['message_id'], None)
        if func is not None:
            if iscoroutinefunction(func):
                answer = await func(query['data'])
            else:
                answer = func(query['data'])
        elif self.gen is not None:
            await self.handle_generator(msg=query['data'])

        # Process answer
        if answer is not None:
            await self.prepare_answer(answer, log="")

    async def on_chat_message(self, msg: dict) -> None:
        """
        The function which will be called by telepot
        :param msg: The received message as dictionary
        """

        if not self.is_allowed():
            return

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
        _context.set('user', self.user)
        _context.set('message', Message(msg))
        _context.set('_<[storage]>_', self.storage)

        # If there is currently no generator ongoing, save this message additionally as init
        # This may be of use when inside a generator the starting message is needed
        if self.gen is None:
            _context.set("init_message", Message(msg))

        # Calls the preprocessing function
        if not Bot._before_function():
            return

        args: Tuple = ()
        kwargs: Dict = {}

        if text == _config_value('bot', 'cancel_command', default="/cancel"):
            self.gen = None
            self.callback = None

        # If a generator is defined, handle it the message and return if it did not stop
        if self.gen is not None:
            # Call the generator and abort if he worked
            if await self.handle_generator(msg=text):
                return

        # If a callback is defined and the text does not match the defined cancel command,
        # the callback function is called
        if self.callback is not None:
            func = self.callback
            self.callback = None
            args = tuple(text)

        # Check, if the message is covered by one of the known simple routes
        elif text in _Session.simple_routes:
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

        # Catch an error due to lacking authorization
        except AuthorizationError:
            # Get the configuration value
            reply = _config_value('bot', 'authorization_reply', default=None)
            logger.info("User's request was blocked due to insufficient access permissions.")

            # If an answer is configured, an reply is sent, else nothing is returned
            if reply is not None:
                await self.prepare_answer(Answer(_config_value('bot', 'authorization_reply', default=None)))

        # Catch any error
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
        Prepares the returned object to be processed later on
        :param answer: The answer to be given
        :param log: A logging string
        """

        # Syncs persistent storage
        if _Session.database is not None:
            _Session.update_user_data(self.user_id, self.storage)

        try:

            # None as return will result in no answer being sent
            if answer is None:
                logger.info(log + "\n\tNo answer was given")
                return

            # Handle multiple strings or answers as return
            if isinstance(answer, (tuple, list)):
                if isinstance(answer[0], str):
                    await self.handle_answer([Answer(str(answer[0]), *answer[1:])])
                elif isinstance(answer[0], Answer):
                    await self.handle_answer(answer)

            # Handle a generator
            elif isgenerator(answer) or isasyncgen(answer):
                self.gen = answer
                self.gen_is_async = isasyncgen(answer)
                await self.handle_generator(first_call=True)

            # Handle a single answer
            else:
                await self.handle_answer([answer])

        except IndexError:
            err = '\n\tAn index error occured while preparing the answer.' \
                  '\n\tLikely the answer is ill-formatted:\n\t\t{}'.format(str(answer))
            logger.warning(log + err)

            # Send error message, if configured
            await self.handle_error()
            return

        except FileNotFoundError as e:
            err = '\n\tThe request could not be fulfilled as the file "{}" could not be found'.format(e.filename)
            logger.warning(log + err)

            # Send error message, if configured
            await self.handle_error()
            return

        except TelegramError as e:
            reason = e.args[0]

            # Try to give a clearer error description
            if reason == "Bad Request: chat not found":
                reason = "The recipient has either not yet started communication with this bot or blocked it"

            err = '\n\tThe request could not be fulfilled as an API error occured:' \
                  '\n\t\t{}' \
                  '\n\tNothing was returned to the user'.format(reason)
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
                  "\n\tYou may report this bug as it either should not have occured " \
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

        if not self.is_allowed():
            return

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

    async def handle_answer(self, answers: Iterable[Answer]) -> None:
        """
        Handle Answer objects
        :param answers: Answer objects to be sent
        """

        # Iterate over answers
        for answer in answers:
            if not isinstance(answer, Answer):
                answer = Answer(str(answer))

            sent = await answer._send(self)
            self.last_sent = answer, sent
            _context.get("history").appendleft(Message(sent))

            if answer.callback is not None:
                if answer.is_query():
                    self.query_callback[sent['message_id']] = answer.callback
                else:
                    self.callback = answer.callback

    async def handle_generator(self, msg=None, first_call=False):
        """
        Performs one iteration on the generator
        :param msg: The message to be sent into the generator
        :param first_call: If this is the initial call to the generator
        """

        # Wrap the whole process into a try to except the end of iteration exception
        try:

            # On first call, None has to be inserted
            if first_call:
                if self.gen_is_async:
                    answer = await self.gen.asend(None)
                else:
                    answer = self.gen.send(None)

            # On the following calls, the message is inserted
            else:
                if self.gen_is_async:
                    answer = await self.gen.asend(msg)
                else:
                    answer = self.gen.send(msg)

            await self.prepare_answer(answer)

        # Return if the iterator worked properly
        except (StopIteration, StopAsyncIteration):
            self.gen = None
            return False
        else:
            return True

    @staticmethod
    async def default_answer() -> Union[str, Answer, Iterable[str], None]:
        """
        Sets the default answer function to do nothing if not overwritten
        """

    @staticmethod
    async def default_sticker_answer() -> Union[str, Answer, Iterable[str], None]:
        """
        Sets the default sticker answer function to do nothing if not overwritten
        """
