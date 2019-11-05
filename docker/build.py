from pathlib import Path
from os import chdir, system
from shutil import copyfile

config_template = """[general]
# Sets the log level for stdout
logging = "DEBUG"

[bot]
# The Bot API token
token = "{}"

"""

bot_template = """from marvin import Marvin, Context

bot = Marvin()


@bot.default_answer
def echo():
    return Context.get('message').text


if __name__ == "__main__":
    bot.listen()

"""

lang_template = """[default]
echo = "I received \"{}\""
error = "An error occured."

"""

run_template = """docker run --rm -d {}
"""

def main():
    print("Welcome to the automatic docker build script.")
    print("To begin with, how many help by this script do you want to have?")
    print()
    print("[1] Help me with as much as possible")
    print("[2] Next to nothing")
    mode = input("Choice [1]: ") or "1"
    print()

    if mode not in ("1", "2"):
        print("An unsupported option was chosen.")
        return
        
    print("Please enter your bot's name.")
    print("This will only be used to create the container.")
    name = (input("Name [marvin-bot]: ") or "marvin-bot").lower()
    print()
    
    print("Please choose a destination for the bot's files.")
    folder = input(f"Folder [{(Path(__file__).parent / name).resolve()}]:")
    print()
        
    print("Please enter your bot's api key.")
    print("If you have no api key, please contact the botfather.")
    while True:
        key = input("Key: ")
        print()
        
        if len(key) == 45 and ":" in key:
            break
            
    if mode == "2":
        create(Path(folder), name, key)
    else:
        pass
        

def create(folder: Path, name: str, api_key: str):
    # Create the folder
    folder.mkdir(exist_ok=True)
    
    # Create the bot's file
    bot_file = folder / "Bot.py"
    bot_file.touch()
    
    with open(bot_file, "w") as f:
        f.write(bot_template)
        
    # Create the bot's file
    run_file = folder / "run.bat"
    run_file.touch()
    
    with open(run_file, "w") as f:
        f.write(run_template.format(name))
        
    # Create the configuration files
    config = folder / "config"
    config.mkdir(exist_ok=True)
    
    # config.toml
    config_file = config / "config.toml"
    config_file.touch()
    
    with open(config_file, "w") as f:
        f.write(config_template.format(api_key))
        
    # lang.toml
    lang_file = config / "lang.toml"
    lang_file.touch()
    
    with open(lang_file, "w") as f:
        f.write(lang_template)
        
    docker_file = Path(__file__).parent / "Dockerfile"
    docker_dest = folder / "Dockerfile"
    
    if docker_file.resolve() != docker_dest.resolve():
        copyfile(docker_file, docker_dest)
        
    # Go into the create directory
    chdir(folder)
    
    system(f"docker build . -t \"{name}\"")

if __name__ == "__main__":
    main()
