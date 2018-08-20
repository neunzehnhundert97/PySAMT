from marvin import Marvin, Context, Mode

bot = Marvin()


@bot.default_answer
def default():
    return "'{}'\ncould not be processed".format(Context.get('message'))


@bot.answer("[Hh][ae]llo", mode=Mode.REGEX)
def greet():
    return f"Greetings, {Context.get('user')}, how are you doing?"


@bot.answer("(?P<first>\d+)\.(?P<second>\d+)\.(?P<third>\d+)\.(?P<fourth>\d+)", mode=Mode.REGEX)
def ip(first, second, third, fourth):
    if 0 <= int(first) <= 255 and 0 <= int(second) <= 255 and 0 <= int(third) <= 255 and 0 <= int(fourth) <= 255:
        return "First block: {}\nSecond block: {}\nThird block: {}\nFourth block: {}".format(first, second, third,
                                                                                             fourth)
    else:
        return "This is illegal"


@bot.answer("{a:d}*{b:d}", mode=Mode.PARSE)
@bot.answer("{a:d}x{b:d}", mode=Mode.PARSE)
def multiply(a, b):
    return F'{a} times {b} equals {a*b}'


if __name__ == "__main__":
    bot.listen()
