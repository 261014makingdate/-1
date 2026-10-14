import sys
from PySide6.QtWidgets import QApplication
from .core import Translator
from .pronunciation import KoreanPronunciationProvider
from .providers import GoogleWebProvider, MyMemoryProvider, FallbackTranslationProvider
from .ui import TranslatorWindow


def main():
    app = QApplication(sys.argv)
    window = TranslatorWindow(Translator(FallbackTranslationProvider([GoogleWebProvider(), MyMemoryProvider()]), KoreanPronunciationProvider()))
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
