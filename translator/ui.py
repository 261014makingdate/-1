from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QLabel, QMainWindow,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)
from .core import LANGUAGES, TranslationError
from . import __version__


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    done = Signal()

    def __init__(self, translator, text, language):
        super().__init__()
        self._translator, self._text, self._language = translator, text, language

    @Slot()
    def run(self):
        try:
            self.finished.emit(self._translator.translate(self._text, self._language))
        except TranslationError as error:
            self.failed.emit(str(error))
        except Exception:
            self.failed.emit('처리 중 오류가 발생했습니다. 다시 시도해 주세요.')
        finally:
            self.done.emit()


class TranslatorWindow(QMainWindow):
    def __init__(self, translator):
        super().__init__()
        self._translator = translator
        self._thread = None
        self.setWindowTitle(f'말모아 · 한국어 번역기 v{__version__}')
        self.resize(760, 760)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(14)
        title = QLabel('말모아  |  한국어를 세계의 언어로')
        title.setStyleSheet('font-size: 23px; font-weight: bold;')
        layout.addWidget(title)
        layout.addWidget(QLabel('한국어 문장을 입력하고 언어를 선택하세요. (최대 3,000자)'))
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText('예: 안녕하세요. 만나서 반갑습니다.')
        self.input.setAccessibleName('한국어 입력')
        layout.addWidget(self.input)
        controls = QHBoxLayout()
        self.language = QComboBox()
        self.language.addItems([item.name for item in LANGUAGES])
        self.language.setAccessibleName('번역 언어')
        controls.addWidget(self.language)
        self.translate_button = QPushButton('번역하기')
        self.translate_button.clicked.connect(self.translate)
        controls.addWidget(self.translate_button)
        layout.addLayout(controls)
        self.status = QLabel('인터넷 연결이 필요합니다. 입력 문장은 Google 또는 보조 서비스 MyMemory로 전송됩니다. 무료 사용량 제한이 있습니다.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addWidget(QLabel('번역 결과'))
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setAccessibleName('번역 결과')
        layout.addWidget(self.output)
        self.copy_button = QPushButton('번역 복사')
        self.copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.output.toPlainText()))
        layout.addWidget(self.copy_button)
        layout.addWidget(QLabel('발음 · 한글로 읽기'))
        self.pronunciation = QPlainTextEdit()
        self.pronunciation.setReadOnly(True)
        self.pronunciation.setAccessibleName('발음')
        layout.addWidget(self.pronunciation)
        self.note = QLabel('아래에 한글로 읽을 수 있는 근사 발음이 표시됩니다.')
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.setCentralWidget(container)
        self.setStyleSheet('QWidget { font-size: 15px; } QPlainTextEdit, QComboBox { padding: 10px; } QPushButton { padding: 10px; }')

    @Slot()
    def translate(self):
        if self._thread is not None:
            return
        self.output.clear()
        self.pronunciation.clear()
        self.note.clear()
        self.translate_button.setEnabled(False)
        self.language.setEnabled(False)
        self.input.setReadOnly(True)
        self.status.setText('번역 중…')
        self._thread = QThread(self)
        self._worker = Worker(self._translator, self.input.toPlainText(), LANGUAGES[self.language.currentIndex()])
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self.show_result)
        self._worker.failed.connect(self.status.setText)
        self._worker.done.connect(self._thread.quit)
        self._worker.done.connect(self._worker.deleteLater)
        self._thread.finished.connect(self.reset_controls)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    @Slot(object)
    def show_result(self, result):
        self.output.setPlainText(result.text)
        self.pronunciation.setPlainText(result.pronunciation)
        self.note.setText(result.pronunciation_note)
        self.status.setText('번역 완료')

    @Slot()
    def reset_controls(self):
        self._thread = None
        self.translate_button.setEnabled(True)
        self.language.setEnabled(True)
        self.input.setReadOnly(False)

    def closeEvent(self, event):
        if self._thread is not None:
            self.status.setText('번역이 끝난 후 창을 닫아 주세요.')
            event.ignore()
        else:
            event.accept()
