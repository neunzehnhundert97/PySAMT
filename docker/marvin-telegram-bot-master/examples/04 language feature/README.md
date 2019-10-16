# Sending media files

This bot uses format strings given in a separate file to answer messages. German users will receive their answers in german, others the english default. Also, the bot uses message styling with HTML.

## Explanation

In the bot's configuration file, the language feature and markup using HTML are activated. A returned string or the first item of sequence will be tried to match against the given keys in the language file. If a segment matching the users language code is available, the bot will prefer the keys their. The found string will then be formatted using the string format function with the remaining items of the sequence as arguments, if any.

Should there be no key, the message is returned directly as normal. If this is not intended, the strict mode can be activated by adding the line `strict_mode = true` to the configuration. This will throw an error if the key could not be found.

This feature may give you two major advantages:

* Making the answer editable without modifying the bot's source, possibly by people not able to understand the bot or python in general.
* Easy support of multiple languages. I am not sure, how Telegram determines the language code, but I suppose it is based on the mobile numbers.

In order to style your messages, you can choose between [HTML](https://core.telegram.org/bots/api#html-style) und [Markdown](https://core.telegram.org/bots/api#markdown-style) syntax.
