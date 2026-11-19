# MedPredict for Android

An installable Android app with the MedPredict name, a medical-box launcher icon,
its own app window, a loading screen and Android back navigation. It loads the
existing deployed Streamlit interface directly. The Python models and account
services continue to run on the server, so an internet connection is required.
Website updates appear in the app without rebuilding the APK. The independent
deployment serves the application directly, without the Community Cloud shell.

The app includes a system file picker, a save-file dialog for supported report
downloads, and camera/microphone permission handling for the app's own origin.
External links open in the appropriate external app. These device-dependent
features should be checked on a real phone before distributing widely.
The app first opens a Trusted Web Activity using the phone's Chrome/browser
session. The browser independently verifies the deployment's Digital Asset
Links file, so Google authentication can take place in the real browser.
If a compatible browser is unavailable, it falls back to the built-in WebView
with a time-limited loading screen and username sign-in. Google sign-in in that
fallback opens the website externally. Browser origin indicators remain
visible for external/unverified pages.

## Install

1. Download `MedPredict-Android.apk` on an Android phone running Android 8 or later.
2. Open the file. If Android asks, allow this browser or Files app to install it.
3. Install and open **MedPredict** from the launcher.

## Build

Install a JDK and Google's official Android SDK Platform 35 and Build Tools 35.0.0.
Then run:

```sh
python3 build_apk.py \
  --android-jar /path/to/android-sdk/platforms/android-35/android.jar \
  --build-tools /path/to/android-sdk/build-tools/35.0.0 \
  --signing-dir /private/path/to/medpredict-signing \
  --app-url https://your-deployment.example/ \
  --out /path/to/MedPredict-Android.apk
```

The script compiles resources and Java, creates DEX bytecode, aligns the package,
signs it, and verifies the resulting signature and package metadata. It generates
a private signing key on the first build. Keep the key and its password private
and reuse them for updates; never commit them or share them with APK recipients.
Increment the version code in `build_apk.py` before distributing a later update.

The build requires the independent deployment URL, and embeds its matching
Digital Asset Links statement. The deployment must publish the APK signing
certificate fingerprint. The four original design versions are unchanged.

## Verification

The APK is compiled with Android Platform 35, targets API 35 and supports API 26+.
It is signed with a private local-distribution certificate and is not debuggable.
APK signature, alignment, manifest, launcher activity, label and icon are checked
by the build script. A physical Android device or emulator is still needed to
verify live sign-in, predictions, camera access, report files and navigation.

No analytics, advertising SDKs or extra Android libraries are included. HTTPS
certificate checks and Android WebView Safe Browsing remain enabled. Native
permissions are requested only when a trusted MedPredict page requests them.
