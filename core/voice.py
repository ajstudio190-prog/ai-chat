"""
AizenOS Universal Voice & Speech Engine.
Provides local offline Whisper Speech-To-Text and Neural Text-To-Speech
supporting macOS (CoreAudio/say), Linux (Piper/espeak), and Windows (SAPI/DirectSound).
"""

import subprocess
import shutil
import os
import re
import sys
import select
import time
import signal
import platform

IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = platform.system() == "Windows"

VOICE_NAME = "Samantha" if IS_MAC else ("Microsoft David Desktop" if IS_WINDOWS else "default")
WHISPER_BIN = shutil.which("whisper-cli") or shutil.which("whisper") or ("/opt/homebrew/bin/whisper-cli" if IS_MAC else "whisper")
FFMPEG_BIN = shutil.which("ffmpeg") or ("/opt/homebrew/bin/ffmpeg" if IS_MAC else "ffmpeg")
WHISPER_MODELS_DIR = os.path.expanduser("~/.ai_models/whisper")

def get_whisper_model_path() -> str:
    base_model = os.path.join(WHISPER_MODELS_DIR, "ggml-base.en.bin")
    tiny_model = os.path.join(WHISPER_MODELS_DIR, "ggml-tiny.en.bin")
    if os.path.exists(base_model):
        return base_model
    if os.path.exists(tiny_model):
        return tiny_model
    return ""

def clean_for_speech(text: str) -> str:
    """Strips markdown code blocks, links, and symbols for natural human speech."""
    t = re.sub(r"```[\s\S]*?```", "Here is the code block.", text)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", t)
    t = re.sub(r"[#*_~`>]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:400]

def extract_sentences_for_speech(buffer: str) -> tuple[list[str], str]:
    """Extracts completed sentences from streaming buffer for real-time sub-second TTS."""
    sentences = []
    while True:
        m = re.search(r"^(.*?\S[.!?])(?:\s+|$)", buffer)
        if m:
            s = m.group(1).strip()
            if re.search(r"\b(?:e\.g|i\.e|vs|mr|ms|dr)\.$", s, re.I):
                break
            if len(s) > 2:
                sentences.append(s)
            buffer = buffer[m.end():].lstrip()
        else:
            break
    return sentences, buffer

def speak_text(text: str, voice: str = VOICE_NAME, wait: bool = False):
    """Speaks text aloud via macOS say, Linux Piper/espeak, or Windows SAPI engine."""
    clean = clean_for_speech(text)
    if not clean:
        return

    try:
        if IS_MAC:
            cmd = ["say", "-v", voice, clean]
            if wait:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif IS_LINUX:
            piper_bin = shutil.which("piper")
            if piper_bin:
                pipe = subprocess.Popen([piper_bin, "--output_raw"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                aplay = subprocess.Popen(["aplay", "-r", "22050", "-f", "S16_LE"], stdin=pipe.stdout)
                pipe.stdin.write(clean.encode())
                pipe.stdin.close()
                if wait:
                    aplay.wait()
            else:
                spd_bin = shutil.which("spd-say") or shutil.which("espeak")
                if spd_bin:
                    subprocess.run([spd_bin, clean], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif IS_WINDOWS:
            escaped = clean.replace("'", "''")
            ps_cmd = f"Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Speak('{escaped}')"
            cmd = ["powershell", "-NoProfile", "-Command", ps_cmd]
            if wait:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def transcribe_audio_file(audio_path: str) -> str:
    """Transcribes a WAV file using local whisper-cli."""
    if not os.path.isfile(audio_path) or os.path.getsize(audio_path) < 1000:
        return ""

    model_path = get_whisper_model_path()
    if not model_path or not os.path.exists(WHISPER_BIN):
        return ""

    try:
        cmd = [
            WHISPER_BIN,
            "-m", model_path,
            "-f", audio_path,
            "-t", "4",
            "-nt",
            "--no-timestamps"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        raw = res.stdout.strip()
        clean = re.sub(r"\[.*?\]", "", raw)
        clean = re.sub(r"\(.*?\)", "", clean)
        clean = clean.strip()
        if clean.upper() in ("BLANK_AUDIO", ""):
            return ""
        return clean
    except Exception:
        return ""

def listen_for_voice(max_seconds: int = 8) -> str:
    """Captures live audio from microphone and transcribes it locally via Whisper."""
    if not os.path.exists(FFMPEG_BIN):
        return ""

    temp_dir = os.environ.get("TEMP") or "/tmp"
    audio_file = os.path.join(temp_dir, "ai_voice_input.wav")
    
    if IS_MAC:
        input_format = "avfoundation"
        input_dev = ":0"
    elif IS_LINUX:
        input_format = "pulse"
        input_dev = "default"
    elif IS_WINDOWS:
        input_format = "dshow"
        input_dev = "audio=Microphone"
    else:
        return ""

    rec_cmd = [
        FFMPEG_BIN,
        "-y",
        "-loglevel", "quiet",
        "-f", input_format,
        "-i", input_dev,
        "-t", str(max_seconds),
        "-ar", "16000",
        "-ac", "1",
        audio_file
    ]

    try:
        proc = subprocess.Popen(rec_cmd)
        start_time = time.time()

        while proc.poll() is None:
            if not IS_WINDOWS:
                rlist, _, _ = select.select([sys.stdin], [], [], 0.15)
                if rlist:
                    sys.stdin.readline()
                    break
            else:
                time.sleep(0.15)
            if time.time() - start_time >= max_seconds:
                break

        if proc.poll() is None:
            if not IS_WINDOWS:
                proc.send_signal(signal.SIGINT)
            else:
                proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    except Exception:
        return ""

    return transcribe_audio_file(audio_file)
