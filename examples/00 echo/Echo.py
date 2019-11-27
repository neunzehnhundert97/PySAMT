from samt import Bot, Context

bot = Bot()


@bot.default_answer
def echo():
    return Context.get('message').text


if __name__ == "__main__":
    bot.listen()
