package com.memorize.anki;

import android.app.Activity;
import android.content.ClipData;
import android.content.Context;
import android.content.Intent;
import android.content.res.Configuration;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Looper;
import android.view.InputDevice;
import android.view.KeyCharacterMap;
import android.view.KeyEvent;
import android.view.Window;
import android.view.WindowManager;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.InputMethodManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class MainActivity extends Activity {
    private static final int FILE_CHOOSER_REQUEST = 4107;
    private static final int BACKUP_OPEN_REQUEST = 4108;
    private static final int BACKUP_SAVE_REQUEST = 4109;
    private static final int MAX_BACKUP_BYTES = 16 * 1024 * 1024;
    private static final int SPECIAL_KEY_NONE = 0;
    private static final int SPECIAL_KEY_SPACE = 1;
    private static final int SPECIAL_KEY_TAB = 2;
    private WebView webView;
    private ValueCallback<Uri[]> fileCallback;
    private String pendingFileContent;
    private String pendingFileName;
    private volatile boolean cardEditorFocused;
    private volatile boolean managedTextInputFocused;
    private volatile boolean strictPhysicalJsMode;
    private long physicalSpaceDownTime = -1L;
    private long physicalTabDownTime = -1L;
    private volatile int pendingDeadAccent;
    private final Object printableKeyLock = new Object();
    private final Set<String> handledPrintableKeyGestures = new HashSet<>();
    private final Map<String, String> lastPrintableDownEventByGesture = new HashMap<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window window = getWindow();
        window.setStatusBarColor(Color.rgb(245, 247, 242));
        window.setNavigationBarColor(Color.rgb(245, 247, 242));
        window.getDecorView().setSystemUiVisibility(
            android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR |
            android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
        );

        webView = new KeyboardAwareWebView(this);
        setContentView(webView);
        setWindowSoftInputPolicy(hasHardwareKeyboardConnected());

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setDefaultTextEncodingName("UTF-8");
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);

        webView.clearCache(true);
        webView.addJavascriptInterface(new AndroidFileBridge(), "AndroidFileBridge");
        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(
                WebView view,
                ValueCallback<Uri[]> callback,
                FileChooserParams params
            ) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                intent.putExtra(Intent.EXTRA_MIME_TYPES, new String[] {
                    "text/plain", "application/json", "application/octet-stream"
                });
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
                try {
                    startActivityForResult(intent, FILE_CHOOSER_REQUEST);
                    return true;
                } catch (Exception error) {
                    fileCallback = null;
                    return false;
                }
            }
        });

        if (savedInstanceState == null) {
            webView.loadUrl("file:///android_asset/index.html");
        } else {
            webView.restoreState(savedInstanceState);
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == BACKUP_OPEN_REQUEST) {
            if (resultCode == RESULT_OK && data != null && data.getData() != null) {
                readBackup(data.getData());
            }
            return;
        }
        if (requestCode == BACKUP_SAVE_REQUEST) {
            if (resultCode == RESULT_OK && data != null && data.getData() != null) {
                writeBackup(data.getData());
            } else {
                pendingFileContent = null;
                pendingFileName = null;
            }
            return;
        }
        if (requestCode != FILE_CHOOSER_REQUEST || fileCallback == null) return;
        Uri[] result = null;
        if (resultCode == RESULT_OK && data != null) {
            ClipData clipData = data.getClipData();
            if (clipData != null) {
                result = new Uri[clipData.getItemCount()];
                for (int i = 0; i < clipData.getItemCount(); i++) {
                    result[i] = clipData.getItemAt(i).getUri();
                }
            } else if (data.getData() != null) {
                result = new Uri[] { data.getData() };
            }
        }
        fileCallback.onReceiveValue(result);
        fileCallback = null;
    }

    private void readBackup(Uri uri) {
        try (InputStream input = getContentResolver().openInputStream(uri);
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            if (input == null) throw new Exception("无法打开所选文件");
            byte[] buffer = new byte[8192];
            int total = 0;
            int count;
            while ((count = input.read(buffer)) != -1) {
                total += count;
                if (total > MAX_BACKUP_BYTES) throw new Exception("备份文件过大");
                output.write(buffer, 0, count);
            }
            String content = new String(output.toByteArray(), StandardCharsets.UTF_8);
            callJavascript("window.onNativeBackupSelected(" + JSONObject.quote(content) + ");");
        } catch (Exception error) {
            reportFileError(error);
        }
    }

    private void writeBackup(Uri uri) {
        String content = pendingFileContent;
        String fileName = pendingFileName;
        pendingFileContent = null;
        pendingFileName = null;
        if (content == null) {
            reportFileError(new Exception("没有可保存的备份数据"));
            return;
        }
        try (OutputStream output = getContentResolver().openOutputStream(uri, "wt")) {
            if (output == null) throw new Exception("无法创建备份文件");
            output.write(content.getBytes(StandardCharsets.UTF_8));
            output.flush();
            callJavascript("window.onNativeFileSaved(" + JSONObject.quote(fileName) + ");");
        } catch (Exception error) {
            reportFileError(error);
        }
    }

    private void reportFileError(Exception error) {
        String message = error.getMessage() == null ? "无法访问文件" : error.getMessage();
        callJavascript("window.onNativeFileError(" + JSONObject.quote(message) + ");");
    }

    private void callJavascript(final String script) {
        if (webView == null) return;
        if (Looper.myLooper() == Looper.getMainLooper()) {
            webView.evaluateJavascript(script, null);
            return;
        }
        webView.post(new Runnable() {
            @Override
            public void run() {
                if (webView != null) webView.evaluateJavascript(script, null);
            }
        });
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        // The full-card editor is a normal WebView text editor.  Bypass every
        // study-key interception before consulting any possibly stale cloze
        // focus state, so Android/IME owns all of its key events.
        if (cardEditorFocused) return super.dispatchKeyEvent(event);
        if (handleManagedPhysicalText(event)) return true;
        if (handleSpecialKeyboardEvent(event)) return true;
        int keyCode = event.getKeyCode();
        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            String key = null;
            switch (keyCode) {
                case KeyEvent.KEYCODE_DPAD_UP:
                    key = "ArrowUp";
                    break;
                case KeyEvent.KEYCODE_DPAD_DOWN:
                    key = "ArrowDown";
                    break;
                case KeyEvent.KEYCODE_DPAD_LEFT:
                    key = "ArrowLeft";
                    break;
                case KeyEvent.KEYCODE_DPAD_RIGHT:
                    key = "ArrowRight";
                    break;
                default:
                    break;
            }
            if (key != null) {
                callJavascript("window.handleNativeStudyKey(" + JSONObject.quote(key) + ");");
                return true;
            }
        }
        return super.dispatchKeyEvent(event);
    }

    private int specialKeyForEvent(KeyEvent event) {
        int keyCode = event.getKeyCode();
        boolean plainKey = !event.isCtrlPressed() && !event.isAltPressed() && !event.isMetaPressed();
        if (keyCode == KeyEvent.KEYCODE_SPACE && plainKey) return SPECIAL_KEY_SPACE;
        if (keyCode == KeyEvent.KEYCODE_TAB) return SPECIAL_KEY_TAB;

        if (event.getAction() == KeyEvent.ACTION_UP) {
            if (physicalSpaceDownTime >= 0L && event.getDownTime() == physicalSpaceDownTime) {
                return SPECIAL_KEY_SPACE;
            }
            if (physicalTabDownTime >= 0L && event.getDownTime() == physicalTabDownTime) {
                return SPECIAL_KEY_TAB;
            }
        }
        if (!plainKey) return SPECIAL_KEY_NONE;

        int unicodeCharacter = event.getUnicodeChar();
        if (unicodeCharacter == ' ') return SPECIAL_KEY_SPACE;
        if (unicodeCharacter == '\t') return SPECIAL_KEY_TAB;

        if (event.getAction() == KeyEvent.ACTION_MULTIPLE) {
            String characters = event.getCharacters();
            if (containsOnly(characters, ' ')) return SPECIAL_KEY_SPACE;
            if (containsOnly(characters, '\t')) return SPECIAL_KEY_TAB;
        }

        if (
            keyCode == KeyEvent.KEYCODE_UNKNOWN &&
            event.isFromSource(InputDevice.SOURCE_KEYBOARD)
        ) {
            int scanCode = event.getScanCode();
            if (scanCode == 57) return SPECIAL_KEY_SPACE;
            if (scanCode == 15) return SPECIAL_KEY_TAB;
        }
        return SPECIAL_KEY_NONE;
    }

    private boolean containsOnly(CharSequence value, char expected) {
        if (value == null || value.length() == 0) return false;
        for (int index = 0; index < value.length(); index++) {
            if (value.charAt(index) != expected) return false;
        }
        return true;
    }

    private int repeatedCharacterCount(KeyEvent event, char expected) {
        String characters = event.getCharacters();
        if (!containsOnly(characters, expected)) return 1;
        return Math.min(32, characters.length());
    }

    private void dispatchNativePhysicalKey(String key, boolean shiftPressed) {
        callJavascript(
            "if(window.handleNativePhysicalKey){window.handleNativePhysicalKey(" +
            JSONObject.quote(key) + "," + (shiftPressed ? "true" : "false") + ");}"
        );
    }

    private boolean isPhysicalKeyboardEvent(KeyEvent event) {
        if (event == null || !event.isFromSource(InputDevice.SOURCE_KEYBOARD)) return false;
        if ((event.getFlags() & KeyEvent.FLAG_SOFT_KEYBOARD) != 0) return false;
        InputDevice device = event.getDevice();
        return device != null &&
            device.isEnabled() &&
            !device.isVirtual() &&
            device.getKeyboardType() != InputDevice.KEYBOARD_TYPE_NONE;
    }

    private String printableGesture(KeyEvent event) {
        return event.getDeviceId() + ":" + event.getKeyCode() + ":" +
            event.getScanCode() + ":" + event.getDownTime();
    }

    private String printableDownSignature(KeyEvent event) {
        return printableGesture(event) + ":" + event.getEventTime() + ":" +
            event.getRepeatCount();
    }

    private boolean isPrintableCodePoint(int codePoint) {
        return Character.isValidCodePoint(codePoint) && !Character.isISOControl(codePoint);
    }

    private boolean isPrintableText(String text) {
        if (text == null || text.length() == 0) return false;
        for (int offset = 0; offset < text.length();) {
            int codePoint = text.codePointAt(offset);
            if (!isPrintableCodePoint(codePoint)) return false;
            offset += Character.charCount(codePoint);
        }
        return true;
    }

    private boolean printableGestureWasHandled(String gesture) {
        synchronized (printableKeyLock) {
            return handledPrintableKeyGestures.contains(gesture);
        }
    }

    private boolean claimPrintableDown(KeyEvent event) {
        String gesture = printableGesture(event);
        String signature = printableDownSignature(event);
        synchronized (printableKeyLock) {
            if (signature.equals(lastPrintableDownEventByGesture.get(gesture))) return false;
            handledPrintableKeyGestures.add(gesture);
            lastPrintableDownEventByGesture.put(gesture, signature);
            return true;
        }
    }

    private boolean consumePrintableUp(KeyEvent event) {
        String gesture = printableGesture(event);
        synchronized (printableKeyLock) {
            if (!handledPrintableKeyGestures.remove(gesture)) return false;
            lastPrintableDownEventByGesture.remove(gesture);
            return true;
        }
    }

    private String applyPendingDeadAccent(String text) {
        int accent = pendingDeadAccent;
        if (accent == 0 || text == null || text.length() == 0) return text;
        pendingDeadAccent = 0;
        int base = text.codePointAt(0);
        int combined = KeyCharacterMap.getDeadChar(accent, base);
        String remainder = text.substring(Character.charCount(base));
        if (combined != 0) return new String(Character.toChars(combined)) + remainder;
        return new String(Character.toChars(accent)) + text;
    }

    private void dispatchNativePrintableText(String text) {
        callJavascript(
            "if(window.handleNativePrintableText){window.handleNativePrintableText(" +
            JSONObject.quote(text) + ");}"
        );
    }

    private void setStrictPhysicalJsMode(final boolean enabled) {
        if (strictPhysicalJsMode == enabled) return;
        strictPhysicalJsMode = enabled;
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (webView == null) return;
                InputMethodManager manager =
                    (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
                if (manager != null) manager.restartInput(webView);
            }
        });
    }

    private boolean handleManagedPhysicalText(KeyEvent event) {
        if (event == null) return false;
        if (cardEditorFocused) return false;
        int action = event.getAction();
        String gesture = printableGesture(event);

        // A key-up belongs to the same owner as its consumed key-down, even if
        // entering the character completed a card and changed focus meanwhile.
        if (action == KeyEvent.ACTION_UP) return consumePrintableUp(event);

        boolean ownedGesture = printableGestureWasHandled(gesture);
        if (!managedTextInputFocused || !isPhysicalKeyboardEvent(event)) {
            return ownedGesture;
        }
        if (event.isMetaPressed() || (event.isCtrlPressed() && !event.isAltPressed())) {
            return false;
        }

        if (action == KeyEvent.ACTION_MULTIPLE) {
            String characters = event.getCharacters();
            if (!isPrintableText(characters)) return false;
            dispatchNativePrintableText(applyPendingDeadAccent(characters));
            return true;
        }
        if (action != KeyEvent.ACTION_DOWN) return false;

        if (pendingDeadAccent != 0 && event.getKeyCode() == KeyEvent.KEYCODE_DEL) {
            if (!claimPrintableDown(event)) return true;
            pendingDeadAccent = 0;
            return true;
        }

        int unicode = event.getUnicodeChar(event.getMetaState());
        boolean combiningAccent = (unicode & KeyCharacterMap.COMBINING_ACCENT) != 0;
        int codePoint = combiningAccent
            ? unicode & KeyCharacterMap.COMBINING_ACCENT_MASK
            : unicode;
        if (!isPrintableCodePoint(codePoint)) return false;
        if (!claimPrintableDown(event)) return true;

        if (combiningAccent) {
            int previousAccent = pendingDeadAccent;
            pendingDeadAccent = codePoint;
            if (previousAccent != 0) {
                dispatchNativePrintableText(new String(Character.toChars(previousAccent)));
            }
            return true;
        }

        String text = new String(Character.toChars(codePoint));
        dispatchNativePrintableText(applyPendingDeadAccent(text));
        return true;
    }

    private boolean handleSpecialKeyboardEvent(KeyEvent event) {
        if (event == null) return false;
        int specialKey = specialKeyForEvent(event);
        if (specialKey == SPECIAL_KEY_NONE) return false;
        // Soft-keyboard text remains on WebView's native input path. Physical
        // printable keys have already been handled above by one unified path.
        if (specialKey == SPECIAL_KEY_SPACE && (managedTextInputFocused || cardEditorFocused)) {
            return false;
        }
        if (specialKey == SPECIAL_KEY_TAB && cardEditorFocused) return false;

        int action = event.getAction();
        if (action == KeyEvent.ACTION_DOWN) {
            if (specialKey == SPECIAL_KEY_SPACE) {
                physicalSpaceDownTime = event.getDownTime();
                dispatchNativePhysicalKey("Space", event.isShiftPressed());
            } else {
                boolean firstDown = physicalTabDownTime != event.getDownTime();
                physicalTabDownTime = event.getDownTime();
                if (firstDown) dispatchNativePhysicalKey("Tab", false);
            }
            return true;
        }
        if (action == KeyEvent.ACTION_UP) {
            if (specialKey == SPECIAL_KEY_SPACE) {
                boolean downWasHandled = physicalSpaceDownTime >= 0L &&
                    physicalSpaceDownTime == event.getDownTime();
                physicalSpaceDownTime = -1L;
                if (!downWasHandled) dispatchNativePhysicalKey("Space", event.isShiftPressed());
            }
            if (specialKey == SPECIAL_KEY_TAB) {
                boolean downWasHandled = physicalTabDownTime >= 0L &&
                    physicalTabDownTime == event.getDownTime();
                physicalTabDownTime = -1L;
                if (!downWasHandled) dispatchNativePhysicalKey("Tab", false);
            }
            return true;
        }
        if (action == KeyEvent.ACTION_MULTIPLE) {
            if (specialKey == SPECIAL_KEY_SPACE) {
                int count = repeatedCharacterCount(event, ' ');
                for (int index = 0; index < count; index++) {
                    dispatchNativePhysicalKey("Space", event.isShiftPressed());
                }
            } else {
                dispatchNativePhysicalKey("Tab", false);
            }
            return true;
        }
        return false;
    }

    private final class KeyboardAwareWebView extends WebView {
        KeyboardAwareWebView(Context context) {
            super(context);
        }

        @Override
        public boolean dispatchKeyEvent(KeyEvent event) {
            if (cardEditorFocused) return super.dispatchKeyEvent(event);
            if (handleManagedPhysicalText(event)) return true;
            if (handleSpecialKeyboardEvent(event)) return true;
            return super.dispatchKeyEvent(event);
        }

        @Override
        public boolean dispatchKeyEventPreIme(KeyEvent event) {
            if (cardEditorFocused) return super.dispatchKeyEventPreIme(event);
            if (handleManagedPhysicalText(event)) return true;
            if (handleSpecialKeyboardEvent(event)) return true;
            return super.dispatchKeyEventPreIme(event);
        }

        @Override
        public boolean onCheckIsTextEditor() {
            return !strictPhysicalJsMode && super.onCheckIsTextEditor();
        }

        @Override
        public InputConnection onCreateInputConnection(EditorInfo outAttrs) {
            if (strictPhysicalJsMode) return null;
            return super.onCreateInputConnection(outAttrs);
        }
    }

    @Override
    protected void onPause() {
        physicalSpaceDownTime = -1L;
        physicalTabDownTime = -1L;
        pendingDeadAccent = 0;
        synchronized (printableKeyLock) {
            handledPrintableKeyGestures.clear();
            lastPrintableDownEventByGesture.clear();
        }
        super.onPause();
    }

    private boolean hasHardwareKeyboardConnected() {
        Configuration configuration = getResources().getConfiguration();
        if (
            configuration.keyboard != Configuration.KEYBOARD_NOKEYS &&
            configuration.hardKeyboardHidden == Configuration.HARDKEYBOARDHIDDEN_NO
        ) return true;

        int[] deviceIds = InputDevice.getDeviceIds();
        for (int deviceId : deviceIds) {
            InputDevice device = InputDevice.getDevice(deviceId);
            if (
                device != null &&
                device.isEnabled() &&
                !device.isVirtual() &&
                device.getKeyboardType() == InputDevice.KEYBOARD_TYPE_ALPHABETIC
            ) return true;
        }
        return false;
    }

    private void hideSoftKeyboard() {
        if (webView == null || webView.getWindowToken() == null) return;
        InputMethodManager manager = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
        if (manager != null) manager.hideSoftInputFromWindow(webView.getWindowToken(), 0);
    }

    private void suppressSoftKeyboardForHardwareKeyboard() {
        if (!hasHardwareKeyboardConnected()) return;
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (webView == null || !hasHardwareKeyboardConnected()) return;
                setWindowSoftInputPolicy(true);
                hideSoftKeyboard();
                int[] delays = new int[] { 80, 240, 500 };
                for (int delay : delays) {
                    webView.postDelayed(new Runnable() {
                        @Override
                        public void run() {
                            if (webView != null && hasHardwareKeyboardConnected()) hideSoftKeyboard();
                        }
                    }, delay);
                }
            }
        });
    }

    private void setWindowSoftInputPolicy(boolean hardwareKeyboardConnected) {
        int state = hardwareKeyboardConnected
            ? WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN
            : WindowManager.LayoutParams.SOFT_INPUT_STATE_UNSPECIFIED;
        getWindow().setSoftInputMode(state | WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
    }

    private void focusCardEditorWithoutSoftKeyboard() {
        cardEditorFocused = true;
        managedTextInputFocused = false;
        pendingDeadAccent = 0;
        setStrictPhysicalJsMode(false);
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (webView == null) return;
                webView.evaluateJavascript(
                    "(function(){var input=document.getElementById('card-editor-textarea');" +
                    "if(input){input.setAttribute('inputmode','text');input.focus();}})();",
                    null
                );
                suppressSoftKeyboardForHardwareKeyboard();
            }
        });
    }

    @Override
    public void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        final boolean connected = hasHardwareKeyboardConnected();
        setStrictPhysicalJsMode(connected && managedTextInputFocused);
        setWindowSoftInputPolicy(connected);
        if (connected) suppressSoftKeyboardForHardwareKeyboard();
        callJavascript(
            "if(window.onNativeHardwareKeyboardChanged){window.onNativeHardwareKeyboardChanged(" +
            (connected ? "true" : "false") + ");}"
        );
    }

    @Override
    public void onBackPressed() {
        if (webView == null) {
            finishFromSystemBack();
            return;
        }
        webView.evaluateJavascript(
            "(function(){return window.handleNativeBack ? window.handleNativeBack() : false;})()",
            new ValueCallback<String>() {
                @Override
                public void onReceiveValue(String value) {
                    if (!"true".equals(value)) finishFromSystemBack();
                }
            }
        );
    }

    private void finishFromSystemBack() {
        super.onBackPressed();
    }

    public final class AndroidFileBridge {
        @JavascriptInterface
        public boolean hasHardwareKeyboard() {
            return hasHardwareKeyboardConnected();
        }

        @JavascriptInterface
        public void focusCardEditorWithHardwareKeyboard() {
            focusCardEditorWithoutSoftKeyboard();
        }

        @JavascriptInterface
        public void hideSoftKeyboardIfHardwareKeyboard() {
            suppressSoftKeyboardForHardwareKeyboard();
        }

        @JavascriptInterface
        public void setCardEditorFocused(final boolean focused) {
            cardEditorFocused = focused;
            if (focused) {
                managedTextInputFocused = false;
                pendingDeadAccent = 0;
                setStrictPhysicalJsMode(false);
                suppressSoftKeyboardForHardwareKeyboard();
            }
        }

        @JavascriptInterface
        public void setManagedTextInputFocused(final boolean focused) {
            // A delayed cloze focus notification must never re-enable the
            // JavaScript key path while the ordinary card editor owns focus.
            boolean effectiveFocus = focused && !cardEditorFocused;
            managedTextInputFocused = effectiveFocus;
            if (!effectiveFocus) pendingDeadAccent = 0;
            setStrictPhysicalJsMode(effectiveFocus && hasHardwareKeyboardConnected());
            if (effectiveFocus) suppressSoftKeyboardForHardwareKeyboard();
        }

        @JavascriptInterface
        public void openBackup() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    intent.setType("*/*");
                    intent.putExtra(Intent.EXTRA_MIME_TYPES, new String[] {
                        "application/json", "application/octet-stream", "text/plain"
                    });
                    try {
                        startActivityForResult(intent, BACKUP_OPEN_REQUEST);
                    } catch (Exception error) {
                        reportFileError(error);
                    }
                }
            });
        }

        @JavascriptInterface
        public void saveBackup(final String fileName, final String content) {
            saveTextFile(fileName, "application/json", content);
        }

        @JavascriptInterface
        public void saveTextFile(final String fileName, final String mimeType, final String content) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    pendingFileContent = content;
                    pendingFileName = fileName;
                    Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    intent.setType(mimeType == null || mimeType.isEmpty() ? "application/octet-stream" : mimeType);
                    intent.putExtra(Intent.EXTRA_TITLE, fileName);
                    try {
                        startActivityForResult(intent, BACKUP_SAVE_REQUEST);
                    } catch (Exception error) {
                        pendingFileContent = null;
                        pendingFileName = null;
                        reportFileError(error);
                    }
                }
            });
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        webView.saveState(outState);
        super.onSaveInstanceState(outState);
    }

    @Override
    protected void onDestroy() {
        if (fileCallback != null) fileCallback.onReceiveValue(null);
        pendingFileContent = null;
        pendingFileName = null;
        cardEditorFocused = false;
        physicalSpaceDownTime = -1L;
        physicalTabDownTime = -1L;
        if (webView != null) {
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }
}
