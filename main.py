from PyQt5 import uic

from PyQt5.QtCore import (
    Qt,
    QDir,
    qRound,
    QDateTime,
    pyqtSignal,
)

from PyQt5.QtSql import (
    QSqlQuery,
    QSqlDatabase,
    QSqlQueryModel
)

from PyQt5.QtPrintSupport import QPrinter

from PyQt5.QtGui import (
    QFont,
    QColor,
    QPainter,
    QPalette,
    QTextDocument
)

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QWidget,
    QLabel,
    QAction,
    QHBoxLayout,
    QPlainTextEdit,
    QFileDialog,
)


FONT = QFont("Arial, sans-serif")
FONT.setPointSize(12)

AUTHOR = "~ Dzakanov Inshoofi - F1D02310110 ~"

SUPPORTED_FILES = "Markdown Files (*.md);;Text Files (*.txt);;All Files (*.*)"

STYLESHEET = """
QMenu, QWidget, QMenuBar, QMenuBar:item, QListView {
    color: #E1E4DA;
    background: #191D17;
    padding: 6px;
}

QMenu {
    border: 2px solid #272B25;
}

QMenu:item:disabled {
    color: #43483F;
}

QMenuBar:item:selected, QMenu:item:selected, QListView:item:selected {
    background: #363A34;
}

QSplitter::handle {
    background-color: #1D211B;
    border: 1px solid #191D17;
    width: 5px;
    height: 5px;
}

QSplitter::handle:hover {
    background-color: #10380C;
}

QPlainTextEdit QScrollBar:handle {
    background: #263422;
    border: 1px solid #3C4B37;
}

QPlainTextEdit QScrollBar:handle:hover {
    background: #275021;
}

QPlainTextEdit, QTextBrowser {
    background: #1D211B;
}
"""


class EditorHistoryDatabase:
    SELECT_OPEN_FILE_QUERY = """
            SELECT name, path FROM File
            WHERE isInUse = 1
            ORDER BY lastAccessed
            DESC
            """

    def __init__(self, dbName="history"):
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName(dbName)

        self.db.open()

        QSqlQuery().exec(
            """
            CREATE TABLE IF NOT EXISTS File (
                id INTEGER PRIMARY KEY NOT NULL,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                lastAccessed DATETIME NOT NULL,
                isInUse INT NOT NULL
            );
            """
        )

        self.openFileModel = QSqlQueryModel()
        self.openFileModel.setQuery(self.SELECT_OPEN_FILE_QUERY)

    def openFile(self, path):
        now = QDateTime.currentDateTime().toString(Qt.ISODate)

        fileQuery = QSqlQuery(f"SELECT id FROM File WHERE path = '{path}'")
        if fileQuery.next():
            id = fileQuery.value(0)
            updateQuery = QSqlQuery("""
                UPDATE File SET
                lastAccessed = ?,
                isInUse = 1
                WHERE id = ?
                """)
            updateQuery.addBindValue(now)
            updateQuery.addBindValue(id)
            updateQuery.exec()
        else:
            insertQuery = QSqlQuery("""
                INSERT INTO File (name, path, lastAccessed, isInUse)
                VALUES
                (?, ?, ?, ?)
                """)
            name = path.split("/")
            name = name[-1]
            insertQuery.addBindValue(name)
            insertQuery.addBindValue(path)
            insertQuery.addBindValue(now)
            insertQuery.addBindValue(1)
            insertQuery.exec()

        self.openFileModel.setQuery(self.SELECT_OPEN_FILE_QUERY)

    def clearHistory(self):
        deleteQuery = QSqlQuery("DELETE FROM File")
        deleteQuery.exec()

        self.openFileModel.setQuery(self.SELECT_OPEN_FILE_QUERY)

    def deleteFile(self, path):
        deleteQuery = QSqlQuery("DELETE FROM File WHERE path = ?")
        deleteQuery.addBindValue(path)
        deleteQuery.exec()

        self.openFileModel.setQuery(self.SELECT_OPEN_FILE_QUERY)

    def closeFile(self, path):
        if path is None:
            return

        fileQuery = QSqlQuery(f"SELECT id FROM File WHERE path = '{path}'")
        if fileQuery.next():
            id = fileQuery.value(0)
            updateQuery = QSqlQuery("""
                UPDATE File SET
                isInUse = 0
                WHERE id = ?
                """)
            updateQuery.addBindValue(id)
            updateQuery.exec()

        self.openFileModel.setQuery(self.SELECT_OPEN_FILE_QUERY)


class EditorTextLineNumber(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(32)

        self.edit = None

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
            block).translated(self.edit.contentOffset()).top()) + 5
        bottom = top + qRound(self.edit.blockBoundingRect(block).height())

        lineCursor = self.edit.textCursor().blockNumber()

        color = self.palette().color(QPalette.Text)
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                if blockNumber == lineCursor:
                    p.setPen(QColor("#FF5449"))
                else:
                    p.setPen(color)

                p.drawText(0, top, width, self.edit.fontMetrics().height(),
                           Qt.AlignmentFlag.AlignLeft, number)

            block = block.next()
            top = bottom
            bottom = top + qRound(self.edit.blockBoundingRect(block).height())
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
    FORMAT_BOLD = 0
    FORMAT_ITALIC = 1
    FORMAT_STROKE = 2

    def __init__(self):
        super().__init__()
        self.currentFile = None
        self.db = EditorHistoryDatabase()

        uic.loadUi("main.ui", self)

        self.splitter.setSizes([80, 320, 320])

        self.statusBar().addPermanentWidget(QLabel(AUTHOR))
        self.textEditor.contentUpdated.connect(self.editorUpdated)

        # File View Config
        self.fileViewer.setModel(self.db.openFileModel)
        self.fileViewer.clicked.connect(self.fileSelectedOnView)
        self.fileViewer.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.fileViewer.customContextMenuRequested.connect(self.fileViewMenu)

        # File Action
        self.actionNew.triggered.connect(self.newFile)
        self.actionOpen.triggered.connect(self.openFile)
        self.actionClearHistory.triggered.connect(lambda:
                                                  self.db.clearHistory())
        self.actionClearHistory.triggered.connect(lambda:
                                                  self.newFile())
        self.actionSave.triggered.connect(lambda:
                                          self.saveToFile(self.currentFile))
        self.actionSaveAs.triggered.connect(lambda: self.saveToFile())
        self.actionExport.triggered.connect(self.exportToPDF)
        self.actionExit.triggered.connect(lambda: self.close())

        # Edit Action
        self.actionCopy.triggered.connect(lambda:
                                          self.textEditor.editor.copy())
        self.actionCut.triggered.connect(lambda:
                                         self.textEditor.editor.cut())
        self.actionPaste.triggered.connect(lambda:
                                           self.textEditor.editor.paste())
        self.actionUndo.triggered.connect(lambda:
                                          self.textEditor.editor.redo())
        self.actionUndo.triggered.connect(lambda:
                                          self.textEditor.editor.undo())
        self.actionFormatBold.triggered.connect(lambda:
                                                self.formatText(self.FORMAT_BOLD))
        self.actionFormatItalic.triggered.connect(lambda:
                                                  self.formatText(self.FORMAT_ITALIC))
        self.actionFormatStroke.triggered.connect(lambda:
                                                  self.formatText(self.FORMAT_STROKE))

        self.actionCopy.setEnabled(False)
        self.actionCut.setEnabled(False)
        self.actionUndo.setEnabled(False)
        self.actionRedo.setEnabled(False)

        self.textEditor.editor.copyAvailable.connect(lambda x:
                                                     self.actionCopy.setEnabled(x))
        self.textEditor.editor.copyAvailable.connect(lambda x:
                                                     self.actionCut.setEnabled(x))
        self.textEditor.editor.undoAvailable.connect(lambda x:
                                                     self.actionUndo.setEnabled(x))
        self.textEditor.editor.redoAvailable.connect(lambda x:
                                                     self.actionRedo.setEnabled(x))

        # View Action
        self.actionZoomIn.triggered.connect(lambda:
                                            self.textEditor.editor.zoomIn(1))
        self.actionZoomOut.triggered.connect(lambda:
                                             self.textEditor.editor.zoomOut(1))
        self.actionStyleDefault.triggered.connect(lambda:
                                                  self.setStyleSheet(""))
        self.actionStyleME.triggered.connect(lambda:
                                             self.setStyleSheet(STYLESHEET))

    def formatText(self, format):
        cursor = self.textEditor.editor.textCursor()
        selected = cursor.selectedText()

        if format == self.FORMAT_BOLD:
            cursor.insertText(f"**{selected}**")
        elif format == self.FORMAT_ITALIC:
            cursor.insertText(f"*{selected}*")
        elif format == self.FORMAT_STROKE:
            cursor.insertText(f"~~{selected}~~")

        if selected != "":
            return

        if format == self.FORMAT_ITALIC:
            cursor.setPosition(cursor.position() - 1)
        else:
            cursor.setPosition(cursor.position() - 2)
        self.textEditor.editor.setTextCursor(cursor)

    def fileViewMenu(self, pos):
        menu = QMenu()

        action = QAction("Close", menu)
        action.triggered.connect(self.fileViewClose)
        action.triggered.connect(lambda: self.newFile())

        if self.currentFile is None:
            action.setEnabled(False)

        menu.addAction(action)
        menu.exec_(self.fileViewer.viewport().mapToGlobal(pos))

    def fileViewClose(self):
        self.db.closeFile(self.currentFile)

    def fileSelectedOnView(self, index):
        row = index.row()
        path = self.db.openFileModel.index(row, 1).data()
        if path:
            self.currentFile = path
            with open(path, "r") as fr:
                self.openToEditor(fr.read())

    def editorUpdated(self, content: str):
        content = content.replace("\n", "\n\n")
        self.textViewer.document().setMarkdown(content)

    def newFile(self):
        self.currentFile = None
        self.textEditor.editor.setPlainText("")

    def openFile(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open File",
            QDir.homePath(),
            SUPPORTED_FILES
        )

        if filename:
            self.currentFile = filename
            self.db.openFile(filename)
            with open(filename, "r") as fr:
                content = fr.read()
                self.openToEditor(content)

    def openToEditor(self, content):
        self.textEditor.editor.setPlainText(content)

    def saveToFile(self, filename=None):
        if filename is None:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save As",
                QDir.homePath(),
                SUPPORTED_FILES
            )

            self.currentFile = filename
            self.db.openFile(filename)

        if filename:
            with open(filename, "w") as fw:
                fw.write(self.textEditor.editor.toPlainText())

    def exportToPDF(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export to PDF",
            QDir.homePath(), "PDF Files (*.pdf)"
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

    win = EditorMainWindow()
    win.setFont(FONT)

    win.setStyleSheet(STYLESHEET)
    win.show()

    app.exec()
