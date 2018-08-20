# Hello bot

This bot greets a user first messaging it with the */start* message and two other greetings and ignore everything else it receives.

## Explanation

The ``bot.answer`` decorator issues the framework to call this method when receiving the message specified as its parameter. This is usually tested by simple ``message == pattern``, but you may also use a regular expression. Also, you may use unlimited many different pattern on the same function.
