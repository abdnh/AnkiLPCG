"""
LPCG - Lyrics/Poetry Cloze Generator
Copyright (c) 2016-2020 Soren Bjornstad <contact@sorenbjornstad.com>

License: GNU AGPL, version 3 or later.
See LICENSE file or <http://www.gnu.org/licenses/agpl.html> for details.
"""

import sys

# don't try to set up the UI if running unit tests
if 'pytest' not in sys.modules:
    # pylint: disable=import-error, no-name-in-module
    # pylint: disable=invalid-name
    import aqt
    from aqt.qt import QAction  # type: ignore
    from aqt.utils import showWarning

    from .lpcg_dialog import LPCGDialog
    from . import models

    def open_dialog():
        "Launch the add-poem dialog."
        current_version = aqt.mw.col.get_config('arlpcg_model_version', default="none")
        if not models.LpcgOne.is_at_version(current_version):
            showWarning(
                "نوع ملحوظة ARLPCG الخاص بك قديم ويجب ترقيته "
                "قبل أن تستطيع استخدام ARLPCG. للترقية، أعد تشغيل أنكي "
                "وجاوب بنعم على النافذة التي ستظهر.")
            return
        dialog = LPCGDialog(aqt.mw)
        dialog.exec_()

    if aqt.mw is not None:
        action = QAction(aqt.mw)
        action.setText("استيراد المنظومات والقصائد")
        aqt.mw.form.menuTools.addAction(action)
        action.triggered.connect(open_dialog)

        aqt.gui_hooks.profile_did_open.append(models.ensure_note_type)
