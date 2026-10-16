import importlib.util
import json
from pathlib import Path
import pytest
from translator.core import TranslationError, Translator
from translator.pronunciation import KoreanPronunciationProvider

path = Path(__file__).parents[1] / 'android/app/src/main/python/android_bridge.py'
spec = importlib.util.spec_from_file_location('android_bridge', path)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


@pytest.mark.parametrize('code,text', [
    ('zh-CN', '你好'), ('ja', 'こんにちは'), ('en', 'hello'),
    ('th', 'สวัสดี'), ('lo', 'ສະບາຍດີ'), ('ru', 'Привет'),
])
def test_android_json_keeps_translation_and_hangul(monkeypatch, code, text):
    class Provider:
        def translate(self, source, target):
            assert source == '안녕하세요'
            assert target == code
            return text, ''
    monkeypatch.setattr(bridge, '_get_translator', lambda: Translator(Provider(), KoreanPronunciationProvider()))
    result = json.loads(bridge.translate(' 안녕하세요 ', code))
    assert result['ok'] is True
    assert result['text'] == text
    assert any('가' <= char <= '힣' for char in result['pronunciation'])
    assert result['note']


@pytest.mark.parametrize('text,code,message', [
    ('', 'en', '입력'), ('a' * 3001, 'en', '3,000'), ('안녕', 'xx', '지원하지'),
])
def test_android_validation_does_not_call_network(monkeypatch, text, code, message):
    class Provider:
        def translate(self, *_):
            pytest.fail('Invalid input must not reach the network')
    monkeypatch.setattr(bridge, '_get_translator', lambda: Translator(Provider(), KoreanPronunciationProvider()))
    result = json.loads(bridge.translate(text, code))
    assert result['ok'] is False
    assert message in result['error']
    assert 'text' not in result


def test_android_unexpected_error_does_not_expose_details(monkeypatch):
    def fail():
        raise RuntimeError('private input / credentials / https://internal.example')
    monkeypatch.setattr(bridge, '_get_translator', fail)
    result = json.loads(bridge.translate('안녕', 'en'))
    assert result['ok'] is False
    assert 'private' not in result['error']
    assert 'internal' not in result['error']


def test_android_service_failure_has_no_stale_result(monkeypatch):
    class Broken:
        def translate(self, *_):
            raise TranslationError('번역 서버에 연결하지 못했습니다.')
    monkeypatch.setattr(bridge, '_get_translator', lambda: Broken())
    assert json.loads(bridge.translate('안녕', 'en')) == {
        'ok': False, 'error': '번역 서버에 연결하지 못했습니다.'}


def test_android_dictionary_reader_accepts_non_filesystem_resource_loader(monkeypatch):
    import pykakasi.properties
    monkeypatch.setattr(pykakasi.properties.Configurations, 'data_path', object())
    provider = bridge.create_pronunciation_provider()
    assert Path(pykakasi.properties.Configurations.dictpath('kanwadict4.db')).is_file()
    assert provider.pronounce('こんにちは', 'ja')[0] == '콘니치와'
