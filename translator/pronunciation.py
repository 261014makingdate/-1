"""Offline, language-specific approximate Hangul pronunciation.

Hangul cannot encode every foreign phoneme, stress or lexical tone. These
readings are a speaking aid, not an exact transcription or a TTS system.
"""
import os
import re
import unicodedata

import eng_to_ipa
from pypinyin import lazy_pinyin, Style
from pykakasi import kakasi

_ONSETS = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
_VOWELS = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'
_CODAS = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
_CONSONANTS = {'b':'ㅂ', 'p':'ㅍ', 'ph':'ㅍ', 'd':'ㄷ', 't':'ㅌ', 'th':'ㅌ',
               'g':'ㄱ', 'k':'ㅋ', 'kh':'ㅋ', 'm':'ㅁ', 'n':'ㄴ', 'ng':'ㅇ',
               'l':'ㄹ', 'r':'ㄹ', 's':'ㅅ', 'sh':'ㅅ', 'z':'ㅈ', 'zh':'ㅈ',
               'ch':'ㅊ', 'j':'ㅈ', 'f':'ㅍ', 'v':'ㅂ', 'h':'ㅎ', 'ts':'ㅊ'}
_NUCLEI = {'a':'ㅏ', 'ae':'ㅐ', 'e':'ㅔ', 'i':'ㅣ', 'o':'ㅗ', 'u':'ㅜ',
           'eo':'ㅓ', 'eu':'ㅡ', 'ya':'ㅑ', 'ye':'ㅖ', 'yo':'ㅛ', 'yu':'ㅠ',
           'yeo':'ㅕ', 'wa':'ㅘ', 'we':'ㅞ', 'wi':'ㅟ', 'wo':'ㅝ', 'oe':'ㅚ'}
_FINALS = {'m':'ㅁ', 'n':'ㄴ', 'ng':'ㅇ', 'l':'ㄹ', 'r':'ㄹ', 'p':'ㅂ',
           'b':'ㅂ', 't':'ㅅ', 'd':'ㅅ', 'k':'ㄱ', 'g':'ㄱ'}


def _syllable(onset, vowel, coda=''):
    return chr(0xAC00 + (_ONSETS.index(onset) * 21 + _VOWELS.index(vowel)) * 28 + _CODAS.index(coda))


def _compose(tokens, mode='latin'):
    """Compose phonemes; insert eu for unsupported consonant clusters."""
    output = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in _NUCLEI:
            onset, vowel = 'ㅇ', _NUCLEI[token]
            i += 1
        elif token in _CONSONANTS:
            onset = _CONSONANTS[token]
            if mode == 'ja' and token == 'f':
                onset = 'ㅎ'
            if mode in ('th', 'lo'):
                onset = {'s':'ㅆ', 'k':'ㄱ', 't':'ㄸ', 'p':'ㅃ', 'ch':'ㅉ'}.get(token, onset)
            i += 1
            if i < len(tokens) and tokens[i] in _NUCLEI:
                vowel = _NUCLEI[tokens[i]]
                i += 1
            else:
                output.append(_syllable(onset, 'ㅡ'))
                continue
        else:
            output.append(token)
            i += 1
            continue
        coda = ''
        if i < len(tokens) and tokens[i] in _FINALS:
            consonant = tokens[i]
            next_vowel = i + 1 < len(tokens) and tokens[i + 1] in _NUCLEI
            at_end = i + 1 == len(tokens)
            if mode == 'en' and consonant == 'l' and next_vowel:
                # English intervocalic l is readable as a Hangul geminate.
                coda = 'ㄹ'
            elif not next_vowel and (not at_end or mode != 'en' or consonant in ('m','n','ng','l','r')):
                coda = _FINALS[consonant]
                i += 1
        output.append(_syllable(onset, vowel, coda))
    return ''.join(output)


def _latin_word(word, mode='latin'):
    word = ''.join(c for c in unicodedata.normalize('NFD', word.lower())
                   if not unicodedata.combining(c))
    combinations = {'sh':'sh', 'ch':'ch', 'zh':'zh', 'ts':'ts', 'ng':'ng',
                    'kh':'kh', 'ph':'ph', 'th':'th', 'ue':'eu', 'oe':'eo',
                    'ya':'ya', 'ye':'ye', 'yo':'yo', 'yu':'yu', 'wa':'wa',
                    'we':'we', 'wi':'wi', 'wo':'wo', 'yi':'i'}
    tokens = []
    i = 0
    while i < len(word):
        pair = word[i:i+2]
        if pair in combinations:
            tokens.append(combinations[pair]); i += 2
        elif word[i] == 'y':
            tokens.append('i'); i += 1
        elif word[i] == 'w':
            tokens.append('u'); i += 1
        elif word[i] == 'c':
            tokens.append('k'); i += 1
        elif word[i] == 'q':
            tokens.append('k'); i += 1
        elif word[i] == 'x':
            tokens.extend(['k', 's']); i += 1
        else:
            tokens.append(word[i]); i += 1
    if mode == 'ja':
        for i, token in enumerate(tokens):
            if token == 'u' and i and tokens[i-1] in ('s', 'ts'):
                tokens[i] = 'eu'
    return _compose(tokens, mode)


_PINYIN_FINALS = {'a':'아','o':'오','e':'어','i':'이','u':'우','v':'위','ü':'위',
    'ai':'아이','ei':'에이','ao':'아오','ou':'오우','an':'안','en':'언',
    'ang':'앙','eng':'엉','ong':'웅','er':'얼','ia':'야','ie':'예','iao':'야오',
    'iu':'유','ian':'옌','in':'인','iang':'양','ing':'잉','iong':'융',
    'ua':'와','uo':'워','uai':'와이','ui':'웨이','uan':'완','un':'운',
    'uang':'왕','ueng':'웡','ue':'위에','ve':'위에','üe':'위에','van':'위안','vn':'윈'}
_PINYIN_INITIALS = {'b':'ㅂ','p':'ㅍ','m':'ㅁ','f':'ㅍ','d':'ㄷ','t':'ㅌ','n':'ㄴ','l':'ㄹ',
    'g':'ㄱ','k':'ㅋ','h':'ㅎ','j':'ㅈ','q':'ㅊ','x':'ㅅ','zh':'ㅈ','ch':'ㅊ','sh':'ㅅ','r':'ㄹ',
    'z':'ㅉ','c':'ㅊ','s':'ㅆ'}
_PINYIN_GLIDES = {'yi':'이','ya':'야','ye':'예','yao':'야오','you':'요우','yan':'옌',
    'yin':'인','yang':'양','ying':'잉','yong':'융','yu':'위','yue':'위에','yuan':'위안','yun':'윈',
    'wu':'우','wa':'와','wo':'워','wai':'와이','wei':'웨이','wan':'완','wen':'원','wang':'왕','weng':'웡'}


def _pinyin_syllable(word):
    if word in _PINYIN_GLIDES:
        return _PINYIN_GLIDES[word]
    initial = next((x for x in sorted(_PINYIN_INITIALS, key=len, reverse=True) if word.startswith(x)), '')
    final = word[len(initial):]
    if initial in ('zh','ch','sh','r','z','c','s') and final == 'i':
        body = '으'
    else:
        if initial in ('j','q','x') and final in ('u','un','uan'):
            final = {'u':'v','un':'vn','uan':'van'}[final]
        body = _PINYIN_FINALS.get(final)
    if body is None:
        return _latin_word(word)
    if not initial:
        return body
    first = ord(body[0]) - 0xAC00
    return chr(0xAC00 + _ONSETS.index(_PINYIN_INITIALS[initial]) * 588 + first % 588) + body[1:]


_IPA_VOWELS = {'æ':'ae','ɛ':'e','e':'e','ə':'eo','ʌ':'eo','ɜ':'eo','ɑ':'a',
               'a':'a','ɒ':'o','ɔ':'o','o':'o','ɪ':'i','i':'i','ʊ':'u','u':'u','ɚ':'eo'}
_IPA_CONSONANTS = {'ɹ':'r','ɾ':'r','ŋ':'ng','ʃ':'sh','ʒ':'zh','θ':'s','ð':'d','ɡ':'g','j':'y','w':'w'}


def _ipa_word(word):
    leading = re.match(r'^[\(\[\"“‘]+', word)
    prefix = leading.group() if leading else ''
    word = word[len(prefix):]
    trailing = re.search(r'[.,!?;:\)\]\"”’]+$', word)
    suffix = trailing.group() if trailing else ''
    if suffix:
        word = word[:-len(suffix)]
    tokens = []
    i = 0
    while i < len(word):
        pair = word[i:i+2]
        if pair in ('tʃ','dʒ'):
            tokens.append('ch' if pair == 'tʃ' else 'j'); i += 2
            continue
        char = word[i]
        i += 1
        if char in 'ˈˌːˑ*':
            continue
        tokens.append(_IPA_VOWELS.get(char, _IPA_CONSONANTS.get(char, char)))
    # English glides form Korean compound vowels, not spoken letter names.
    result = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens) and tokens[i] in ('y','w'):
            glide = tokens[i] + tokens[i+1]
            glide = {'yeo':'yeo','weo':'wo','yu':'yu','yi':'i'}.get(glide, glide)
            if glide in _NUCLEI:
                result.append(glide); i += 2; continue
        result.append('i' if tokens[i] == 'y' else 'u' if tokens[i] == 'w' else tokens[i]); i += 1
    return prefix + _compose(result, 'en') + suffix


_RUSSIAN = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh','з':'z',
    'и':'i','й':'i','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s',
    'т':'t','у':'u','ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sh','ъ':'','ы':'eu','ь':'','э':'e','ю':'yu','я':'ya'}


class KoreanPronunciationProvider:
    def __init__(self):
        self._japanese = kakasi()

    def pronounce(self, text: str, language: str, phonetic: str = '') -> tuple[str, str]:
        if language == 'zh-CN':
            syllables = lazy_pinyin(text, style=Style.NORMAL)
            output = ' '.join(re.sub(r'[a-zü]+', lambda m: _pinyin_syllable(m.group()), s)
                              for s in syllables)
        elif language == 'ja':
            text = text.replace('こんにちは', 'こんにちわ').replace('こんばんは', 'こんばんわ')
            parts = []
            for item in self._japanese.convert(text):
                reading = item['hepburn']
                if item['orig'] == 'は' and parts:
                    reading = 'wa'
                elif item['orig'] == 'へ' and parts:
                    reading = 'e'
                parts.append(re.sub(r'[a-z]+', lambda m: _latin_word(m.group(), 'ja'), reading.lower()))
            output = ' '.join(parts)
        elif language == 'en':
            parts = []
            for variants in eng_to_ipa.ipa_list(text):
                reading = variants[0]
                if '*' in reading:
                    parts.append(re.sub(r'[a-zA-Z]+', lambda m: _latin_word(m.group(), 'en'), reading.replace('*','')))
                else:
                    parts.append(_ipa_word(reading))
            output = ' '.join(parts)
        elif language in ('th','lo'):
            # Only bundled dictionaries and rule-based RTGS are used.
            os.environ.setdefault('PYTHAINLP_READ_ONLY', '1')
            os.environ.setdefault('PYTHAINLP_OFFLINE', '1')
            from pythainlp.tokenize import word_tokenize
            from pythainlp.transliterate.royin import romanize
            if language == 'lo':
                from laonlp.transliterate import lao2thai_script
                text = lao2thai_script(text.replace('ສະບາຍດີ','싸바이디').replace('ຊ','ซ').replace('ຍ','ย'))
            parts = []
            for token in word_tokenize(text, engine='newmm'):
                if token.isspace():
                    continue
                reading = 'sawatdi' if token == 'สวัสดี' else romanize(token)
                parts.append(re.sub(r'[a-zA-Z]+', lambda m: _latin_word(m.group(), language), reading))
            output = ' '.join(parts)
        elif language == 'ru':
            def russian_word(match):
                word = match.group().lower()
                exceptions = {'привет':'프리벳','спасибо':'스파시바','здравствуйте':'즈드라스트부이테',
                              'пожалуйста':'파잘루스타','хорошо':'하라쇼'}
                if word in exceptions:
                    return exceptions[word]
                tokens = [_RUSSIAN[c] for c in word if _RUSSIAN[c]]
                return _compose(tokens, 'ru')
            output = re.sub(r'[А-Яа-яЁё]+', russian_word, text)
            output = re.sub(r'[a-zA-Z]+', lambda m: _latin_word(m.group()), output)
        else:
            raise ValueError('Unsupported pronunciation language')
        output = re.sub(r' +', ' ', output).strip()
        note = '한글로 읽기 위한 근사 발음입니다. 성조·강세·장단음과 고유명사 발음은 실제 소리와 다를 수 있습니다.'
        return output, note
