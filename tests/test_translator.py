import pytest
import httpx
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop, QTimer
from translator.core import Translator, TranslationError, LANGUAGES
from translator.providers import GoogleWebProvider, RomanizationProvider
from translator.ui import TranslatorWindow


class Provider:
    def translate(self, text, target):
        return '你好', 'nǐ hǎo'


@pytest.mark.parametrize('text', ['', '  ', '가' * 3001])
def test_input_validation(text):
    with pytest.raises(TranslationError):
        Translator(Provider(), RomanizationProvider()).translate(text, LANGUAGES[0])


def test_service_pronunciation_preferred():
    result = Translator(Provider(), RomanizationProvider()).translate('안녕', LANGUAGES[0])
    assert result.text == '你好'
    assert result.pronunciation == 'nǐ hǎo'


@pytest.mark.parametrize('code,text', [('zh-CN', '你好'), ('ja', 'こんにちは'), ('en', 'hello'), ('th', 'สวัสดี'), ('lo', 'ສະບາຍດີ'), ('ru', 'Привет')])
def test_pronunciation_fallback(code, text):
    pronunciation, note = RomanizationProvider().pronounce(text, code)
    assert pronunciation.strip()
    assert note
    assert pronunciation != text


def test_network_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError('offline')
    monkeypatch.setattr(httpx, 'get', fail)
    with pytest.raises(TranslationError):
        GoogleWebProvider().translate('안녕', 'en')


def test_response_parsing(monkeypatch):
    data = [[['Hello', '안녕', None, None], [None, None, 'hello', 'annyeong']]]
    response = httpx.Response(200, json=data, request=httpx.Request('GET', 'https://example.com'))
    monkeypatch.setattr(httpx, 'get', lambda *a, **k: response)
    assert GoogleWebProvider().translate('안녕', 'en') == ('Hello', 'hello')


def test_desktop_translation_flow():
    app = QApplication.instance() or QApplication([])
    window = TranslatorWindow(Translator(Provider(), RomanizationProvider()))
    window.show()
    window.input.setPlainText('안녕')
    window.translate()
    loop = QEventLoop()
    window._thread.finished.connect(loop.quit)
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    app.processEvents()
    assert window.output.toPlainText() == '你好'
    assert window.pronunciation.toPlainText() == 'nǐ hǎo'
    assert window.translate_button.isEnabled()
    window.close()


def test_structured_target_pronunciation(monkeypatch):
    data = {'sentences': [{'trans': 'สวัสดี'}, {'translit': 'sawasdee', 'src_translit': 'annyeong'}]}
    response = httpx.Response(200, json=data, request=httpx.Request('GET', 'https://example.com'))
    monkeypatch.setattr(httpx, 'get', lambda *a, **k: response)
    assert GoogleWebProvider().translate('안녕', 'th') == ('สวัสดี', 'sawasdee')


def test_backup_endpoint(monkeypatch):
    calls = []
    def request(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            raise httpx.ConnectError('network unavailable')
        return httpx.Response(200, json={'sentences': [{'trans': 'Hello'}]}, request=httpx.Request('GET', url))
    monkeypatch.setattr(httpx, 'get', request)
    assert GoogleWebProvider().translate('안녕', 'en') == ('Hello', '')
    assert len(calls) == 2


def test_rate_limit_message(monkeypatch):
    response = httpx.Response(429, request=httpx.Request('GET', 'https://example.com'))
    monkeypatch.setattr(httpx, 'get', lambda *a, **k: response)
    with pytest.raises(TranslationError, match='HTTP 429'):
        GoogleWebProvider().translate('안녕', 'en')


def test_tls_message_without_sensitive_details(monkeypatch):
    def request(*a, **k):
        raise httpx.ConnectError('CERTIFICATE_VERIFY_FAILED secret-user-input')
    monkeypatch.setattr(httpx, 'get', request)
    with pytest.raises(TranslationError, match='TLS') as error:
        GoogleWebProvider().translate('안녕', 'en')
    assert 'secret-user-input' not in str(error.value)


def test_invalid_response_is_not_connectivity_error(monkeypatch):
    response = httpx.Response(200, json={'unexpected': True}, request=httpx.Request('GET', 'https://example.com'))
    monkeypatch.setattr(httpx, 'get', lambda *a, **k: response)
    with pytest.raises(TranslationError, match='RESPONSE'):
        GoogleWebProvider().translate('안녕', 'en')


def test_legacy_null_segments_are_ignored():
    assert GoogleWebProvider._parse([[None, ['Hello'], [None, None, 'hello', 'annyeong']]]) == ('Hello', 'hello')


def test_google_webpage_fallback_after_api_rate_limit(monkeypatch):
    calls = []
    def request(url, **kwargs):
        calls.append(url)
        if url.endswith('/m'):
            return httpx.Response(200, text='<div class="result-container">สวัสดี <span>โลก</span><br>!</div>', request=httpx.Request('GET', url))
        return httpx.Response(429, request=httpx.Request('GET', url))
    monkeypatch.setattr(httpx, 'get', request)
    assert GoogleWebProvider().translate('안녕', 'th') == ('สวัสดี โลก\n!', '')
    assert len(calls) == 2


def test_google_webpage_missing_result_is_rejected(monkeypatch):
    monkeypatch.setattr(GoogleWebProvider, '_ENDPOINTS', ('https://translate.google.com/m',))
    response = httpx.Response(200, text='<html>Service unavailable</html>', request=httpx.Request('GET', 'https://example.com'))
    monkeypatch.setattr(httpx, 'get', lambda *a, **k: response)
    with pytest.raises(TranslationError, match='RESPONSE'):
        GoogleWebProvider().translate('안녕', 'en')


def test_secondary_provider_after_google_failure():
    from translator.providers import FallbackTranslationProvider
    class Failed:
        def translate(self, *args):
            raise TranslationError('HTTP 429')
    assert FallbackTranslationProvider([Failed(), Provider()]).translate('안녕', 'zh-CN') == ('你好', 'nǐ hǎo')


def test_mymemory_result_and_query_limit(monkeypatch):
    from translator.providers import MyMemoryProvider
    calls = []
    def request(url, **kwargs):
        calls.append(kwargs['params']['q'])
        return httpx.Response(200, json={'responseStatus': 200, 'responseData': {'translatedText': 'Hello &amp; welcome'}}, request=httpx.Request('GET', url))
    monkeypatch.setattr(httpx, 'get', request)
    result, phonetic = MyMemoryProvider().translate('가' * 901, 'en')
    assert [len(s) for s in calls] == [450, 450, 1]
    assert result == '\n'.join(['Hello & welcome'] * 3)
    assert phonetic == ''


def test_mymemory_quota_is_not_translation(monkeypatch):
    from translator.providers import MyMemoryProvider
    response = httpx.Response(200, json={'responseStatus': 403, 'quotaFinished': True, 'responseData': {'translatedText': 'MYMEMORY WARNING'}}, request=httpx.Request('GET', 'https://example.com'))
    monkeypatch.setattr(httpx, 'get', lambda *a, **k: response)
    with pytest.raises(TranslationError, match='MYMEMORY LIMIT'):
        MyMemoryProvider().translate('안녕', 'en')


def test_live_diagnostic_assembles_providers(monkeypatch, tmp_path):
    import json
    from translator.diagnostics import run_live
    samples = {'zh-CN': '你好', 'ja': 'こんにちは', 'en': 'hello', 'th': 'สวัสดี', 'lo': 'ສະບາຍດີ', 'ru': 'Привет'}
    monkeypatch.setattr(GoogleWebProvider, 'translate', lambda self, text, target: (samples[target], 'phonetic'))
    report = tmp_path / 'live.json'
    assert run_live(str(report)) == 0
    data = json.loads(report.read_text(encoding='utf-8'))
    assert data['status'] == 'passed'
    assert len(data['checks']) == 6
