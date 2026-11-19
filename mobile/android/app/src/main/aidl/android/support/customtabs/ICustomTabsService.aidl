// Derived from the Android Open Source Project Custom Tabs public IPC interface.
// Copyright (C) 2015 The Android Open Source Project
// Licensed under the Apache License, Version 2.0 (https://www.apache.org/licenses/LICENSE-2.0).
// This client uses only the first two, explicitly numbered, compatible methods.
package android.support.customtabs;
import android.support.customtabs.ICustomTabsCallback;

interface ICustomTabsService {
    boolean warmup(long flags) = 1;
    boolean newSession(in ICustomTabsCallback callback) = 2;
}
