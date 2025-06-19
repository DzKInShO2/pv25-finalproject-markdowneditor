from PyQt5 import uic

from PyQt5.QtCore import (
    Qt,
    qRound,
    pyqtSignal,
)

from PyQt5.QtPrintSupport import QPrinter

from PyQt5.QtGui import (
    QFont,
    QPainter,
    QPalette,
    QTextDocument
)

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QHBoxLayout,
    QPlainTextEdit,
    QFileDialog
)

AUTHOR = "~ Dzakanov Inshoofi - F1D02310110 ~"

STYLESHEET = """
QMenu, QWidget {
    background: #1D211B;
    color: #E1E4DA;
}

QMenu {
    border: 2px solid #272B25;
    min-width: 198px;
}

QMenu:item:disabled {
    color: #43483F;
}

QMenuBar:item:selected, QMenu:item:selected {
    background: #363A34;
}

QSplitter::handle {
    background-color: #191D17;
    border: 1px solid #1E4D51;
    width: 5px;
    height: 5px;
}

QPlainTextEdit QScrollBar:handle {
    background: #263422;
    border: 1px solid #3C4B37;
}

QPlainTextEdit QScrollBar:handle:hover {
    background: #275021;
}
"""


class EditorTextLineNumber(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(32)

        self.edit: QPlainTextEdit = None

    def paintEvent(self, event):
        p = QPainter(self)

        font = self.font()
        p.setFont(font)

        digit = str(self.edit.blockCount())
        width = self.fontMetrics().horizontalAdvance("9") * len(digit)
        self.setMaximumWidth(width)

        block = self.edit.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = qRound(self.edit.blockBoundingGeometry(
            block).translated(self.edit.contentOffset()).top())
        bottom = top + qRound(self.edit.blockBoundingRect(block).height())

        lineCursor = self.edit.textCursor().blockNumber()

        color = self.palette().color(QPalette.Text)
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                if blockNumber == lineCursor:
                    p.setPen(Qt.red)
                else:
                    p.setPen(color)

                p.drawText(0, top, width, self.edit.fontMetrics().height(),
                           Qt.AlignmentFlag.AlignLeft, number)

            block = block.next()
            top = bottom
            bottom = top + \
                qRound(self.edit.blockBoundingRect(block).height())
            blockNumber += 1

        p.end()

    def resizeEvent(self, event):
        self.update()


class EditorTextArea(QWidget):
    contentUpdated = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.editor = QPlainTextEdit()
        self.editor.updateRequest.connect(self.editorUpdated)
        self.editor.cursorPositionChanged.connect(self.editorCursorMoved)
        self.editor.blockCountChanged.connect(self.editorBlockCountUpdated)
        self.line = EditorTextLineNumber()
        self.line.edit = self.editor

        layout = QHBoxLayout()

        layout.addWidget(self.line)
        layout.addWidget(self.editor)
        self.setLayout(layout)

    def editorBlockCountUpdated(self, blockCount):
        self.line.update()

    def editorUpdated(self, rect, dy):
        self.contentUpdated.emit(self.editor.toPlainText())
        self.line.update()

    def editorCursorMoved(self):
        self.line.lineCursor = self.editor.textCursor().blockNumber()
        self.line.update()


class EditorMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        uic.loadUi("main.ui", self)
        self.statusBar().addPermanentWidget(QLabel(AUTHOR))

        self.textEditor.contentUpdated.connect(self.editorUpdated)

        self.actionExit.triggered.connect(lambda: self.close())

        self.actionCopy.triggered.connect(lambda:
                                          self.textEditor.editor.copy())
        self.actionCut.triggered.connect(lambda:
                                         self.textEditor.editor.cut())
        self.actionPaste.triggered.connect(lambda:
                                           self.textEditor.editor.paste())

        self.actionCopy.setEnabled(False)
        self.actionCut.setEnabled(False)
        self.textEditor.editor.copyAvailable.connect(lambda x:
                                                     self.actionCopy.setEnabled(x))

        self.textEditor.editor.copyAvailable.connect(lambda x:
                                                     self.actionCut.setEnabled(x))

        self.actionZoom_In.triggered.connect(lambda:
                                             self.textEditor.editor.zoomIn(1))
        self.actionZoom_Out.triggered.connect(lambda:
                                              self.textEditor.editor.zoomOut(1))

        self.actionExport.triggered.connect(self.exportToPDF)

    def editorUpdated(self, content: str):
        content = content.replace("\n", "\n\n")
        self.textViewer.document().setMarkdown(content)

    def exportToPDF(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export to PDF",
            "output.pdf", "PDF Files (*.pdf)"
        )

        if filename:
            printer = QPrinter()
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(filename)

            document = QTextDocument()
            document.setMarkdown(self.textEditor.editor.toPlainText())
            document.print(printer)


if __name__ == "__main__":
    app = QApplication([])

    font = QFont("Arial, sans-serif")
    font.setPointSize(12)

    win = EditorMainWindow()
    win.setFont(font)

    win.setStyleSheet(STYLESHEET)
    win.show()

    app.exec()
