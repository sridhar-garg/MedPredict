package app.medpredict.mobile;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.util.Base64;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.CookieManager;
import android.webkit.PermissionRequest;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.List;
import org.json.JSONTokener;
import org.json.JSONObject;

/** Installed Android host for the existing, online MedPredict interface. */
public final class MainActivity extends Activity {
    private static final int PICK_FILE = 41, SAVE_FILE = 42, MEDIA_PERMISSION = 43;
    private WebView web;
    private LinearLayout cover;
    private TextView status;
    private Button retry;
    private ProgressBar spinner;
    private ValueCallback<Uri[]> chooser;
    private PermissionRequest mediaRequest;
    private byte[] pendingDownload;
    private String appUrl, appHost;
    private boolean failed;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        appUrl = getString(R.string.app_url);
        appHost = Uri.parse(appUrl).getHost();
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(getColor(R.color.canvas));
        setContentView(root);
        if (Build.VERSION.SDK_INT >= 30) {
            root.setOnApplyWindowInsetsListener((view, insets) -> {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars());
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
                return insets;
            });
        }

        web = new WebView(this);
        root.addView(web, new FrameLayout.LayoutParams(-1, -1));
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSafeBrowsingEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(true);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, true);
        web.setBackgroundColor(getColor(R.color.canvas));
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri url = request.getUrl();
                if (!request.isForMainFrame()) return false;
                if (insideApp(url)) return false;
                if ("https".equals(url.getScheme()) && "accounts.google.com".equals(url.getHost())) {
                    showGoogleBrowser();
                    return true;
                }
                if (request.hasGesture()) openExternal(url);
                return true;
            }
            @Override public void onPageStarted(WebView view, String url, android.graphics.Bitmap icon) {
                failed = false;
            }
            @Override public void onPageFinished(WebView view, String url) {
                if (!failed) cover.setVisibility(View.GONE);
                CookieManager.getInstance().flush();
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) showError();
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (chooser != null) chooser.onReceiveValue(null);
                chooser = callback;
                try {
                    Intent picker = params.createIntent();
                    picker.addCategory(Intent.CATEGORY_OPENABLE);
                    startActivityForResult(picker, PICK_FILE);
                } catch (ActivityNotFoundException e) {
                    chooser.onReceiveValue(null); chooser = null;
                    message("No file picker is available on this device.");
                }
                return true;
            }
            @Override public void onPermissionRequest(PermissionRequest request) {
                runOnUiThread(() -> requestMedia(request));
            }
            @Override public void onPermissionRequestCanceled(PermissionRequest request) {
                if (mediaRequest == request) mediaRequest = null;
            }
        });
        web.setDownloadListener((url, agent, disposition, type, length) -> {
            if (url.startsWith("blob:") && trustedOrigin(Uri.parse(web.getUrl()))) {
                String script = "(async()=>{try{const b=await(await fetch(" + JSONObject.quote(url)
                    + ")).blob();if(b.size>26214400)return null;return await new Promise(r=>{const f=new FileReader();f.onload=()=>r(f.result);f.readAsDataURL(b)})}catch(e){return null}})()";
                // evaluateJavascript cannot await a Promise. Resolve via an explicit callback poll.
                String id = "__medpredictDownload";
                web.evaluateJavascript("window." + id + "=undefined;" + script + ".then(x=>window." + id + "=x)", null);
                pollDownload(0, type, URLUtil.guessFileName(url, disposition, type));
            } else if (url.startsWith("data:")) {
                saveDataUrl(url, type, "MedPredict-report");
            } else {
                openExternal(Uri.parse(url));
            }
        });

        cover = new LinearLayout(this);
        cover.setOrientation(LinearLayout.VERTICAL);
        cover.setGravity(Gravity.CENTER);
        cover.setPadding(dp(28), dp(28), dp(28), dp(28));
        cover.setBackgroundColor(getColor(R.color.canvas));
        ImageView logo = new ImageView(this);
        logo.setImageResource(R.drawable.medical_box);
        cover.addView(logo, new LinearLayout.LayoutParams(dp(82), dp(82)));
        TextView title = new TextView(this);
        title.setText("MedPredict"); title.setTextSize(28); title.setTextColor(getColor(R.color.ink));
        title.setGravity(Gravity.CENTER); title.setPadding(0, dp(18), 0, dp(12));
        cover.addView(title);
        status = new TextView(this);
        status.setText("Opening your health workspace…"); status.setTextSize(15);
        status.setTextColor(Color.rgb(87,94,118)); status.setGravity(Gravity.CENTER);
        cover.addView(status);
        spinner = new ProgressBar(this);
        LinearLayout.LayoutParams spin = new LinearLayout.LayoutParams(dp(30), dp(30));
        spin.topMargin = dp(24); cover.addView(spinner, spin);
        retry = new Button(this); retry.setText("Try again"); retry.setVisibility(View.GONE);
        retry.setOnClickListener(v -> loadApp()); cover.addView(retry);
        root.addView(cover, new FrameLayout.LayoutParams(-1, -1));
        if (state == null || web.restoreState(state) == null) loadApp();
        else cover.setVisibility(View.GONE);
    }

    private boolean trustedOrigin(Uri uri) {
        return uri != null && "https".equals(uri.getScheme()) && appHost.equals(uri.getHost());
    }
    private boolean insideApp(Uri uri) {
        if (trustedOrigin(uri)) return true;
        // Streamlit Community Cloud may perform its session bootstrap on these hosts.
        return "https".equals(uri.getScheme()) &&
            ("share.streamlit.io".equals(uri.getHost()) || "auth.streamlit.io".equals(uri.getHost()));
    }
    private void loadApp() {
        failed = false; retry.setVisibility(View.GONE); spinner.setVisibility(View.VISIBLE);
        status.setText("Opening your health workspace…"); cover.setVisibility(View.VISIBLE);
        web.loadUrl(appUrl);
    }
    private void showError() {
        failed = true; status.setText("Unable to reach MedPredict. Check your internet connection and try again.");
        spinner.setVisibility(View.GONE); retry.setVisibility(View.VISIBLE); cover.setVisibility(View.VISIBLE);
    }
    private void openExternal(Uri uri) {
        String scheme = uri.getScheme();
        if (!"https".equals(scheme) && !"http".equals(scheme) && !"mailto".equals(scheme) && !"tel".equals(scheme)) return;
        try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); }
        catch (ActivityNotFoundException e) { message("No app is available to open this link."); }
    }
    private void showGoogleBrowser() {
        new AlertDialog.Builder(this)
            .setTitle("Continue with Google")
            .setMessage("Google requires sign-in through a browser. Open MedPredict in your browser to continue with Google, or use the usual sign-in here.")
            .setPositiveButton("Open MedPredict", (dialog, which) -> {
                loadApp();
                openExternal(Uri.parse(appUrl).buildUpon().clearQuery().build());
            })
            .setNegativeButton("Stay here", (dialog, which) -> loadApp())
            .setOnCancelListener(dialog -> loadApp())
            .show();
    }
    private void requestMedia(PermissionRequest request) {
        if (!trustedOrigin(request.getOrigin())) { request.deny(); return; }
        if (mediaRequest != null) mediaRequest.deny();
        mediaRequest = request;
        List<String> needed = new ArrayList<>();
        for (String resource : request.getResources()) {
            String permission = PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(resource) ? Manifest.permission.CAMERA
                : PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource) ? Manifest.permission.RECORD_AUDIO : null;
            if (permission != null && checkSelfPermission(permission) != PackageManager.PERMISSION_GRANTED) needed.add(permission);
        }
        if (needed.isEmpty()) finishMediaRequest();
        else requestPermissions(needed.toArray(new String[0]), MEDIA_PERMISSION);
    }
    private void finishMediaRequest() {
        PermissionRequest request = mediaRequest; mediaRequest = null;
        if (request == null) return;
        List<String> allowed = new ArrayList<>();
        for (String resource : request.getResources()) {
            if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(resource) && checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) allowed.add(resource);
            if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource) && checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) allowed.add(resource);
        }
        if (allowed.isEmpty()) request.deny(); else request.grant(allowed.toArray(new String[0]));
    }
    @Override public void onRequestPermissionsResult(int request, String[] permissions, int[] grants) {
        super.onRequestPermissionsResult(request, permissions, grants);
        if (request == MEDIA_PERMISSION) finishMediaRequest();
    }
    private void pollDownload(int attempt, String mime, String filename) {
        if (attempt >= 100) { message("Unable to prepare this download. Please try again."); return; }
        web.evaluateJavascript("window.__medpredictDownload === undefined ? 'pending' : window.__medpredictDownload", value -> {
            try {
                Object decoded = new JSONTokener(value).nextValue();
                if ("pending".equals(decoded)) web.postDelayed(() -> pollDownload(attempt + 1, mime, filename), 150);
                else if (decoded instanceof String) { web.evaluateJavascript("delete window.__medpredictDownload", null); saveDataUrl((String) decoded, mime, filename); }
                else message("Unable to prepare this download.");
            } catch (Exception e) { message("Unable to prepare this download."); }
        });
    }
    private void saveDataUrl(String data, String mime, String name) {
        try {
            int comma = data.indexOf(',');
            if (comma < 0 || !data.substring(0, comma).contains(";base64") || data.length() > 36*1024*1024) throw new IllegalArgumentException();
            pendingDownload = Base64.decode(data.substring(comma + 1), Base64.DEFAULT);
            Intent save = new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE);
            save.setType(mime == null || mime.isEmpty() ? "application/octet-stream" : mime);
            save.putExtra(Intent.EXTRA_TITLE, name.replaceAll("[^a-zA-Z0-9._ -]", "_"));
            startActivityForResult(save, SAVE_FILE);
        } catch (Exception e) { pendingDownload = null; message("Unable to save this file."); }
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == PICK_FILE && chooser != null) {
            Uri[] values = WebChromeClient.FileChooserParams.parseResult(result, data);
            // Only return document-provider URIs; never expose the app's private files.
            if (values != null) for (Uri uri : values) if (!"content".equals(uri.getScheme())) { values = null; break; }
            chooser.onReceiveValue(values); chooser = null;
        }
        if (request == SAVE_FILE) {
            if (result == RESULT_OK && data != null && data.getData() != null && pendingDownload != null) {
                try (OutputStream output = getContentResolver().openOutputStream(data.getData())) {
                    if (output != null) { output.write(pendingDownload); message("File saved."); }
                } catch (Exception e) { message("Unable to save this file."); }
            }
            pendingDownload = null;
        }
    }
    @Override public void onBackPressed() { if (web.canGoBack()) web.goBack(); else super.onBackPressed(); }
    @Override protected void onSaveInstanceState(Bundle state) { web.saveState(state); super.onSaveInstanceState(state); }
    @Override protected void onPause() { web.onPause(); CookieManager.getInstance().flush(); super.onPause(); }
    @Override protected void onResume() { super.onResume(); if (web != null) web.onResume(); }
    @Override protected void onDestroy() {
        if (chooser != null) chooser.onReceiveValue(null);
        if (mediaRequest != null) mediaRequest.deny();
        pendingDownload = null; web.destroy(); super.onDestroy();
    }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private void message(String text) { Toast.makeText(this, text, Toast.LENGTH_LONG).show(); }
}
