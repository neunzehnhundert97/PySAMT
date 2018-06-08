# Echobot

As hinted by its name, this bot will echo any message directed to it. Stickers, documents and so on will be silently ignored.

## Explaination

In the first step, the framework is initialized and bound to a local variable. After defining the endpoint, the framework is issued to start the listening process. If you now *flask*, this should be quite familiar.

By using the ``bot.default_answer`` decorator (which can be, by the way, also be called in a static way), the framework is being told to call the following function whenever it cannot find a better way to handle an incoming message. As there is not other option defined, this will always be the case.

In the simplest way of using the framework, the functions return value will directly be sent back to the user, a value of ``None`` would tell the bot to do nothing.

Via ``Context`` you can access additional information about the request instead of using parameters. in this way, a function which does not need the addition information will not be cluttered with unused parameters. The ``Context`` is accessed by the ``get``function in the way you would use a dictionary. By using the key *message* you get a ``Message`` instance, which allows you to access the message's original text and its date of arrival.