package app.aiworkspace.mobile;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.*;
import org.json.JSONObject;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public final class StandaloneActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final String HOME = "https://" + HOST + "/";
    private WebView web;
    private ValueCallback<Uri[]> chooser;
    private String pendingCallback;
    private boolean loaded;
    private static final int FILE_REQUEST = 41;
    private final String projectHost() { return getString(R.string.mp_project_host); }

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        web = new WebView(this);
        setContentView(web);
        web.setOnApplyWindowInsetsListener((view, insets) -> {
            if (android.os.Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout() | WindowInsets.Type.ime());
                view.setPadding(bars.left,bars.top,bars.right,bars.bottom);
            }
            return insets;
        });
        WebSettings s=web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(true); // Android system file chooser; file:// access remains disabled.
        s.setJavaScriptCanOpenWindowsAutomatically(false);
        s.setSupportMultipleWindows(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        if(android.os.Build.VERSION.SDK_INT>=26)s.setSafeBrowsingEnabled(true);
        WebView.setWebContentsDebuggingEnabled(false);
        web.addJavascriptInterface(new AuthBridge(),"MedPredictNative");
        web.setWebViewClient(new WebViewClient(){
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest req){
                Uri uri=req.getUrl();
                if(!"https".equals(uri.getScheme()))return denied();
                if(!HOST.equals(uri.getHost()))return projectHost().equals(uri.getHost())&&uri.getPort()==-1?null:denied();
                if(!"GET".equals(req.getMethod())||uri.getPort()!=-1)return denied();
                String path=uri.getPath();
                if(path==null||path.equals("/"))path="/index.html";
                if(!path.matches("/(?:[a-zA-Z0-9_-]+/)*[a-zA-Z0-9_.-]+")||path.contains(".."))return denied();
                try {
                    InputStream stream=getAssets().open("web"+path);
                    String mime=path.endsWith(".html")?"text/html":path.endsWith(".css")?"text/css":path.endsWith(".js")||path.endsWith(".mjs")?"text/javascript":path.endsWith(".json")?"application/json":path.endsWith(".webp")?"image/webp":path.endsWith(".svg")?"image/svg+xml":"application/octet-stream";
                    Map<String,String> headers=new HashMap<>();
                    headers.put("Cache-Control","no-store");
                    headers.put("X-Content-Type-Options","nosniff");
                    return new WebResourceResponse(mime,mime.startsWith("image/")&& !mime.endsWith("svg+xml")?null:"UTF-8",200,"OK",headers,stream);
                } catch(Exception ex){return denied();}
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest req){
                Uri u=req.getUrl();
                if (HOST.equals(u.getHost())&&"https".equals(u.getScheme()))return false;
                if(req.isForMainFrame()&&req.hasGesture()&&"https".equals(u.getScheme()))openExternal(u);
                return true;
            }
            @Override public void onPageFinished(WebView v,String url){
                if(HOME.equals(url)|| (HOME+"index.html").equals(url)){loaded=true;dispatchCallback();}
            }
        });
        web.setWebChromeClient(new WebChromeClient(){
            @Override public boolean onShowFileChooser(WebView v,ValueCallback<Uri[]> cb,FileChooserParams params){
                if(chooser!=null)chooser.onReceiveValue(null);
                chooser=cb;
                Intent intent=new Intent(Intent.ACTION_GET_CONTENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                intent.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"text/plain","application/pdf","image/png","image/jpeg","image/webp"});
                try{startActivityForResult(intent,FILE_REQUEST);return true;}catch(Exception ex){chooser.onReceiveValue(null);chooser=null;return false;}
            }
        });
        acceptCallback(getIntent());
        web.loadUrl(HOME);
    }
    private WebResourceResponse denied(){
        return new WebResourceResponse("text/plain","UTF-8",404,"Not Found",Collections.emptyMap(),new ByteArrayInputStream(new byte[0]));
    }
    private void openExternal(Uri url){
        try{startActivity(new Intent(Intent.ACTION_VIEW,url).addCategory(Intent.CATEGORY_BROWSABLE));}
        catch(Exception e){android.widget.Toast.makeText(this,"No external browser available.",android.widget.Toast.LENGTH_LONG).show();}
    }
    public final class AuthBridge{
        @JavascriptInterface public void openAuth(String url){
            Uri u=Uri.parse(url);
            if(!"https".equals(u.getScheme())||!projectHost().equals(u.getHost())||u.getPort()!=-1||!"/auth/v1/authorize".equals(u.getPath())||!"google".equals(u.getQueryParameter("provider"))||!"app.aiworkspace.mobile://auth-callback".equals(u.getQueryParameter("redirect_to")))return;
            runOnUiThread(()->openExternal(u));
        }
    }
    private void acceptCallback(Intent i){
        Uri u=i.getData();
        if(u!=null&&"app.aiworkspace.mobile".equals(u.getScheme())&&"auth-callback".equals(u.getHost())&&(u.getPath()==null||u.getPath().isEmpty())&&u.toString().length()<=4096)pendingCallback=u.toString();
    }
    private void dispatchCallback(){
        if(loaded&&pendingCallback!=null){String value=pendingCallback;pendingCallback=null;web.evaluateJavascript("window.MPAuthCallback && window.MPAuthCallback("+JSONObject.quote(value)+")",null);}
    }
    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);acceptCallback(intent);dispatchCallback();}
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request==FILE_REQUEST&&chooser!=null){
            Uri uri=result==RESULT_OK&&data!=null?data.getData():null;
            chooser.onReceiveValue(uri!=null&&"content".equals(uri.getScheme())?new Uri[]{uri}:null);chooser=null;
        }
    }
    @Override protected void onDestroy(){if(chooser!=null)chooser.onReceiveValue(null);if(web!=null){web.removeJavascriptInterface("MedPredictNative");web.destroy();}super.onDestroy();}
}
