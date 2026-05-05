from utils.internet import search_google
from automation.app_control import open_app
from utils.music import play_song
from brain.chat_engine import ask_ai


def auto_task(command):

    command = command.lower()

    # open apps
    if "open" in command:
        open_app(command)
        return "Opening application Boss"

    # play music
    elif "play" in command:
        play_song(command)
        return "Playing music Boss"

    # search
    elif "search" in command or "find" in command:
        search_google(command)
        return "Searching on Google Boss"

    # otherwise AI answer
    else:
        answer = ask_ai(command)
        return answer