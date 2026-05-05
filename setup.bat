@echo off
title CRACKA AI v3.0 - Setup
color 0B
cls

echo.
echo  ============================================================
echo   @@@@@@  @@@@@@ @@@@@   @@@@  @@@  @@ @@@@@   @@@@  @@@
echo  @@      @@  @@ @@  @@ @@  @@ @@@@ @@ @@  @@ @@  @@ @@@
echo  @@      @@@@@@ @@@@@  @@@@@@ @@ @@@@  @@@@@  @@@@@@ @@
echo  @@      @@  @@ @@  @@ @@  @@ @@  @@@  @@  @@ @@  @@
echo   @@@@@@  @@  @@ @@  @@ @@  @@ @@   @@ @@   @@ @@  @@ @@
echo.
echo            AI Assistant v3.0 - Windows Setup
echo  ============================================================
echo.

:: ── Admin check ──────────────────────────────────────────────────────────────
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo  [!] Please run this file as Administrator!
    echo  [!] Right-click setup.bat and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo  [*] Running as Administrator - Good!
echo.

:: ── Python check ─────────────────────────────────────────────────────────────
echo  [1/8] Checking Python installation...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo  [!] Python not found!
    echo  [*] Opening Python download page...
    start https://www.python.org/downloads/
    echo  [*] Install Python 3.10 or above.
    echo  [*] IMPORTANT: Check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  [OK] Python %PYVER% found!
echo.

:: ── pip upgrade ──────────────────────────────────────────────────────────────
echo  [2/8] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo  [OK] pip upgraded!
echo.

:: ── Project folder structure ─────────────────────────────────────────────────
echo  [3/8] Creating project folder structure...

if not exist "data"          mkdir data
if not exist "data\logs"     mkdir data\logs
if not exist "data\screenshots" mkdir data\screenshots
if not exist "models"        mkdir models

echo  [OK] Folders created!
echo.

:: ── Core libraries install ───────────────────────────────────────────────────
echo  [4/8] Installing core libraries...
echo  [*] This may take 5-10 minutes. Please wait...
echo.

pip install SpeechRecognition==3.10.4 --quiet
echo  [OK] SpeechRecognition

pip install pyttsx3==2.90 --quiet
echo  [OK] pyttsx3

pip install gTTS==2.5.1 --quiet
echo  [OK] gTTS

pip install pygame==2.5.2 --quiet
echo  [OK] pygame

pip install playsound==1.2.2 --quiet
echo  [OK] playsound

pip install TextBlob==0.18.0 --quiet
echo  [OK] TextBlob

pip install requests==2.31.0 --quiet
echo  [OK] requests

pip install PyAutoGUI==0.9.54 --quiet
echo  [OK] PyAutoGUI

pip install pyperclip==1.8.2 --quiet
echo  [OK] pyperclip

pip install mss==9.0.1 --quiet
echo  [OK] mss

pip install Pillow==10.3.0 --quiet
echo  [OK] Pillow

pip install psutil==5.9.8 --quiet
echo  [OK] psutil

pip install pywhatkit==5.4 --quiet
echo  [OK] pywhatkit

pip install deep-translator==1.11.4 --quiet
echo  [OK] deep-translator

pip install python-dotenv==1.0.1 --quiet
echo  [OK] python-dotenv

pip install customtkinter==5.2.2 --quiet
echo  [OK] customtkinter

pip install rich==14.3.3 --quiet
echo  [OK] rich

pip install schedule==1.2.2 --quiet
echo  [OK] schedule

pip install ollama==0.6.1 --quiet
echo  [OK] ollama (Python client)

pip install groq==1.2.0 --quiet
echo  [OK] groq

echo.
echo  [OK] Core libraries installed!
echo.

:: ── PyAudio (tricky on Windows) ───────────────────────────────────────────────
echo  [5/8] Installing PyAudio (microphone support)...

pip install PyAudio==0.2.14 --quiet 2>nul
if %errorLevel% neq 0 (
    echo  [*] Direct install failed. Trying pipwin method...
    pip install pipwin --quiet
    pipwin install pyaudio --quiet 2>nul
    if %errorLevel% neq 0 (
        echo  [!] PyAudio install failed via pipwin too.
        echo  [*] Manual install karo:
        echo      1. https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
        echo      2. Apne Python version ka .whl file download karo
        echo      3. pip install downloaded_file.whl
        echo  [*] Skipping PyAudio for now...
    ) else (
        echo  [OK] PyAudio installed via pipwin!
    )
) else (
    echo  [OK] PyAudio installed!
)
echo.

:: ── Google APIs ───────────────────────────────────────────────────────────────
echo  [6/8] Installing Google APIs (Gmail + Calendar)...

pip install google-api-python-client==2.127.0 --quiet
echo  [OK] google-api-python-client

pip install google-auth==2.29.0 --quiet
echo  [OK] google-auth

pip install google-auth-oauthlib==1.2.0 --quiet
echo  [OK] google-auth-oauthlib

pip install google-auth-httplib2==0.2.0 --quiet
echo  [OK] google-auth-httplib2

echo.

:: ── Browser automation ────────────────────────────────────────────────────────
echo  [7/8] Installing browser automation (Form Filler)...

pip install selenium==4.20.0 --quiet
echo  [OK] selenium

pip install webdriver-manager==4.0.1 --quiet
echo  [OK] webdriver-manager

echo.

:: ── TextBlob data download ────────────────────────────────────────────────────
echo  [*] Downloading TextBlob language data...
python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('averaged_perceptron_tagger', quiet=True)" 2>nul
echo  [OK] TextBlob data ready!
echo.

:: ── Ollama check & model download ────────────────────────────────────────────
echo  [8/8] Checking Ollama (AI Brain)...
ollama --version >nul 2>&1
if %errorLevel% neq 0 (
    echo  [!] Ollama not installed!
    echo  [*] Opening Ollama download page...
    start https://ollama.com/download
    echo.
    echo  [*] Steps:
    echo      1. Download aur install karo Ollama
    echo      2. Phir yeh command run karo:
    echo         ollama pull phi3
    echo.
    echo  [*] Ollama install ke baad Cracka chalao.
) else (
    echo  [OK] Ollama found!
    echo  [*] Downloading phi3 AI model (1-2 GB)...
    echo  [*] Yeh thoda time lega - please wait...
    ollama pull phi3
    if %errorLevel% neq 0 (
        echo  [!] phi3 download failed. Internet check karo.
        echo  [*] Manually run karo: ollama pull phi3
    ) else (
        echo  [OK] phi3 model ready!
    )
)
echo.

:: ── Create default config if not exists ──────────────────────────────────────
echo  [*] Setting up config files...

if not exist "data\config.json" (
    echo  [*] Creating default config.json...
    (
        echo {
        echo   "_readme": "Cracka AI v3.0 Config - Apni API keys yahan daalo",
        echo   "assistant": {
        echo     "name": "Cracka",
        echo     "boss_name": "Boss",
        echo     "wake_words": ["cracka", "hey cracka", "jarvis"],
        echo     "language": "en-IN",
        echo     "voice_speed": 160,
        echo     "default_city": "Pune",
        echo     "hinglish_mode": true
        echo   },
        echo   "ai_model": {
        echo     "primary": "ollama",
        echo     "ollama_model": "phi3",
        echo     "ollama_url": "http://127.0.0.1:11434",
        echo     "groq_api_key": "GROQ_KEY_YAHAN_DAALO",
        echo     "temperature": 0.4,
        echo     "max_tokens": 300
        echo   },
        echo   "apis": {
        echo     "openweather_key": "OPENWEATHER_KEY_YAHAN_DAALO",
        echo     "newsapi_key": "NEWSAPI_KEY_YAHAN_DAALO"
        echo   },
        echo   "features": {
        echo     "voice_enabled": true,
        echo     "wake_word_enabled": true,
        echo     "gmail_enabled": false,
        echo     "calendar_enabled": false,
        echo     "network_monitor": false,
        echo     "face_recognition": false,
        echo     "offline_voice": false,
        echo     "form_filler": true,
        echo     "code_reviewer": true,
        echo     "mobile_control_adb": false
        echo   }
        echo }
    ) > data\config.json
    echo  [OK] config.json created!
) else (
    echo  [OK] config.json already exists - skipping
)
echo.

:: ── Create launch shortcuts ───────────────────────────────────────────────────
echo  [*] Creating launch files...

:: start_cracka.bat
(
    echo @echo off
    echo title CRACKA AI
    echo color 0B
    echo cls
    echo echo.
    echo echo  Starting CRACKA AI v3.0...
    echo echo.
    echo python main.py
    echo pause
) > start_cracka.bat
echo  [OK] start_cracka.bat created!

:: cracka_voice_only.bat (bina GUI ke)
(
    echo @echo off
    echo title CRACKA AI - Voice Mode
    echo color 0A
    echo python -c "from core.listener import listen; from core.ai_brain import process; from core.voice_engine import speak; speak('Cracka ready'); [speak(process(c)) for c in iter(listen, None)]"
    echo pause
) > cracka_voice_only.bat
echo  [OK] cracka_voice_only.bat created!

echo.

:: ── Final summary ─────────────────────────────────────────────────────────────
cls
color 0A
echo.
echo  ============================================================
echo.
echo         CRACKA AI v3.0 - SETUP COMPLETE!
echo.
echo  ============================================================
echo.
echo  [OK] Python - Ready
echo  [OK] Core libraries - Installed
echo  [OK] PyAudio - Ready
echo  [OK] Google APIs - Installed
echo  [OK] Selenium - Installed
echo  [OK] Config files - Created
echo  [OK] Launch files - Created
echo.
echo  ============================================================
echo  NEXT STEPS:
echo  ============================================================
echo.
echo  1. data\config.json kholo aur apna naam daalo:
echo     "boss_name": "Aditi Patil"
echo.
echo  2. API keys daalo (optional):
echo     - OpenWeather: openweathermap.org (free)
echo     - Groq: console.groq.com (free, fast AI)
echo.
echo  3. Cracka start karo:
echo     Double-click: start_cracka.bat
echo     Ya terminal mein: python main.py
echo.
echo  4. "Cracka" ya "Jarvis" bolke activate karo!
echo.
echo  ============================================================
echo.
echo  Press any key to launch Cracka now...
pause >nul

:: Launch Cracka