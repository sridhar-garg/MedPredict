# MedPredict for Android

An installable Android app with the MedPredict name, a medical-box launcher icon,
its own app window, a loading screen and Android back navigation. It loads the
existing deployed Streamlit interface directly. The Python models and account
services continue to run on the server, so an internet connection is required.
Website updates appear in the app without rebuilding the APK. Streamlit's
supported embedded mode hides the hosting toolbar and footer.

The app includes a system file picker, a save-file dialog for supported report
downloads, and camera/microphone permission handling for the app's own origin.
External links open in the appropriate external app. These device-dependent
features should be checked on a real phone before distributing widely.

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
  --out /path/to/MedPredict-Android.apk
```

The script compiles resources and Java, creates DEX bytecode, aligns the package,
signs it, and verifies the resulting signature and package metadata. It generates
a private signing key on the first build. Keep the key and its password private
and reuse them for updates; never commit them or share them with APK recipients.
Increment the version code in `build_apk.py` before distributing a later update.

Change `app/src/main/res/values/strings.xml` to point to a different MedPredict
deployment. The default is the current public Streamlit app, which follows the
`design/reference-inspired-ui` branch. The four design versions are unchanged.

## Verification

The APK is compiled with Android Platform 35, targets API 35 and supports API 26+.
It is signed with a private local-distribution certificate and is not debuggable.
APK signature, alignment, manifest, launcher activity, label and icon are checked
by the build script. A physical Android device or emulator is still needed to
verify live sign-in, predictions, camera access, report files and navigation.

No analytics, advertising SDKs or extra Android libraries are included. HTTPS
certificate checks and Android WebView Safe Browsing remain enabled. Native
permissions are requested only when a trusted MedPredict page requests them.
