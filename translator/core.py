from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Language:
    code: str
    name: str


LANGUAGES = (
    Language('zh-CN', '중국어'), Language('ja', '일본어'),
    Language('en', '영어'), Language('th', '태국어'),
    Language('lo', '라오스어'), Language('ru', '러시아어'),
)


@dataclass(frozen=True)
class Translation:
    text: str
    pronunciation: str
    pronunciation_note: str


class TranslationError(Exception):
    pass


class TranslationProvider(Protocol):
    def translate(self, text: str, target: str) -> tuple[str, str]: ...


class PronunciationProvider(Protocol):
    def pronounce(self, text: str, language: str) -> tuple[str, str]: ...


class Translator:
    def __init__(self, provider: TranslationProvider, pronunciation: PronunciationProvider):
        self._provider = provider
        self._pronunciation = pronunciation

    def translate(self, text: str, language: Language) -> Translation:
        text = text.strip()
        if not text:
            raise TranslationError('한국어 문장을 입력해 주세요.')
        if len(text) > 3000:
            raise TranslationError('한 번에 3,000자 이하로 입력해 주세요.')
        if language not in LANGUAGES:
            raise TranslationError('지원하지 않는 언어입니다.')
        translated, phonetic = self._provider.translate(text, language.code)
        if phonetic:
            return Translation(translated, phonetic, '번역 서비스에서 제공한 로마자 발음입니다.')
        pronunciation, note = self._pronunciation.pronounce(translated, language.code)
        return Translation(translated, pronunciation, note)
