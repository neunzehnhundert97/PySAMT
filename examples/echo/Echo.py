from marvin import Marvin, context

bot = Marvin()

@bot.default_answer
def echo():
    return context.get('message').text
    
if __name__ == "__main__":
    bot.listen()