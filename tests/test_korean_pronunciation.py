import re
import pytest
from translator.core import LANGUAGES, Translator
from translator.pronunciation import KoreanPronunciationProvider


@pytest.mark.parametrize('language,text,expected', [
    ('zh-CN', '你好', '니 하오'),
    ('zh-CN', '谢谢', '셰 셰'),
    ('ja', 'こんにちは', '콘니치와'),
    ('th', 'สวัสดี', '싸왓디'),
    ('lo', 'ສະບາຍດີ', '싸바이디'),
    ('ru', 'Привет', '프리벳'),
    ('ru', 'Спасибо', '스파시바'),
])
def test_familiar_readings(language, text, expected):
    reading, note = KoreanPronunciationProvider().pronounce(text, language)
    assert reading == expected
    assert '근사' in note


@pytest.mark.parametrize('language,text', [
    ('zh-CN', '很高兴见到你。'), ('ja', 'ありがとうございます。'),
    ('en', 'Hello, nice to meet you.'), ('th', 'ยินดีที่ได้รู้จัก'),
    ('lo', 'ຍິນດີທີ່ໄດ້ພົບເຈົ້າ'), ('ru', 'Рад встрече.'),
])
def test_supported_sentences_are_readable_in_hangul(language, text):
    reading, _ = KoreanPronunciationProvider().pronounce(text, language)
    assert re.search('[가-힣]', reading)
    assert not re.search('[A-Za-zА-Яа-я\u0e00-\u0eff\u3040-\u30ff\u4e00-\u9fff]', reading)


def test_english_uses_sound_dictionary_not_letter_spelling():
    reading, _ = KoreanPronunciationProvider().pronounce('nice to meet you', 'en')
    assert reading == '나이스 투 미트 유'


def test_translator_does_not_bypass_hangul_for_service_romanization():
    class Provider:
        def translate(self, text, target):
            return '你好', 'nǐ hǎo'
    result = Translator(Provider(), KoreanPronunciationProvider()).translate('안녕', LANGUAGES[0])
    assert result.pronunciation == '니 하오'


def test_japanese_final_su_is_readable_as_su_devoicing():
    assert KoreanPronunciationProvider().pronounce('ありがとうございます', 'ja')[0].endswith('고자이마스')


def test_punctuation_does_not_change_english_word_reading():
    provider = KoreanPronunciationProvider()
    plain = provider.pronounce('meet', 'en')[0]
    punctuated = provider.pronounce('meet.', 'en')[0]
    assert punctuated == plain + '.'
