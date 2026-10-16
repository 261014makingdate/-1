package kr.malmoa.translator;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.text.InputFilter;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.widget.*;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import org.json.JSONObject;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final String[] CODES = {"zh-CN", "ja", "en", "th", "lo", "ru"};
    private static final String[] LANGUAGES = {"중국어", "일본어", "영어", "태국어", "라오스어", "러시아어"};
    private static final int GREEN = Color.rgb(23, 107, 85);
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private EditText input;
    private Spinner language;
    private TextView output, pronunciation, note, status;
    private Button translate, copy, speak;
    private ProgressBar progress;
    private TextToSpeech tts;
    private boolean ttsReady, busy, destroyed;
    private String resultCode = "";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(dp(24), dp(20), dp(24), dp(32));
        scroll.addView(page);
        scroll.setOnApplyWindowInsetsListener((v, insets) -> {
            v.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                    insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets;
        });
        setContentView(scroll);
        TextView brand = text("말모아", 32);
        brand.setTypeface(null, Typeface.BOLD);
        brand.setTextColor(GREEN);
        page.addView(brand);
        page.addView(text("마음을 전하는 쉬운 번역", 16));
        space(page, 24);
        page.addView(label("01  한국어 문장"));
        input = new EditText(this);
        input.setId(R.id.source_input);
        input.setHint("어떤 말을 전하고 싶으세요?");
        input.setTextSize(18);
        input.setGravity(android.view.Gravity.TOP);
        input.setMinLines(4);
        input.setMaxLines(8);
        input.setInputType(android.text.InputType.TYPE_CLASS_TEXT |
                android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE |
                android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        input.setFilters(new InputFilter[]{new InputFilter.LengthFilter(3000)});
        input.setPadding(dp(16), dp(16), dp(16), dp(16));
        input.setBackground(card());
        page.addView(input, full());
        page.addView(text("최대 3,000자 · 번역하려면 인터넷 연결이 필요해요", 12));
        space(page, 20);
        page.addView(label("02  번역할 언어"));
        language = new Spinner(this);
        language.setId(R.id.target_language);
        language.setAdapter(new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_dropdown_item, LANGUAGES));
        language.setBackground(card());
        page.addView(language, new LinearLayout.LayoutParams(-1, dp(56)));
        space(page, 16);
        translate = button("번역하기");
        translate.setId(R.id.translate_button);
        translate.setTextColor(Color.WHITE);
        translate.setBackgroundTintList(android.content.res.ColorStateList.valueOf(GREEN));
        page.addView(translate, full());
        progress = new ProgressBar(this);
        progress.setVisibility(View.GONE);
        page.addView(progress, new LinearLayout.LayoutParams(-1, dp(40)));
        status = text("", 14);
        status.setTextColor(Color.rgb(156, 47, 47));
        status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        page.addView(status);
        space(page, 12);
        page.addView(label("번역 결과"));
        output = text("번역한 문장이 여기에 표시돼요", 24);
        output.setTextIsSelectable(true);
        output.setPadding(dp(16), dp(20), dp(16), dp(20));
        output.setBackground(card());
        page.addView(output, full());
        space(page, 16);
        page.addView(label("한글로 읽기"));
        pronunciation = text("", 21);
        pronunciation.setTextColor(GREEN);
        pronunciation.setTextIsSelectable(true);
        page.addView(pronunciation, full());
        note = text("한글 발음은 실제 소리와 차이가 있는 근사 표기예요.", 12);
        page.addView(note);
        LinearLayout actions = new LinearLayout(this);
        copy = button("번역문 복사");
        speak = button("발음 듣기");
        actions.addView(copy, new LinearLayout.LayoutParams(0, dp(56), 1));
        actions.addView(speak, new LinearLayout.LayoutParams(0, dp(56), 1));
        page.addView(actions);
        space(page, 24);
        page.addView(text("입력 문장은 번역을 위해 Google 또는 MyMemory로 전송됩니다. " +
                "무료 서비스의 이용 제한으로 번역이 지연되거나 실패할 수 있어요. " +
                "발음 듣기는 휴대폰의 음성 엔진을 사용하며, 엔진 설정에 따라 텍스트가 전송될 수 있어요. " +
                "앱은 번역 내용을 별도로 저장하지 않습니다.", 12));
        clearResult();
        if (state != null) {
            input.setText(state.getString("input", ""));
            language.setSelection(state.getInt("language", 0));
            resultCode = state.getString("resultCode", "");
            if (!resultCode.isEmpty()) {
                output.setText(state.getString("output", ""));
                pronunciation.setText(state.getString("pronunciation", ""));
                note.setText(state.getString("note", ""));
                copy.setEnabled(true);
            }
        }
        translate.setOnClickListener(v -> startTranslation());
        copy.setOnClickListener(v -> {
            ((ClipboardManager) getSystemService(CLIPBOARD_SERVICE))
                    .setPrimaryClip(ClipData.newPlainText("말모아 번역", output.getText()));
            Toast.makeText(this, "번역문을 복사했어요", Toast.LENGTH_SHORT).show();
        });
        speak.setOnClickListener(v -> readAloud());
        tts = new TextToSpeech(this, code -> runOnUiThread(() -> {
            if (destroyed) return;
            ttsReady = code == TextToSpeech.SUCCESS;
            speak.setEnabled(ttsReady && !resultCode.isEmpty());
        }));
    }

    private void startTranslation() {
        if (busy) return;
        String source = input.getText().toString().trim();
        if (source.isEmpty()) { input.setError("한국어 문장을 입력해 주세요."); return; }
        String code = CODES[language.getSelectedItemPosition()];
        ((InputMethodManager) getSystemService(INPUT_METHOD_SERVICE))
                .hideSoftInputFromWindow(input.getWindowToken(), 0);
        if (tts != null) tts.stop();
        clearResult();
        busy = true;
        translate.setEnabled(false);
        translate.setText("번역 중…");
        input.setEnabled(false);
        language.setEnabled(false);
        progress.setVisibility(View.VISIBLE);
        status.setText("번역하고 있어요. 잠시만 기다려 주세요.");
        worker.execute(() -> {
            JSONObject payload;
            try {
                synchronized (Python.class) {
                    if (!Python.isStarted()) Python.start(new AndroidPlatform(getApplicationContext()));
                }
                payload = new JSONObject(Python.getInstance().getModule("android_bridge")
                        .callAttr("translate", source, code).toString());
            } catch (Exception error) {
                payload = new JSONObject();
                try { payload.put("ok", false).put("error", "번역을 시작하지 못했습니다. 앱을 다시 열어 주세요."); }
                catch (Exception ignored) { }
            }
            final JSONObject response = payload;
            runOnUiThread(() -> {
                if (destroyed) return;
                busy = false;
                translate.setEnabled(true);
                translate.setText("번역하기");
                input.setEnabled(true);
                language.setEnabled(true);
                progress.setVisibility(View.GONE);
                if (response.optBoolean("ok")) {
                    resultCode = code;
                    output.setText(response.optString("text"));
                    pronunciation.setText(response.optString("pronunciation"));
                    note.setText(response.optString("note"));
                    status.setText("");
                    copy.setEnabled(true);
                    speak.setEnabled(ttsReady);
                    output.announceForAccessibility("번역이 완료됐어요. " + output.getText());
                } else {
                    status.setText(response.optString("error", "번역에 실패했습니다. 다시 시도해 주세요."));
                }
            });
        });
    }

    private void readAloud() {
        if (!ttsReady || resultCode.isEmpty()) return;
        int availability = tts.setLanguage(Locale.forLanguageTag(resultCode));
        if (availability == TextToSpeech.LANG_MISSING_DATA || availability == TextToSpeech.LANG_NOT_SUPPORTED) {
            Toast.makeText(this, "휴대폰 음성 엔진에서 이 언어를 지원하지 않아요. 음성 언어 데이터를 확인해 주세요.", Toast.LENGTH_LONG).show();
            return;
        }
        String value = output.getText().toString();
        if (value.length() > TextToSpeech.getMaxSpeechInputLength()) {
            Toast.makeText(this, "문장이 너무 길어요. 짧게 나누어 번역한 뒤 들어 주세요.", Toast.LENGTH_LONG).show();
            return;
        }
        if (tts.speak(value, TextToSpeech.QUEUE_FLUSH, null, "malmoa") == TextToSpeech.ERROR) {
            Toast.makeText(this, "음성을 재생하지 못했어요. 휴대폰 음성 설정을 확인해 주세요.", Toast.LENGTH_LONG).show();
        }
    }

    private void clearResult() {
        resultCode = "";
        output.setText("번역한 문장이 여기에 표시돼요");
        pronunciation.setText("");
        status.setText("");
        copy.setEnabled(false);
        speak.setEnabled(false);
    }
    @Override protected void onSaveInstanceState(Bundle state) {
        super.onSaveInstanceState(state);
        state.putString("input", input.getText().toString());
        state.putInt("language", language.getSelectedItemPosition());
        state.putString("resultCode", resultCode);
        state.putString("output", output.getText().toString());
        state.putString("pronunciation", pronunciation.getText().toString());
        state.putString("note", note.getText().toString());
    }
    @Override protected void onStop() {
        if (tts != null) tts.stop();
        super.onStop();
    }
    @Override protected void onDestroy() {
        destroyed = true;
        worker.shutdownNow();
        if (tts != null) { tts.stop(); tts.shutdown(); }
        super.onDestroy();
    }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private TextView text(String value, int size) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(Color.rgb(45, 59, 53));
        view.setLineSpacing(dp(4), 1);
        return view;
    }
    private TextView label(String value) {
        TextView view = text(value, 14);
        view.setTypeface(null, Typeface.BOLD);
        view.setPadding(0, 0, 0, dp(8));
        return view;
    }
    private Button button(String value) {
        Button button = new Button(this);
        button.setText(value);
        button.setTextSize(16);
        button.setAllCaps(false);
        button.setMinHeight(dp(56));
        return button;
    }
    private GradientDrawable card() {
        GradientDrawable background = new GradientDrawable();
        background.setColor(Color.WHITE);
        background.setCornerRadius(dp(12));
        background.setStroke(dp(1), Color.rgb(215, 225, 218));
        return background;
    }
    private LinearLayout.LayoutParams full() { return new LinearLayout.LayoutParams(-1, -2); }
    private void space(LinearLayout parent, int height) {
        parent.addView(new View(this), new LinearLayout.LayoutParams(1, dp(height)));
    }
}
