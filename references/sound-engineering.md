# Sound Engineering for Reels

Web research summary (2026). Loudness and ducking figures come from creator and vendor guidance,
not Meta documentation. No official Instagram LUFS spec was found.

## Targets

- **Integrated loudness: −14 LUFS** with a **−1 dBTP** true-peak ceiling is the common target for
  Reels, TikTok, and Shorts. Some creators push to −10 to −12 for extra punch; that is anecdotal.
  Sources: [Opus – LUFS presets](https://opus.pro/blog/best-loudness-normalizers),
  [Film and Flow – LUFS guide](https://filmandflow.beehiiv.com/p/the-ultimate-lufs-guide-perfect-audio-for-social-media),
  [Pixteller – audio finishing checklist](https://pixteller.com/blog/the-audio-finishing-checklist-every-social-media-creator-needs-649).
- **Do not trust the "80% watch with sound" claim.** It traces back to an unnamed "internal data" blog.

## Mix order

1. **Dialogue first.** Balance voice, then music, then SFX. Phone speakers and earbuds make
   background music that competes with speech lose the message.
2. **Ducking.** Lower music while speech is present. Mechanics: a compressor reduces music gain when voice
   crosses a threshold; attack and release set how fast it dips and recovers. Auto-ducking can pump on
   short pauses or return music too early between phrases, so check by ear and correct keyframes.
   Sources: [Openclip – audio ducking](https://openclip.app/learn/audio-ducking.md),
   [NemoVideo – balancing voice and music](https://www.nemovideo.com/blog/ai-video-editing/how-to-balance-voiceover-and-background-music).
3. **Set the export loudness last.** Measure the whole mix, then normalize to −14 LUFS / −1 dBTP.
   Clip-level normalization before the mix is a known trap: normalize the final program, not each clip.
   Source: [Hollyland – normalize audio in Resolve](https://store.hollyland.com/blogs/creator-hub/normalize-audio-in-davinci-resolve).

## DaVinci Resolve specifics

- Fairlight's loudness meter has EBU R128, ATSC A/85, and BS.1770 options. Reset it, play the full
  program, and make sure you are monitoring the same Main bus you export from.
- Deliver page has **Normalize to Standard** (scales toward the target until loudness or peak limits govern).
- Resolve 21 **Voice Isolation** and **Dialogue Leveler** help specific recordings, but do not control
  master loudness.
- Versions differ, and some features are Studio-only. Verify menu names in your version.
  Sources: [DaVinci Resolve Club – audio levels and LUFS](https://davinciresolveclub.com/davinci-resolve-audio-levels-lufs/),
  [Cutsio – audio volume in Resolve](https://cutsio.com/blog/automatically-set-perfect-audio-volume-in-davinci-resolve).

## What the skill does automatically

`scripts/master_audio.py` (ffmpeg, no Resolve needed) ducks an existing music bed under narration,
then loudness-normalizes the whole mix to −14 LUFS / −1 dBTP. See the script header for usage.
