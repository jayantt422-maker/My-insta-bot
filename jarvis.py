#!/usr/bin/env python3
# JARVIS AI - Termux Android assistant
# Works with Termux + the separate Termux:API Android app.

import json
import re
import shutil
import subprocess
import urllib.parse
import webbrowser
from datetime import datetime

NAME = "JARVIS"

# Correct Android package IDs. If an app is missing, JARVIS opens its website.
APPS = {
    "youtube": ("com.google.android.youtube", "https://www.youtube.com"),
    "instagram": ("com.instagram.android", "https://www.instagram.com"),
    "whatsapp": ("com.whatsapp", "https://web.whatsapp.com"),
    "whatsapp business": ("com.whatsapp.w4b", "https://www.whatsapp.com/business/"),
    "facebook": ("com.facebook.katana", "https://www.facebook.com"),
    "messenger": ("com.facebook.orca", "https://www.messenger.com"),
    "chrome": ("com.android.chrome", "https://www.google.com/chrome/"),
    "telegram": ("org.telegram.messenger", "https://web.telegram.org"),
    "google": ("com.google.android.googlequicksearchbox", "https://www.google.com"),
    "gmail": ("com.google.android.gm", "https://mail.google.com"),
    "maps": ("com.google.android.apps.maps", "https://maps.google.com"),
    "play store": ("com.android.vending", "https://play.google.com/store"),
    "settings": ("com.android.settings", None),
    "calculator": ("com.google.android.calculator", None),
    "photos": ("com.google.android.apps.photos", "https://photos.google.com"),
}

def run_cmd(args, timeout=12):
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

def speak(message):
    print(f"\n{NAME}: {message}")
    # Termux:API's termux-tts-speak command
    if shutil.which("termux-tts-speak"):
        run_cmd(["termux-tts-speak", message], timeout=20)

def open_url(url):
    # Android opens the URL in the user's default browser/app.
    if shutil.which("termux-open-url"):
        result = run_cmd(["termux-open-url", url])
        if result is not None and result.returncode == 0:
            return True
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False

def open_app(app_name):
    key = app_name.strip().lower()
    if key not in APPS:
        speak(f"{app_name} is not in my app list.")
        return

    package, fallback_url = APPS[key]
    # Use Android's launcher intent rather than `monkey`.
    result = run_cmd([
        "am", "start", "-a", "android.intent.action.MAIN",
        "-c", "android.intent.category.LAUNCHER", "-p", package
    ])

    if result is not None and result.returncode == 0:
        speak(f"Opening {key}.")
    elif fallback_url:
        speak(f"{key} app was not found. Opening its website.")
        open_url(fallback_url)
    else:
        speak(f"Could not open {key}. Check whether it is installed.")

def battery_status():
    result = run_cmd(["termux-battery-status"])
    if result is None or result.returncode != 0:
        speak("Battery status unavailable. Install and allow the Termux API app.")
        return
    try:
        data = json.loads(result.stdout)
        percent = data.get("percentage", "unknown")
        status = str(data.get("status", "unknown")).lower()
        plugged = str(data.get("plugged", "unknown")).lower()
        charging = ("charging" in status or
                    plugged not in ("unplugged", "unknown", "none"))
        speak(f"Battery is {percent} percent. " +
              ("The phone is charging." if charging else "The phone is not charging."))
    except (ValueError, TypeError):
        speak("I could not read the battery information.")

def tell_time():
    speak("The time is " + datetime.now().strftime("%I:%M %p"))

def youtube_search(query):
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    speak("Searching YouTube for " + query)
    open_url(url)

def instagram_account(username):
    username = username.strip().lstrip("@").replace(" ", "")
    if not username:
        speak("Please say the Instagram username.")
        return
    speak("Opening Instagram account " + username)
    open_url("https://www.instagram.com/" + urllib.parse.quote(username) + "/")

def whatsapp_chat(number):
    # Enter a full international number, e.g. 919876543210.
    digits = re.sub(r"\D", "", number)
    if not digits:
        speak("Please provide the phone number with country code.")
        return
    speak("Opening WhatsApp chat. Confirm the contact in WhatsApp.")
    open_url("https://wa.me/" + digits)

def listen():
    if not shutil.which("termux-speech-to-text"):
        speak("Voice recognition is unavailable. Install Termux API and grant microphone permission.")
        return ""
    result = run_cmd(["termux-speech-to-text"], timeout=45)
    if result is None or result.returncode != 0:
        speak("I could not hear that. Please try again.")
        return ""
    return result.stdout.strip()

def handle(command):
    text = command.strip()
    low = text.lower()

    if not text:
        return

    if low in ("exit", "quit", "band ho jao", "close jarvis"):
        raise SystemExit

    if "help" in low or "madad" in low:
        speak("Say open app name, YouTube search topic, Instagram account username, "
              "WhatsApp chat phone number, battery status, or time.")
        return

    if "battery" in low or "charge" in low:
        battery_status()
        return

    if "time" in low or "samay" in low or "kitna baja" in low:
        tell_time()
        return

    match = re.search(r"(?:youtube|you tube)\s+search\s+(.+)", text, re.I)
    if match:
        youtube_search(match.group(1))
        return
    match = re.search(r"(?:search)\s+youtube\s+(.+)", text, re.I)
    if match:
        youtube_search(match.group(1))
        return

    match = re.search(r"instagram\s+(?:account|profile)\s+(.+)", text, re.I)
    if match:
        instagram_account(match.group(1))
        return

    match = re.search(r"whatsapp\s+(?:chat|message)\s+(.+)", text, re.I)
    if match:
        whatsapp_chat(match.group(1))
        return

    match = re.search(r"(?:open|kholo)\s+(.+)", text, re.I)
    if match:
        app = match.group(1).strip().lower()
        if app in APPS:
            open_app(app)
        else:
            speak(f"{app} is not listed. Add its package name in the APPS dictionary.")
        return

    if low.startswith("search "):
        query = text[7:].strip()
        speak("Searching the web for " + query)
        open_url("https://www.google.com/search?q=" + urllib.parse.quote_plus(query))
        return

    speak("Command not recognized. Say Jarvis help.")

def main():
    speak("Hello. Jarvis is ready.")
    while True:
        print("\n========== JARVIS AI ==========")
        print("[1] Voice command")
        print("[2] Type command")
        print("[3] Exit")
        choice = input("Select: ").strip()

        try:
            if choice == "1":
                speak("Listening. Speak now.")
                command = listen()
                print("YOU:", command)
                handle(command)
            elif choice == "2":
                command = input("YOU: ")
                handle(command)
            elif choice == "3":
                speak("Goodbye.")
                break
            else:
                speak("Please select 1, 2, or 3.")
        except SystemExit:
            speak("Goodbye.")
            break
        except KeyboardInterrupt:
            print("\n")
            speak("Jarvis stopped.")
            break

if __name__ == "__main__":
    main()
