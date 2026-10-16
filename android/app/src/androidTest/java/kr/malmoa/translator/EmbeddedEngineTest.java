package kr.malmoa.translator;

import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Test;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import com.chaquo.python.PyObject;
import org.json.JSONObject;

@RunWith(AndroidJUnit4.class)
public class EmbeddedEngineTest {
    private Python python() {
        synchronized (Python.class) {
            if (!Python.isStarted()) Python.start(new AndroidPlatform(
                    InstrumentationRegistry.getInstrumentation().getTargetContext()));
        }
        return Python.getInstance();
    }
    @Test public void testAllSixBundledPronunciationDictionaries() {
        PyObject engine = python().getModule("android_bridge").callAttr("create_pronunciation_provider");
        String[] codes = {"zh-CN", "ja", "en", "th", "lo", "ru"};
        String[] samples = {"你好", "こんにちは", "hello", "สวัสดี", "ສະບາຍດີ", "Привет"};
        for (int i = 0; i < codes.length; i++) {
            String reading = engine.callAttr("pronounce", samples[i], codes[i]).asList().get(0).toString();
            assertTrue(codes[i] + ": " + reading, reading.matches(".*[가-힣].*"));
        }
    }
    @Test public void testEmptyInputReturnsUserError() throws Exception {
        JSONObject result = new JSONObject(python().getModule("android_bridge")
                .callAttr("translate", "", "en").toString());
        assertFalse(result.getBoolean("ok"));
        assertTrue(result.getString("error").contains("입력"));
    }
    @Test public void testScreenRejectsBlankInput() {
        android.app.Instrumentation instrumentation = InstrumentationRegistry.getInstrumentation();
        android.content.Intent intent = new android.content.Intent(instrumentation.getTargetContext(), MainActivity.class);
        intent.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
        MainActivity activity = (MainActivity) instrumentation.startActivitySync(intent);
        try {
            instrumentation.runOnMainSync(() -> {
                android.widget.EditText input = activity.findViewById(R.id.source_input);
                input.setText("   ");
                activity.findViewById(R.id.translate_button).performClick();
                assertNotNull(input.getError());
                assertTrue(input.getError().toString().contains("입력"));
            });
        } finally {
            instrumentation.runOnMainSync(activity::finish);
        }
    }
}
