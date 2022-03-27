import codecs
import urllib
import html

import aqt
import aqt.editor
from aqt.qt import *  # type: ignore
from aqt.utils import getFile, showWarning, askUser, tooltip
from anki.notes import Note


if aqt.qtmajor > 5:
    from . import import_dialog_qt6 as lpcg_form
else:
    from . import import_dialog_qt5 as lpcg_form

from .gen_notes import MediaImportMode, add_notes, cleanse_text, ImportMode
from . import models


class LPCGDialog(QDialog):
    """
    Import Lyrics/Poetry dialog, the core of the add-on. The user can either
    enter the text of a poem in the editor or import a text file from somewhere
    else on the computer. The poem can be entered with usual markup (blank
    lines between stanzas, one level of indentation with tabs or spaces in
    front of lines). LPCG then processes it into notes with two lines of
    context and adds them to the user's collection.
    """
    def __init__(self, mw):
        self.mw = mw

        QDialog.__init__(self)
        self.form = lpcg_form.Ui_Dialog()
        self.form.setupUi(self)
        self.deckChooser = aqt.deckchooser.DeckChooser(
            self.mw, self.form.deckChooser)

        self.form.addCardsButton.clicked.connect(self.accept)
        self.form.cancelButton.clicked.connect(self.reject)
        self.form.openFileButton.clicked.connect(self.onOpenFile)
        self.form.helpButton.clicked.connect(self.onHelp)
        self.form.automaticCheckBox.toggled.connect(self.onAutomatic)
        self.form.bySectionCheckBox.toggled.connect(self.onBySection)

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        opt = QTextOption()
        opt.setTextDirection(Qt.LayoutDirection.RightToLeft)
        opt.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.form.textBox.document().setDefaultTextOption(opt)

        self.media = []
        self.form.mediaButton.clicked.connect(self.onMedia)

    def accept(self):
        "On close, create notes from the contents of the poem editor."
        title = self.form.titleBox.text().strip()
        mode = self.getImportMode()

        if not title and mode == ImportMode.CUSTOM:
            showWarning("يجب أن تدخل عنوانًا لهذه القصيدة.")
            return

        if not self.form.textBox.toPlainText().strip():
            showWarning("لا يوجد شيء لتوليد البطاقات! "
                        "اكتب قصيدة في الصندوق النصي، أو "
                        'استخدم زر "فتح ملف" لاستيراد ملف نصي.')
            return

        config = self.mw.addonManager.getConfig(__name__)
        tags = self.mw.col.tags.split(self.form.tagsBox.text())
        text = cleanse_text(self.form.textBox.toPlainText().strip(),
                            config)
        context_lines = self.form.contextLinesSpin.value()
        recite_lines = self.form.reciteLinesSpin.value()
        group_lines = self.form.groupLinesSpin.value()
        step = self.form.StepSpin.value()
        did = self.deckChooser.selectedId()
        self.writeMedia()

        try:
            notes_generated = add_notes(self.mw.col, config, Note, title, tags, text, did,
                                        context_lines, group_lines, recite_lines, step, self.media,
                                        self.getMediaImportMode(), mode,
                                        self.form.caesura.text())
        except KeyError as e:
            showWarning(
                "تعذر إيجاد حقل {field} في نوع ملحوظة {name} في مجموعتك. "
                "إذا لم يكن لديك أي ملحوظات ARLPCG بعد، تستطيع حذف "
                "نوع الملحوظة من خلال أدوات > إدارة أنواع الملحوظات وإعادة تشغيل "
                "أنكي لحل المشكلة. أو أضف الحقل إلى نوع الملحوظة."
                .format(field=str(e), name=models.LpcgOne.name))  # pylint: disable=no-member
            return

        if notes_generated:
            super(LPCGDialog, self).accept()
            self.mw.reset()
            tooltip("%i notes added." % notes_generated)

    def getImportMode(self) -> ImportMode:
        if self.form.automaticCheckBox.isChecked():
            return ImportMode.AUTOMATIC
        elif self.form.bySectionCheckBox.isChecked():
            return ImportMode.BY_SECTION
        else:
            return ImportMode.CUSTOM

    def onAutomatic(self, checked: bool):
        if checked:
            self.form.bySectionCheckBox.setChecked(False)
        self.form.titleBox.setEnabled(not self.form.titleBox.isEnabled())
        self.updateCaesuraInputState()

    def onBySection(self, checked: bool):
        if checked:
            self.form.automaticCheckBox.setChecked(False)
        self.form.titleBox.setEnabled(not self.form.titleBox.isEnabled())
        self.form.StepSpin.setEnabled(not self.form.StepSpin.isEnabled())
        self.form.reciteLinesSpin.setEnabled(not self.form.reciteLinesSpin.isEnabled())
        self.form.contextLinesSpin.setEnabled(not self.form.contextLinesSpin.isEnabled())
        self.form.groupLinesSpin.setEnabled(not self.form.groupLinesSpin.isEnabled())
        self.updateCaesuraInputState()

    def updateCaesuraInputState(self):
        if self.form.automaticCheckBox.isChecked() or self.form.bySectionCheckBox.isChecked():
            self.form.caesura.setEnabled(True)
        else:
            self.form.caesura.setEnabled(False)

    def getMediaImportMode(self) -> MediaImportMode:
        if self.form.MediaByNoteRadioButton.isChecked():
            return MediaImportMode.ONE_FOR_EACH_NOTE
        elif self.form.MediaByReciteLinesRadioButton.isChecked():
            return MediaImportMode.BY_RECITE_LINES
        else:
            return MediaImportMode.BULK

    def onMedia(self):
        filenames = getFile(self, "استيراد وسائط", None, key="import", multi=True)
        if filenames:
            self.media = filenames

    # from aqt/editor.py with some changes
    def fnameToLink(self, fname: str) -> str:
        ext = fname.split(".")[-1].lower()
        if ext in aqt.editor.pics:
            name = urllib.parse.quote(fname.encode("utf8"))
            return '<img src="%s">' % name
        else:
            return "[sound:%s]" % html.escape(fname, quote=False)

    def writeMedia(self):
        new_filenames = []
        for filename in self.media:
            new_filenames.append(self.fnameToLink(self.mw.col.media.add_file(filename)))
        self.media = new_filenames

    def onOpenFile(self):
        """
        Read a text file (in UTF-8 encoding) and replace the contents of the
        poem editor with the contents of the file.
        """
        if (self.form.textBox.toPlainText().strip()
                and not askUser("سيؤدي استيراد ملف إلى استبدال المحتوى الحالي لمحرر الأشعار. "
                                "هل تريد الاستمرار؟")):
            return
        filename = getFile(self, "استيراد نص", None, key="import")
        if not filename: # canceled
            return
        with codecs.open(filename, 'r', 'utf-8') as f:
            text = f.read()
        self.form.textBox.setPlainText(text)

    def onHelp(self):
        """
        Open the documentation on importing files in a browser.
        """
        doc_url = "https://ankilpcg.readthedocs.io/en/latest/importing.html"
        QDesktopServices.openUrl(QUrl(doc_url))
