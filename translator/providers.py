import os
from html.parser import HTMLParser
from collections.abc import Sequence
import ssl
from urllib.parse import urlparse
from urllib.request import getproxies, proxy_bypass

import certifi
import eng_to_ipa
import httpx
from pypinyin import lazy_pinyin, Style
from pykakasi import kakasi
from unidecode import unidecode

from .core import TranslationError, TranslationProvider


def _windows_connection_options(host: str) -> dict:
    """Use Windows trust roots and manually configured system proxies."""
    if os.name != 'nt':
        return {}
    import truststore
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(certifi.where())
    # Respect an explicitly configured trusted CA bundle without disabling TLS.
    extra_ca = os.environ.get('SSL_CERT_FILE')
    if extra_ca:
        context.load_verify_locations(extra_ca)
    options = {'verify': context}
    if not proxy_bypass(host):
        proxies = getproxies()
        proxy = proxies.get('https') or proxies.get('http')
        if proxy:
            options['proxy'] = proxy
    return options


class _GoogleResultParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if self.depth:
            if tag == 'br':
                self.parts.append('\n')
            elif tag not in ('img', 'hr', 'input', 'meta', 'link', 'wbr'):
                self.depth += 1
        elif tag == 'div' and 'result-container' in dict(attrs).get('class', '').split():
            self.depth = 1

    def handle_endtag(self, tag):
        if self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)


class GoogleWebProvider:
    """Google web adapter with native Windows trust and a backup endpoint."""
    _ENDPOINTS = (
        'https://translate.googleapis.com/translate_a/single',
        'https://translate.google.com/translate_a/single',
        'https://translate.google.com/m',
    )

    @staticmethod
    def _parse(data) -> tuple[str, str]:
        if isinstance(data, dict):
            sentences = data.get('sentences')
            if not isinstance(sentences, list):
                raise ValueError('Missing sentences')
            translated = ''.join(s['trans'] for s in sentences
                                 if isinstance(s, dict) and isinstance(s.get('trans'), str))
            phonetic = ' '.join(s['translit'] for s in sentences
                                if isinstance(s, dict) and isinstance(s.get('translit'), str))
        elif isinstance(data, list) and data and isinstance(data[0], list):
            # Legacy Google response: target pronunciation is index 2;
            # index 3 is the Korean source pronunciation.
            sentences = [s for s in data[0] if isinstance(s, list)]
            translated = ''.join(s[0] for s in sentences if s and isinstance(s[0], str))
            phonetic = ' '.join(s[2] for s in sentences
                                if len(s) > 2 and isinstance(s[2], str))
        else:
            raise ValueError('Invalid translation response')
        if not translated.strip():
            raise ValueError('Empty translation')
        return translated, phonetic

    @staticmethod
    def _failure(error: Exception) -> str:
        if isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code
            if status == 429:
                return '번역 요청이 일시적으로 제한됐습니다. 잠시 후 다시 시도해 주세요. (HTTP 429)'
            return f'번역 서비스가 요청을 거절했습니다. (HTTP {status})'
        if isinstance(error, httpx.TimeoutException):
            return '번역 서버의 응답 시간이 초과됐습니다. 다시 시도해 주세요. (TIMEOUT)'
        if isinstance(error, httpx.ProxyError):
            return '프록시 서버 연결이 차단됐습니다. Windows의 프록시 설정을 확인해 주세요. (PROXY)'
        if isinstance(error, httpx.ConnectError):
            if 'certificate' in str(error).lower() or 'ssl' in str(error).lower():
                return '보안 인증서를 확인하지 못했습니다. PC 날짜와 회사·학교의 인증서 설정을 확인해 주세요. (TLS)'
            return '번역 서버에 연결하지 못했습니다. Google 번역 접속 및 방화벽 설정을 확인해 주세요. (CONNECT)'
        if isinstance(error, httpx.HTTPError):
            return '번역 서버와 통신 중 오류가 발생했습니다. (NETWORK)'
        return '번역 응답을 읽지 못했습니다. 서비스의 응답 형식이 변경됐을 수 있습니다. (RESPONSE)'

    def translate(self, text: str, target: str) -> tuple[str, str]:
        failures = []
        last_error = None
        api_limited = False
        for endpoint in self._ENDPOINTS:
            webpage = endpoint.endswith('/m')
            if api_limited and not webpage:
                continue
            try:
                options = _windows_connection_options(urlparse(endpoint).hostname)
                params = [('sl', 'ko'), ('tl', target), ('q', text)]
                if not webpage:
                    params += [('client', 'gtx'), ('dt', 't'), ('dt', 'rm'), ('dj', '1')]
                response = httpx.get(
                    endpoint,
                    params=params,
                    timeout=httpx.Timeout(12, connect=6),
                    follow_redirects=True,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Malmoa/0.1.3',
                             'Accept': 'text/html' if webpage else 'application/json'},
                    **options,
                )
                response.raise_for_status()
                if webpage:
                    parser = _GoogleResultParser()
                    parser.feed(response.text)
                    translated = ''.join(parser.parts).strip()
                    if not translated:
                        raise ValueError('Google web translation was unavailable')
                    return translated, ''
                return self._parse(response.json())
            except (httpx.HTTPError, ValueError, TypeError, IndexError, OSError) as error:
                last_error = error
                if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 429:
                    api_limited = True
                # Do not expose request URLs, input text or proxy credentials.
                failures.append(self._failure(error))
        messages = list(dict.fromkeys(failures))
        raise TranslationError(' / '.join(messages)) from last_error


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


class MyMemoryProvider:
    """Documented public MyMemory API; no key, with a free daily quota."""
    def translate(self, text: str, target: str) -> tuple[str, str]:
        from html import unescape
        language = 'zh-CN' if target == 'zh-CN' else target
        # The public API accepts at most 500 characters per query.
        chunks = [text[start:start + 450] for start in range(0, len(text), 450)]
        translations = []
        for chunk in chunks:
            try:
                response = httpx.get(
                    'https://api.mymemory.translated.net/get',
                    params={'q': chunk, 'langpair': f'ko|{language}'},
                    timeout=httpx.Timeout(12, connect=6),
                    **_windows_connection_options('api.mymemory.translated.net'),
                )
                response.raise_for_status()
                data = response.json()
                if str(data.get('responseStatus')) != '200' or data.get('quotaFinished'):
                    raise TranslationError('보조 번역 서비스의 사용량이 제한됐거나 지원하지 않는 요청입니다. (MYMEMORY LIMIT)')
                translated = data.get('responseData', {}).get('translatedText')
                if not isinstance(translated, str) or not translated.strip() or translated.upper().startswith('MYMEMORY WARNING'):
                    raise TranslationError('보조 번역 서비스에서 결과를 받지 못했습니다. (MYMEMORY RESPONSE)')
                translations.append(unescape(translated))
            except (httpx.HTTPError, ValueError, TypeError, AttributeError, OSError) as error:
                raise TranslationError('보조 번역 서비스: ' + GoogleWebProvider._failure(error)) from error
        return '\n'.join(translations), ''


class FallbackTranslationProvider:
    def __init__(self, providers: Sequence[TranslationProvider]):
        if not providers:
            raise ValueError("At least one translation provider is required")
        self._providers = tuple(providers)

    def translate(self, text: str, target: str) -> tuple[str, str]:
        failures = []
        for provider in self._providers:
            try:
                return provider.translate(text, target)
            except TranslationError as error:
                failures.append(str(error))
        raise TranslationError(' / '.join(dict.fromkeys(failures)))
