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
- on "Stop & save," exports **two files**: `sleep-<timestamp>.csv` (the
  samples) and `sleep-<timestamp>.meta.json` (a sidecar with the sample rate
  and units) via your browser's normal download

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

## 2. Analyze it — two ways

You now have both files on your computer. Pick either path (or both — they
don't conflict):

### 2a. The real NeuroSleep Twin app

This runs your recording through the actual production pipeline (Postgres +
Celery, same as every other study), not a standalone script.

1. Start the real app (see the repo root README's "Getting started").
2. Open `http://localhost:5173` → **Upload Your Sleep Study**.
3. Select **both** `sleep-<timestamp>.csv` and `sleep-<timestamp>.meta.json`
   together (drag both in, or multi-select in the file picker) → **Upload &
   Analyze**.
4. On the **Channel Mapping** screen, map `audio_rms` → **resp** (this is
   what makes the real detector run on it) and, optionally, `motion_mag` →
   **other** (stored, but no pipeline stage reads it yet — that's a real gap,
   not a bug: there's no "motion" signal type in the app today). Leave
   `t_sec` unmapped — it's an inert extra channel, not a real signal.
5. Confirm the mapping. The **Events** page will show detected candidate
   events; **Oxygen Burden**, **Brain Response**, and **Autonomic Response**
   will correctly say "not available" — there's no SpO2/EEG/ECG channel here,
   and the app never fills those in with invented numbers.

This path was verified end-to-end against the real running backend (upload →
ingest → channel mapping → detection), including a real pre-existing bug it
surfaced and got fixed: deleting a study with detected events used to fail
(`respiratory_events.channel_id` had no `ON DELETE CASCADE`) — see
`backend/alembic/versions/*_add_ondelete_cascade_*.py`.

### 2b. The standalone Live Replay viewer

Move `sleep-<timestamp>.csv` into `personal-sleep-tracker/recordings/` on
this computer (that folder is git-ignored — recordings never get committed;
the `.meta.json` isn't needed here). Then:

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
- a cardiovascular-risk-context panel citing real published research at
  whatever severity band your detected-event rate maps to — population
  context, not a personal score

This path is faster to iterate on and doesn't need Postgres/Redis running,
but nothing here is saved into the real app's database.

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
and an accelerometer-magnitude reading, both at 4 Hz. Raw loudness is always
positive, but `detect_events()` (`backend/app/services/respiratory_events/
detector.py`) looks for *drops in oscillation around the signal's own
median* — correct for a real effort belt (AC-coupled, swings positive and
negative all night), backwards for a strictly-positive signal. Both the real
app and the standalone viewer now share one fix for this:
`prepare_resp_signal()` in that same `detector.py` — if a channel never goes
negative, it subtracts a short rolling mean first so it oscillates around
zero on every breath and goes flat during a pause, same shape as a real
effort channel; a real physiological channel (already negative-going) passes
through unchanged. One disclosed preprocessing step, one detector, used by
both paths in §2.

## What's missing: heart rate

You can't get real heart rate from a phone microphone or accelerometer —
that needs an actual pulse signal (ECG, or camera-based photoplethysmography
with a finger over the camera+flash). Neither is built into `recorder.html`
today. The `motion_mag` channel is *not* a heart-rate proxy — don't read the
movement numbers as pulse. If heart-rate tracking matters to you, that's a
real, separate feature (camera PPG capture) to build next, not something to
fake from what's already being recorded.
