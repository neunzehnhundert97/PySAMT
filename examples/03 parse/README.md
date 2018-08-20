# Complex matching, accessing additional information

This bot is capable of matching incoming messages using regular expressions, the _parse_-module and extracting values in this way to be used as parameters.

## Explanation

The `answer`-decorator has a optional keyword argument mode, which may be `Mode.REGEX` or `Mode.PARSE` (the default value is `Mode.TEXT`). By using this, the given string will not be compared directly but using the given method.

If you are not very experienced with regular expressions, you should favor the `parse`-Mode. It uses the module [parse](https://github.com/r1chardj0n3s/parse) to circumvent regular expressions. This module allows matching with format-string-like expressions.

If matching groups have a specified name, they will be given to the function as same named parameters.
