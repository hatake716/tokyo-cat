package io.github.hatake716.tokyocat;

import android.annotation.SuppressLint;
import android.content.ContentValues;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.util.Base64;
import android.util.Log;
import android.webkit.*;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import androidx.webkit.WebViewAssetLoader;
import androidx.activity.ComponentActivity;
import androidx.activity.OnBackPressedCallback;
import org.json.JSONObject;
import java.io.ByteArrayInputStream;
import java.io.OutputStream;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;

/** Only packaged UI receives the bridge. Remote resources are data, never executable pages. */
public class MainActivity extends ComponentActivity {
    public WebView webView;
    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private static final String ORIGIN = "https://appassets.androidplatform.net";

    @SuppressLint("SetJavaScriptEnabled")
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().getDecorView();
        webView = new WebView(this);
        WebSettings s = webView.getSettings();
        configureWebView(s);
    }
    private void hideSystemBars() {
        if (android.os.Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
            WindowInsetsController controller = getWindow().getInsetsController();
            if (controller != null) {
                controller.hide(WindowInsets.Type.systemBars());
                controller.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        } else getWindow().getDecorView().setSystemUiVisibility(5894);
    }
    @Override public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemBars();
    }
    @SuppressLint("SetJavaScriptEnabled")
    private void configureWebView(WebSettings s) {
        s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false); s.setAllowContentAccess(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setMediaPlaybackRequiresUserGesture(true);
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);
        final WebViewAssetLoader assets = new WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this)).build();
        webView.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                WebResourceResponse response = assets.shouldInterceptRequest(request.getUrl());
                if (response != null) return response;
                if ("appassets.androidplatform.net".equals(request.getUrl().getHost()))
                    return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found", java.util.Map.of(), new ByteArrayInputStream(new byte[0]));
                return null;
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri u = request.getUrl();
                if ((ORIGIN + "/assets/game/index.html").equals(u.toString())) return false;
                if (request.hasGesture() && "https".equals(u.getScheme())) {
                    try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception e) { Log.w("TokyoCat", "No browser", e); }
                }
                return true;
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onConsoleMessage(ConsoleMessage m) {
                if (BuildConfig.DEBUG) Log.d("TokyoCatWeb", m.messageLevel()+": "+m.message()+" @"+m.lineNumber());
                return true;
            }
        });
        webView.addJavascriptInterface(new PhotoBridge(), "TokyoCatAndroid");
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override public void handleOnBackPressed() { webView.evaluateJavascript("window.handleBack?.()", null); }
        });
        setContentView(webView);
        hideSystemBars();
        webView.loadUrl(ORIGIN + "/assets/game/index.html");
    }
    private class PhotoBridge {
        @JavascriptInterface public void exportPhoto(String requestId, String encoded) {
            if (!requestId.matches("[a-zA-Z0-9-]{1,64}") || encoded.length() > 12_000_000) return;
            io.execute(() -> {
                Uri uri = null;
                try {
                    byte[] bytes = Base64.decode(encoded, Base64.DEFAULT);
                    BitmapFactory.Options bounds = new BitmapFactory.Options(); bounds.inJustDecodeBounds = true;
                    BitmapFactory.decodeByteArray(bytes, 0, bytes.length, bounds);
                    if (bounds.outWidth < 1 || bounds.outHeight < 1 || (long)bounds.outWidth * bounds.outHeight > 16_000_000) throw new IllegalArgumentException("Image size");
                    Bitmap bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.length);
                    if (bitmap == null) throw new IllegalArgumentException("Image data");
                    ContentValues values = new ContentValues();
                    values.put(MediaStore.Images.Media.DISPLAY_NAME, "TOKYO-CAT-"+System.currentTimeMillis()+".jpg");
                    values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
                    values.put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/TOKYO-CAT");
                    values.put(MediaStore.Images.Media.IS_PENDING, 1);
                    uri = getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values);
                    if (uri == null) throw new IllegalStateException("MediaStore unavailable");
                    try (OutputStream out = getContentResolver().openOutputStream(uri)) {
                        if (out == null || !bitmap.compress(Bitmap.CompressFormat.JPEG, 94, out)) throw new IllegalStateException("Write failed");
                    } finally { bitmap.recycle(); }
                    ContentValues done = new ContentValues(); done.put(MediaStore.Images.Media.IS_PENDING, 0);
                    getContentResolver().update(uri, done, null, null);
                    result(requestId, true);
                } catch (Exception e) {
                    if (uri != null) getContentResolver().delete(uri, null, null);
                    Log.w("TokyoCat", "Photo export failed", e); result(requestId, false);
                }
            });
        }
    }
    private void result(String id, boolean ok) {
        runOnUiThread(() -> { if (!isDestroyed()) webView.evaluateJavascript("window.onPhotoExport?.("+JSONObject.quote(id)+","+ok+")", null); });
    }
    @Override protected void onPause() { webView.evaluateJavascript("window.pauseGame?.()", null); webView.onPause(); super.onPause(); }
    @Override protected void onResume() { super.onResume(); if (webView != null) webView.onResume(); }
    @Override protected void onDestroy() { io.shutdown(); webView.removeJavascriptInterface("TokyoCatAndroid"); webView.destroy(); super.onDestroy(); }
}
