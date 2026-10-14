"""Offline diagnostics for checking the packaged desktop application."""
import json
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from .core import LANGUAGES, Translator
from .providers import RomanizationProvider
from .ui import TranslatorWindow


class _DiagnosticProvider:
    def translate(self, text, target):
        return '你好', 'nǐ hǎo'


def run(report_path: str) -> int:
    report = {'mode': 'offline', 'checks': [], 'live_translation_verified': False}
    window = None
    try:
        app = QApplication.instance() or QApplication([])
        pronunciation = RomanizationProvider()
        samples = ['你好', 'こんにちは', 'hello', 'สวัสดี', 'ສະບາຍດີ', 'Привет']
        for language, text in zip(LANGUAGES, samples):
            result, note = pronunciation.pronounce(text, language.code)
            if not result.strip() or not note:
                raise RuntimeError(f'Pronunciation unavailable: {language.code}')
            report['checks'].append({'language': language.code, 'pronunciation': result})
        window = TranslatorWindow(Translator(_DiagnosticProvider(), pronunciation))
        window.show()
        window.input.setPlainText('안녕하세요')
        window.translate()
        loop = QEventLoop()
        window._thread.finished.connect(loop.quit)
        QTimer.singleShot(10000, loop.quit)
        loop.exec()
        app.processEvents()
        if window._thread is not None:
            raise RuntimeError('Translation worker did not finish')
        if window.output.toPlainText() != '你好' or window.pronunciation.toPlainText() != 'nǐ hǎo':
            raise RuntimeError('Desktop output mismatch')
        if not window.translate_button.isEnabled():
            raise RuntimeError('Desktop controls did not recover')
        report['checks'].append({'desktop_window_and_worker': 'passed'})
        report['status'] = 'passed'
        exit_code = 0
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = f'{type(error).__name__}: {error}'
        exit_code = 1
    finally:
        if window is not None and window._thread is None:
            window.close()
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return exit_code


def run_live(report_path: str) -> int:
    """Exercise all six languages through the packaged network adapter."""
    import re
    from .providers import GoogleWebProvider
    translator = Translator(GoogleWebProvider(), RomanizationProvider())
    scripts = [r'[\u4e00-\u9fff]', r'[\u3040-\u30ff]', r'[A-Za-z]',
               r'[\u0e00-\u0e7f]', r'[\u0e80-\u0eff]', r'[\u0400-\u04ff]']
    report = {'mode': 'live', 'checks': [], 'live_translation_verified': True}
    for language, script in zip(LANGUAGES, scripts):
        try:
            result = translator.translate('안녕하세요. 만나서 반갑습니다.', language)
            if not re.search(script, result.text) or not result.pronunciation.strip():
                raise RuntimeError('Translation or pronunciation is missing')
            report['checks'].append({'language': language.code, 'status': 'passed',
                                     'translation': result.text, 'pronunciation': result.pronunciation})
        except Exception as error:
            report['live_translation_verified'] = False
            report['checks'].append({'language': language.code, 'status': 'failed', 'error': str(error)})
    report['status'] = 'passed' if report['live_translation_verified'] else 'failed'
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['live_translation_verified'] else 1
