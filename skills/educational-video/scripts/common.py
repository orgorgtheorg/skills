"""Shared helpers. Every script runs from the project dir (/workspace/video/<slug>)."""
import json, os, subprocess, wave

PROJECT = os.getcwd()
AUDIO_DIR = os.path.join(PROJECT, "audio")
RENDER_DIR = os.path.join(PROJECT, "rendered")
OUT_DIR = os.path.join(PROJECT, "output")


def ffmpeg_exe():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def duration(path):
    """Seconds of media. WAV via the stdlib, anything else via pyav (ships with manim)."""
    if path.endswith(".wav"):
        with wave.open(path, "rb") as w:
            return w.getnframes() / w.getframerate()
    import av
    with av.open(path) as c:
        return float(c.duration) / av.time_base


def load_sections():
    """script.py in the project dir defines SECTIONS = [(id, narration), ...]."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("script", os.path.join(PROJECT, "script.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SECTIONS


def scene_name(section_id):
    """s01_hook -> S01Hook"""
    return "".join(p.capitalize() for p in section_id.split("_"))


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)
