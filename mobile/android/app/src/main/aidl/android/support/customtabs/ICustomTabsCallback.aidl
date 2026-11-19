// Derived from the Android Open Source Project Custom Tabs public IPC interface.
// Copyright (C) 2015 The Android Open Source Project
// Licensed under the Apache License, Version 2.0 (https://www.apache.org/licenses/LICENSE-2.0).
package android.support.customtabs;
import android.net.Uri;
import android.os.Bundle;

interface ICustomTabsCallback {
    oneway void onNavigationEvent(int navigationEvent, in Bundle extras) = 1;
    oneway void extraCallback(String callbackName, in Bundle args) = 2;
    void onMessageChannelReady(in Bundle extras) = 3;
    void onPostMessage(String message, in Bundle extras) = 4;
    oneway void onRelationshipValidationResult(int relation, in Uri origin, boolean result, in Bundle extras) = 5;
    Bundle extraCallbackWithResult(String callbackName, in Bundle args) = 6;
    oneway void onActivityResized(int height, int width, in Bundle extras) = 7;
    oneway void onWarmupCompleted(in Bundle extras) = 8;
}
