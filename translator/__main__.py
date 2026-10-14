import sys
from PySide6.QtWidgets import QApplication
from .core import Translator
from .providers import GoogleWebProvider, RomanizationProvider
from .ui import TranslatorWindow


def main():
    app = QApplication(sys.argv)
    window = TranslatorWindow(Translator(GoogleWebProvider(), RomanizationProvider()))
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
