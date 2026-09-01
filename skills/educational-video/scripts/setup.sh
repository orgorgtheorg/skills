#!/usr/bin/env bash
# One-time, idempotent setup for the video pipeline on the agent's computer.
# CPU only, pip only, no sudo, no apt. Safe to re-run.
set -euo pipefail

VOICE="${VOICE:-en_US-lessac-medium}"
VOICE_DIR="${VOICE_DIR:-$HOME/.local/share/piper-voices}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

echo "== python packages"
pip3 install --quiet --break-system-packages --upgrade \
  "manim>=0.19" "piper-tts>=1.2.0" "imageio-ffmpeg>=0.5" numpy

echo "== ffmpeg on PATH (static build shipped by imageio-ffmpeg)"
mkdir -p "$BIN_DIR"
FF="$(python3 -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')"
ln -sf "$FF" "$BIN_DIR/ffmpeg"
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) export PATH="$BIN_DIR:$PATH"; echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$HOME/.bashrc";; esac

if ffmpeg -hide_banner -filters 2>/dev/null | grep -q '^ ... ass '; then
  echo "captions: ass filter available (burn-in on)"
else
  echo "captions: NO ass filter in this ffmpeg build — compose.py will write .srt sidecars instead"
fi

echo "== piper voice: $VOICE"
mkdir -p "$VOICE_DIR"
# en_US-lessac-medium -> en/en_US/lessac/medium
LANG_SHORT="${VOICE%%_*}"                 # en
LOCALE="${VOICE%%-*}"                     # en_US
REST="${VOICE#*-}"                        # lessac-medium
NAME="${REST%-*}"                         # lessac
QUALITY="${REST##*-}"                     # medium
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/$LANG_SHORT/$LOCALE/$NAME/$QUALITY"
for f in "$VOICE.onnx" "$VOICE.onnx.json"; do
  if [ ! -s "$VOICE_DIR/$f" ]; then
    curl -fsSL "$BASE/$f" -o "$VOICE_DIR/$f"
  fi
done

echo "== smoke test"
python3 - <<'PY'
import manim, importlib
print("manim", manim.__version__)
try:
    from piper import PiperVoice  # >=1.3
except ImportError:
    from piper.voice import PiperVoice  # 1.2
print("piper ok")
PY
echo "setup done: voice=$VOICE_DIR/$VOICE.onnx  ffmpeg=$FF"
