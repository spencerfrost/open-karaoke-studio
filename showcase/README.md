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
| Open | `src/shots/HookShot.tsx` (`OpenShot`) | "Karaoke night." → "Any song." over a wall of covers |
| Find | `src/shots/FindShot.tsx` | A search types "don't blink", Add is pressed, the cover breaks into the song's waveform |
| Split | `src/shots/SplitShot.tsx` | The waveform tears into singer and music on the song's three chord stabs |
| TV | `src/shots/HookShot.tsx` (`TvShot`) | "Hosted on your TV.", the TV, bunny and name land on the stabs, push through the screen |
| Remote | `src/shots/RemoteShot.tsx` | One phone adds a song, four more fire theirs at the TV's queue |
| Sing | `src/shots/SingShot.tsx` | Lyrics on the TV, the "Original singer" fader up and down, then "Make it yours" flips through the four themes on the beat |
| Close | `src/shots/CloseShot.tsx` | Logo, tags, GitHub link |

`src/Showcase.tsx` puts them in order and lays the audio under them. Every cut sits on the song's beat grid
(`src/beats.ts`): the shots are counted back in beats from the sing shot, so changing a shot's length in beats
moves the ones before it.

## Soundtrack

"Don't Blink" by Dropical (royalty-free). The audio isn't committed. To render, put these in place:

- `public/covers/`: real album covers for the open's background options (`Open-*` compositions,
  `src/components/CoverBackgrounds.tsx`). `scripts/pick-covers.sh` copies a fixed random set from the app's
  library (`LIBRARY_DIR` in `backend/.env`). They stay local because the labels own them.
- `public/audio/instrumental.mp3` and `public/audio/vocals.mp3`: the app's three-track separation of the song
  (`instrumental.mp3` and `vocals.mp3` from the song's folder in the library).

The data in `src/data/` comes from the same song in the app:

- `lyrics.json`: the lines on screen with the app's word timings. Lines with `"checked": true` were confirmed by ear.
- `waveform.json`: levels of the separated vocals and instrumental, 0:40–0:49.6.
- `beats.json`: the song's beat grid (librosa), used for every cut and the theme flips.
