# MedPredict for Windows

Run **MedPredict.exe** on a 64-bit Windows 10 or Windows 11 PC. The first launch
offers to install MedPredict into your own Windows account and place shortcuts
named MedPredict on the desktop and Start menu. Choose No to open it once
without installation. Installation does not require administrator rights.

MedPredict opens the deployed reference-inspired interface in Microsoft Edge's
application window, with Chrome as a fallback. If neither is installed, it
opens in your default browser. The hosted service requires internet access.
Website updates appear without downloading another Windows executable.
Installed copies appear in Windows Settings under Installed apps.

Build from this directory with Python, Pillow and Zig 0.14.1:

```sh
python build_windows.py --zig /path/to/zig --out /path/to/MedPredict.exe
```

The executable contains its own icon and Windows release metadata (MedPredict
1.1.0). This personal-distribution executable does not have an Authenticode
signature. Windows may display an unknown-publisher notice. Verify the
provided file before running it. The Windows build needs a Windows PC for
end-to-end installation and launch testing.
