#!/usr/bin/env python3
"""
Murdock Dunkin — Voice Wakeword Trigger
Listens to mic for "moinsen" / "moin moin" / "moin" via Vosk (offline, deutsch).
On trigger: runs scripts/launch-session.ps1 then exits.
"""

import json
import os
import queue
import subprocess
import sys

import sounddevice as sd
import vosk

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

WORKSPACE_PATH = config["workspace_path"]
SCRIPT_PATH = os.path.join(WORKSPACE_PATH, "scripts", "launch-session.ps1")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "vosk-model-small-de-0.15")

WAKEWORDS = ("moinsen", "moin moin", "moin")
SAMPLE_RATE = 16000
BLOCK_SIZE = 8000

if not os.path.isdir(MODEL_PATH):
    print(f"[murdock] Vosk-Modell fehlt: {MODEL_PATH}", flush=True)
    sys.exit(1)

vosk.SetLogLevel(-1)
model = vosk.Model(MODEL_PATH)
recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)
audio_q: "queue.Queue[bytes]" = queue.Queue()


def audio_callback(indata, frames, time_info, status):
    audio_q.put(bytes(indata))


def matches_wakeword(text: str) -> bool:
    t = text.lower().strip()
    if not t:
        return False
    return any(w in t for w in WAKEWORDS)


def fire_and_exit(text: str):
    print(f"[murdock] Wakeword erkannt: '{text}'. Starte Session, beende Listener.", flush=True)
    subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", SCRIPT_PATH])
    sys.exit(0)


print("[murdock] Lausche auf Wakeword (moinsen / moin moin / moin) ...", flush=True)

with sd.RawInputStream(
    samplerate=SAMPLE_RATE,
    blocksize=BLOCK_SIZE,
    dtype="int16",
    channels=1,
    callback=audio_callback,
):
    while True:
        data = audio_q.get()
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "")
            if matches_wakeword(text):
                fire_and_exit(text)
        else:
            partial = json.loads(recognizer.PartialResult())
            text = partial.get("partial", "")
            if matches_wakeword(text):
                fire_and_exit(text)
