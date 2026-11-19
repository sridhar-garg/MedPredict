package app.medpredict.mobile;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.RemoteException;
import android.view.Gravity;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.support.customtabs.ICustomTabsCallback;
import android.support.customtabs.ICustomTabsService;

/** Launches a browser-verified Trusted Web Activity, with a WebView fallback.
 * The browser alone verifies Digital Asset Links; no security checks are disabled.
 * Chrome handles Google account cookies, external OAuth pages and device permissions.
 */
public final class LauncherActivity extends Activity {
    private static final String SERVICE = "android.support.customtabs.action.CustomTabsService";
    private static final int OPEN_WORKSPACE = 73;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean bound, opened;
    private Uri url;
    private final Runnable timeout = () -> fallback();

    // No page contents, credentials, messages or identity tokens are requested or processed.
    private final ICustomTabsCallback callback = new ICustomTabsCallback.Stub() {
        @Override public void onNavigationEvent(int event, Bundle extras) { }
        @Override public void extraCallback(String name, Bundle args) { }
        @Override public void onMessageChannelReady(Bundle extras) { }
        @Override public void onPostMessage(String message, Bundle extras) { }
        @Override public void onRelationshipValidationResult(int relation, Uri origin, boolean result, Bundle extras) { }
        @Override public Bundle extraCallbackWithResult(String name, Bundle args) { return null; }
        @Override public void onActivityResized(int height, int width, Bundle extras) { }
        @Override public void onWarmupCompleted(Bundle extras) { }
    };

    private final ServiceConnection connection = new ServiceConnection() {
        @Override public void onServiceConnected(ComponentName name, IBinder binder) {
            // Do not block the screen if a browser is starting slowly.
            new Thread(() -> {
                boolean ready = false;
                try {
                    ICustomTabsService client = ICustomTabsService.Stub.asInterface(binder);
                    client.warmup(0L);
                    ready = client.newSession(callback);
                } catch (RemoteException | RuntimeException ignored) { }
                final boolean valid = ready;
                runOnUiThread(() -> { if (valid) launch(name.getPackageName()); else fallback(); });
            }, "medpredict-browser-connect").start();
        }
        @Override public void onServiceDisconnected(ComponentName name) { if (!opened) fallback(); }
        @Override public void onNullBinding(ComponentName name) { fallback(); }
        @Override public void onBindingDied(ComponentName name) { if (!opened) fallback(); }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if (state != null && state.getBoolean("opened")) { finish(); return; }
        url = Uri.parse(getString(R.string.app_url));
        LinearLayout content = new LinearLayout(this);
        content.setBackgroundColor(getColor(R.color.canvas));
        content.setOrientation(LinearLayout.VERTICAL);
        content.setGravity(Gravity.CENTER);
        int size = Math.round(getResources().getDisplayMetrics().density * 84);
        ImageView logo = new ImageView(this);
        logo.setImageResource(R.drawable.medical_box);
        content.addView(logo, new LinearLayout.LayoutParams(size, size));
        TextView title = new TextView(this);
        title.setText("MedPredict"); title.setTextSize(28); title.setTextColor(getColor(R.color.ink));
        title.setGravity(Gravity.CENTER); title.setPadding(0, 20, 0, 20);
        content.addView(title);
        content.addView(new ProgressBar(this));
        setContentView(content);

        String provider = browserProvider();
        if (provider == null) { fallback(); return; }
        try {
            bound = bindService(new Intent(SERVICE).setPackage(provider), connection, Context.BIND_AUTO_CREATE);
        } catch (SecurityException ex) { bound = false; }
        if (!bound) fallback(); else handler.postDelayed(timeout, 6000);
    }

    private String browserProvider() {
        PackageManager pm = getPackageManager();
        if (pm.resolveService(new Intent(SERVICE).setPackage("com.android.chrome"), 0) != null)
            return "com.android.chrome";
        ResolveInfo browser = pm.resolveActivity(new Intent(Intent.ACTION_VIEW, url), PackageManager.MATCH_DEFAULT_ONLY);
        if (browser != null && browser.activityInfo != null) {
            String candidate = browser.activityInfo.packageName;
            if (!getPackageName().equals(candidate) && pm.resolveService(new Intent(SERVICE).setPackage(candidate), 0) != null)
                return candidate;
        }
        return null;
    }

    private void launch(String browser) {
        if (opened || isFinishing() || isDestroyed()) return;
        Intent intent = new Intent(Intent.ACTION_VIEW, url).setPackage(browser);
        Bundle extras = new Bundle();
        extras.putBinder("android.support.customtabs.extra.SESSION", callback.asBinder());
        // Chrome will show normal browser chrome unless the owned origin is verified.
        extras.putBoolean("android.support.customtabs.extra.LAUNCH_AS_TRUSTED_WEB_ACTIVITY", true);
        extras.putInt("android.support.customtabs.extra.TOOLBAR_COLOR", getColor(R.color.brand));
        intent.putExtras(extras);
        try {
            startActivityForResult(intent, OPEN_WORKSPACE);
            opened = true;
            handler.removeCallbacks(timeout);
        } catch (RuntimeException ex) { fallback(); }
    }

    private void fallback() {
        if (opened || isFinishing() || isDestroyed()) return;
        opened = true;
        handler.removeCallbacks(timeout);
        startActivity(new Intent(this, MainActivity.class));
        finish();
    }

    @Override public void onSaveInstanceState(Bundle state) {
        state.putBoolean("opened", opened);
        super.onSaveInstanceState(state);
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == OPEN_WORKSPACE) finish();
    }

    @Override protected void onDestroy() {
        handler.removeCallbacks(timeout);
        if (bound) { unbindService(connection); bound = false; }
        super.onDestroy();
    }
}
