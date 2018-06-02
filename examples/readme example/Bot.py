from marvin import Marvin

bot = Marvin()

@bot.answer("/start")
def start():
    return "Hello, new user, how can I help you?"
    
if __name__ == "__main__":
    bot.listen()