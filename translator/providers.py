import eng_to_ipa
import httpx
from pypinyin import lazy_pinyin, Style
from pykakasi import kakasi
from unidecode import unidecode

from .core import TranslationError


class GoogleWebProvider:
    """Public web endpoint adapter, replaceable with an official API provider."""
    def translate(self, text: str, target: str) -> tuple[str, str]:
        try:
            response = httpx.get(
                'https://translate.googleapis.com/translate_a/single',
                params=[('client', 'gtx'), ('sl', 'ko'), ('tl', target),
                        ('dt', 't'), ('dt', 'rm'), ('q', text)],
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            segments = data[0]
            translated = ''.join(s[0] for s in segments if s and isinstance(s[0], str))
            phonetic = ' '.join(s[3] for s in segments if len(s) > 3 and isinstance(s[3], str))
            if not translated:
                raise ValueError('Empty translation')
            return translated, phonetic
        except (httpx.HTTPError, ValueError, TypeError, IndexError) as error:
            raise TranslationError('번역 서버에 연결하지 못했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.') from error


class RomanizationProvider:
    def __init__(self):
        self._japanese = kakasi()

    def pronounce(self, text: str, language: str) -> tuple[str, str]:
        if language == 'zh-CN':
            return ' '.join(lazy_pinyin(text, style=Style.TONE)), '중국어 병음입니다. 문맥에 따라 읽기가 달라질 수 있습니다.'
        if language == 'ja':
            return ' '.join(item['hepburn'] for item in self._japanese.convert(text)), '일본어 로마자 표기입니다. 고유명사 읽기는 다를 수 있습니다.'
        if language == 'en':
            return eng_to_ipa.convert(text), '영어 국제음성기호(IPA)입니다. * 표시는 사전에 없는 단어입니다.'
        return unidecode(text), '간이 로마자 표기입니다. 실제 발음·성조와 차이가 있을 수 있습니다.'
