# Showcase video

The Open Karaoke Studio showcase video, made with [Remotion](https://www.remotion.dev/) (React → MP4).
The screens are redrawn in the app's theme tokens, not recorded from the app.

```bash
pnpm install
pnpm studio          # scrub and edit in the browser
pnpm render          # full video → out/showcase.mp4
pnpm render:shot RemoteShot out/remote-shot.mp4   # one shot
```

## Shots

| Shot | File | What happens |
|---|---|---|
| Hook | `src/shots/HookShot.tsx` | "Karaoke night." → "Any song." → "Your TV.", push through the screen |
| Remote | `src/shots/RemoteShot.tsx` | Phones send songs to the TV's queue |
| Split | `src/shots/SplitShot.tsx` | The song's waveform splits into singer and music |
| Sing | `src/shots/SingShot.tsx` | Lyrics on the TV, the "Original singer" fader up and down, then "Make it yours" theme flips on the beat |
| Close | `src/shots/CloseShot.tsx` | Logo, tags, GitHub link |

`src/Showcase.tsx` puts them in order and lays the audio under them.

## Soundtrack

"Don't Blink" by Dropical (royalty-free). The audio isn't committed. To render, put these in place:

- `public/audio/instrumental.mp3` and `public/audio/vocals.mp3`: the app's three-track separation of the song
  (`instrumental.mp3` and `vocals.mp3` from the song's folder in the library).

The data in `src/data/` comes from the same song in the app:

- `lyrics.json`: the lines on screen with the app's word timings. Lines with `"checked": true` were confirmed by ear.
- `waveform.json`: levels of the separated vocals and instrumental, 0:40–0:49.6.
- `beats.json`: the song's beat grid (librosa), used for the theme flips.
