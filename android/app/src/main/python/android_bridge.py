"""JSON interface between native Android and the shared translation engine."""
from functools import lru_cache
import json
from pathlib import Path

from translator.core import LANGUAGES, TranslationError, Translator
from translator.pronunciation import KoreanPronunciationProvider
from translator.providers import FallbackTranslationProvider, GoogleWebProvider, MyMemoryProvider


def create_pronunciation_provider():
    # pykakasi assumes resources.files() is os.PathLike; Chaquopy's AssetPath
    # is a Traversable. Bundled data is extracted relative to __file__.
    import pykakasi.properties
    pykakasi.properties.Configurations.data_path = str(
        Path(pykakasi.properties.__file__).parent / 'data'
    )
    return KoreanPronunciationProvider()


@lru_cache(maxsize=1)
def _get_translator():
    return Translator(FallbackTranslationProvider([GoogleWebProvider(), MyMemoryProvider()]),
                      create_pronunciation_provider())


def translate(text, code):
    try:
        language = next((item for item in LANGUAGES if item.code == code), None)
        if language is None:
            raise TranslationError('지원하지 않는 언어입니다.')
        result = _get_translator().translate(text, language)
        payload = dict(ok=True, text=result.text, pronunciation=result.pronunciation,
                       note=result.pronunciation_note)
    except TranslationError as error:
        message = str(error).replace('Windows의 프록시 설정', '휴대폰의 네트워크 설정').replace('PC 날짜', '휴대폰 날짜')
        payload = dict(ok=False, error=message)
    except Exception:
        payload = dict(ok=False, error='번역을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.')
    return json.dumps(payload, ensure_ascii=False)
