import subprocess

def play_spotify(command):
    song = command.replace("play spotify", "").strip()
    subprocess.Popen(["spotify", "--uri", f"spotify:search:{song}"])
    return f"Playing {song} on Spotify Boss."