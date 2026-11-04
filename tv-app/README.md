# Shield TV app

An Android TV app for the NVIDIA Shield. It opens the stage (`/stage`) full screen in a WebView
and lets the remote drive it. The stage itself is the web app in `frontend/`. See the
[plan](../docs/plans/2026-10-22-shield-tv-app.md) for why it's built this way.

## Remote

| Remote | What the stage gets |
|---|---|
| D-pad arrows | Arrow keys |
| D-pad center | Enter |
| Back | Escape (the stage's back) |
| Play/pause (game controller, media remotes) | Space |
| Hold Back | App menu: Reload, Change server address, Exit |
| Home | Leaves the app; the stage keeps its state |

## Build

Needs JDK 21. The Android Gradle Plugin doesn't run on the system's default JDK 27, so point the
build at 21 without changing the default:

```bash
cd tv-app
echo "sdk.dir=$HOME/Android/Sdk" > local.properties   # once
JAVA_HOME=/usr/lib/jvm/java-21-openjdk ./gradlew assembleDebug
```

The APK is at `app/build/outputs/apk/debug/app-debug.apk`.

## Install on the Shield

Once, on the Shield: Settings → Device Preferences → About → tap **Build** seven times. Then
Settings → Device Preferences → Developer options → turn on **Network debugging**.

```bash
adb connect <shield-ip>:5555        # accept the prompt on the TV the first time
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

The app shows up as a tile on the home screen. `-r` keeps the app's data, so the host stays
logged in across installs.

## Pointing it at the dev server

Hold Back → Change server address, then type the dev frontend, e.g. `192.168.1.20:5193` (no
scheme means `http://`). "Reset to karaoke.mrspinn.ca" goes back to prod. Each server has its
own login, since logins live in that origin's localStorage.

## Debugging

Debug builds let Chrome attach to the WebView. With the Shield connected over adb, open
`chrome://inspect` on the dev machine; the stage page is listed under the Shield. The console,
network tab and `innerWidth`/`devicePixelRatio` are all there.

If a frontend deploy doesn't show up on the TV, suspect the PWA service worker first: hold Back →
Reload, or clear it from DevTools → Application → Service workers.
