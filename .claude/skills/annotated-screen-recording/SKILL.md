---
name: annotated-screen-recording
description: Record and annotate a screen recording for other people to watch - App Review, Google OAuth verification, a customer, a teammate, a bug report. Use whenever a recording of an iOS simulator, an Android emulator, or a web page leaves this machine. Adds a caption for every step, a marker on every tap, and cuts the waits. Not for a recording you only watch yourself.
---

# Annotated screen recording

Wayne's standard, set 2026-09-15: **a recording that another person watches carries
captions and visible tap targets, and it has no dead time.** A raw capture jumps
between screens with no sign of what was pressed, and it makes the viewer wait
through every pause an automated walk leaves behind.

This applies to web, Android, and iOS. It does not apply to a clip you record to
check your own work.

## The standard

1. **A caption for each step**, in a band under the frame, never over the UI. Name
   the control: "Tap: Delete My Account", not "deleting".
2. **A marker on every tap**, on the control, at the moment of the tap.
3. **No dead time.** Keep the seconds around each action, cut the waits.
4. **Real time inside each kept window.** Never speed the video up: a reviewer
   reads a sped-up flow as something to look at twice.
5. **Show the outcome.** End on the screen that proves the result, held long
   enough to read.

## 1. Record

**iOS simulator.** `xcrun simctl io <udid> recordVideo --codec=h264 --force out.mp4`
- Start the recorder, then confirm `Recording started` in its log, then launch the app.
  A recorder that is still writing a previous file silently drops the first seconds,
  and a second recorder fails with `Host recording is already in progress`.
- The recording captures the device framebuffer only. `ShowSingleTouches` draws
  nothing in it, and Xcode 27's Device Hub has no touch overlay. Hence the markers
  in step 3.
- Xcode 27 renamed Simulator.app to **Device Hub**
  (`/Applications/Xcode.app/Contents/Applications/DeviceHub.app`). Typing needs
  **Device > Keyboard > Keyboard Capture**, and even then iOS drops repeated keys
  and opens the accent picker. Tap the on-screen keyboard instead: it is reliable.
- After any shell command, the terminal takes focus. Click the Device Hub toolbar
  once to raise the window before the next tap.

**Android emulator.** `adb shell screenrecord --bit-rate 8000000 /sdcard/out.mp4`,
then `adb pull`. Android does show taps: Developer options > **Show taps**. Turn it
on and you can skip the markers, but keep the captions.

**Web.** Record the window with `screencapture -v -R x,y,w,h out.mov`, or drive the
page with Playwright and `page.video`. The cursor is visible, so markers are
optional; captions are not.

## 2. Find the times

Every time in the spec is a time in the source video.

```bash
# When the screen changed:
ffmpeg -i raw.mp4 -filter:v "select='gt(scene,0.02)',showinfo" -f null - 2>&1 \
  | grep -o "pts_time:[0-9.]*" | cut -d: -f2

# Where it sat still (these are the waits to cut):
ffprobe -v error -select_streams v:0 -show_entries frame=best_effort_timestamp_time \
  -of csv=p=0 raw.mp4
```

A tap lands a moment **before** the change it causes. Read each change, then place
the marker in the second before it.

To see what a moment shows, seek accurately. `-ss` before `-i` lands on a keyframe
and lies to you on these variable-frame-rate files:

```bash
ffmpeg -i raw.mp4 -vf "select='gte(t\,42)',scale=200:-2" -frames:v 1 \
  -fps_mode passthrough shot.jpg
```

## 3. Annotate

```bash
python3 .claude/skills/annotated-screen-recording/scripts/annotate.py spec.json
```

```json
{
  "source": "raw.mp4",
  "output": "demo.mp4",
  "captions": [[0.0, 6.5, "The app, signed out"],
               [6.5, 22.0, "Tap: Sign in with Google"]],
  "taps":     [[10.0, 11.0, 600, 2233]],
  "keep":     [[1.5, 7.5], [9.3, 12.5]]
}
```

- Tap coordinates are pixels in the source frame. To convert a screen coordinate
  from a Mac screenshot: `video_x = (mac_x - device_left) * (frame_width / device_width)`.
- `keep` windows play at their real speed and are joined in order.
- The script normalizes to 15 fps first. Without that, a variable-frame-rate capture
  collapses each still window to one frame.

## 4. Check before you send it

Sample the OUTPUT at the middle of each caption and at each marker, and look at the
frames. Confirm the caption matches the screen and the marker sits on the control.
A caption that names the wrong control is worse than no caption.

Sizes to expect: about 1 MB and under a minute for a sign-in-to-result flow.
