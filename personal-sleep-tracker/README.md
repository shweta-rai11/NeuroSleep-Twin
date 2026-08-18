# Personal Sleep Tracker

A phone-only way to record your own night and watch it analyzed live, using the
same event-detection code as NeuroSleep Twin. No PSG device, no wearable, no
extra hardware.

**Read this before you rely on it:** this uses your phone's microphone
(breathing/snore-sound loudness) and motion sensor as *proxies* for breathing
effort. It does not measure blood oxygen, heart rhythm, or brain activity —
the signals a real sleep-apnea evaluation is actually built on. Treat it as a
personal screening/tracking tool, not a diagnosis. If you suspect sleep apnea,
see a doctor about a real sleep study.

## 1. Record a night

`recorder.html` is a single self-contained page — no server, no install. It:
- asks for microphone + motion-sensor permission
- keeps the screen awake and samples a breathing-sound loudness reading and a
  movement reading 4 times a second
- **never stores or uploads raw audio** — only a numeric loudness level, so
  there's no recording of what was actually said or heard in the room
- on "Stop & save," exports a CSV (`sleep-<timestamp>.csv`) via your browser's
  normal download

Get it onto your phone one of these ways, then open it directly:
- **iPhone**: AirDrop `recorder.html` to your phone, open it from Files in
  Safari.
- **Android**: send it to yourself (email/Drive/etc.), open it from your
  Downloads folder in Chrome.
- **Fallback** if the microphone permission prompt doesn't appear when opened
  as a local file: run `scripts/dev/start_live_demo.sh` on your computer, find
  your computer's LAN IP (`ipconfig getifaddr en0` on macOS), and open
  `http://<that-ip>:8090/recorder` from the phone on the same WiFi. Some
  browsers still refuse microphone access over plain `http://`, in which case
  the real fix is HTTPS — ask for a tunnel (e.g. `cloudflared tunnel --url
  http://localhost:8090`) if you hit this.

Before bed: plug the phone in, dim the screen, place it face-up on the
nightstand (mic side toward you, not under the pillow), hit **Start
recording**, then just go to sleep. Hit **Stop & save** in the morning.

## 2. Move the file into place

Move the downloaded `sleep-*.csv` into `personal-sleep-tracker/recordings/`
on this computer (that folder is git-ignored — recordings never get
committed). It'll show up in the Live Replay viewer's record dropdown
automatically, under "My recordings."

## 3. Watch it analyzed

```
scripts/dev/start_live_demo.sh
open http://localhost:8090
```

Pick your recording, hit Start. You'll see:
- a live **breathing** trace and a **motion** trace (no EEG/ECG/SpO2 lanes —
  there's no sensor for those here)
- candidate breathing-pause events as they're detected, each with a duration,
  a movement-response reading, and a fingerprint — with the desaturation,
  hr_response, and arousal axes shown as a hatched **n/a**, not a fake zero,
  because nothing measured them

## What this can and can't tell you

**Can:** give you a rough sense of how often your breathing sound drops out
for a sustained stretch overnight, and whether movement/restlessness clusters
around those stretches.

**Can't:** tell you your AHI, your oxygen desaturation, or whether what it
found is actually apnea rather than a room noise dip, a mic bump, or you
rolling away from the phone. The detector (`envelope-v1`, in
`backend/app/services/respiratory_events/detector.py`) was tuned for a real
respiratory-effort belt signal, not room audio — treat every count here as
"worth paying attention to," not as a validated number.

## How the signals are built

`recorder.html` writes `t_sec,audio_rms,motion_mag` — a loudness RMS reading
and an accelerometer-magnitude reading, both at 4 Hz. The viewer server
(`scripts/dev/live_replay_demo.py`, `_load_personal_recording` /
`_detrend`) turns the loudness signal into something shaped like a real
effort channel before handing it to the real detector: it subtracts a short
rolling mean so the signal oscillates around zero on every breath and goes
flat during a pause — because the detector looks for *drops in oscillation
around the signal's own median*, and raw loudness (always positive) doesn't
have that shape on its own. This is a disclosed preprocessing step, not a
different detector.
