import time
import sys

from qt.core import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                     QPushButton, QDialog, QDialogButtonBox, QCheckBox, QTabWidget,
                     Qt, QGroupBox)
from calibre.gui2 import warning_dialog
from calibre.utils.config import JSONConfig
from calibre_plugins.highlights_to_obsidian.version import version
from calibre_plugins.highlights_to_obsidian.constants import TIME_FORMAT
from calibre_plugins.highlights_to_obsidian.templates import (
    VAULT_DEFAULT_NAME, TITLE_FORMAT, BODY_FORMAT,
    HEADER_FORMAT, NOTE_HEADER_FORMAT, SORT_KEY_DEFAULT, FORMAT_OPTIONS
)


def create_selectable_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


prefs = JSONConfig('plugins/highlights_to_obsidian')

prefs.defaults['vault_name'] = VAULT_DEFAULT_NAME
prefs.defaults['title_format'] = TITLE_FORMAT
prefs.defaults['body_format'] = BODY_FORMAT
prefs.defaults['no_notes_format'] = ""
prefs.defaults['header_format'] = HEADER_FORMAT
prefs.defaults['note_header_format'] = NOTE_HEADER_FORMAT
prefs.defaults['sort_key'] = SORT_KEY_DEFAULT

prefs.defaults['last_send_time'] = time.strftime(
    TIME_FORMAT, time.localtime(172800))
prefs.defaults['confirm_send_all'] = True
prefs.defaults['highlights_sent_dialog'] = True
prefs.defaults['max_note_size'] = 20000
prefs.defaults['copy_header'] = False
prefs.defaults['web_user_name'] = "*"
prefs.defaults['web_user'] = False
prefs.defaults['use_xdg_open'] = False
prefs.defaults['sleep_secs'] = 0.1

prefs.defaults.update({
    "vault_path": "",
    "use_direct_write": True,
    "open_obsidian_after_write": False,
    "prepend_on_write": False,
    "enable_file_logging": False,
    "log_level": "INFO",
})


class ConfigWidget(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        self.l = QVBoxLayout()
        self.setLayout(self.l)
        self.spacing = 10

        self.config_label = QLabel(
            f'<b>Highlights to Obsidian v{version}</b>', self)
        self.l.addWidget(self.config_label)

        self.l.addSpacing(self.spacing)

        open_config_button = QPushButton("Open Configuration")
        open_config_button.clicked.connect(self.do_config)
        self.l.addWidget(open_config_button)

        self.l.addSpacing(self.spacing)

    def do_config(self):
        dialog = H2OConfigDialog()
        dialog.exec()

    def save_settings(self):
        pass


class H2OConfigDialog(QDialog):

    def __init__(self):
        QDialog.__init__(self)
        self.setWindowTitle("Highlights to Obsidian Configuration")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self.format_tab = self._create_format_tab()
        self.vault_tab = self._create_vault_tab()
        self.advanced_tab = self._create_advanced_tab()

        self.tabs.addTab(self.format_tab, "Formatting")
        self.tabs.addTab(self.vault_tab, "Vault")
        self.tabs.addTab(self.advanced_tab, "Advanced")

        self.buttons = QDialogButtonBox()
        self.buttons.setStandardButtons(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.ok_button)
        self.buttons.rejected.connect(self.cancel_button)
        self.main_layout.addWidget(self.buttons)

    def _create_format_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        layout.setSpacing(4)

        layout.addWidget(QLabel(
            "Use <b>{variable}</b> in templates. "
            "Use <b>{if_notes}...{end_if_notes}</b> for content shown only when highlight has notes."
        ))

        self.var_toggle_btn = QPushButton("▶ 显示变量参考")
        self.var_toggle_btn.setFlat(True)
        self.var_toggle_btn.setStyleSheet("text-align: left; padding: 2px;")
        self.var_toggle_btn.clicked.connect(self._toggle_var_ref)
        layout.addWidget(self.var_toggle_btn)

        self.var_ref_widget = self._create_var_ref_widget()
        self.var_ref_widget.setVisible(False)
        layout.addWidget(self.var_ref_widget)

        layout.addWidget(QLabel('<b>Note title format:</b>'))
        self.title_format_input = QLineEdit()
        self.title_format_input.setText(prefs['title_format'] or TITLE_FORMAT)
        self.title_format_input.setPlaceholderText("Note title format...")
        layout.addWidget(self.title_format_input)

        layout.addWidget(QLabel('<b>Note body format:</b>'))
        self.body_format_input = QPlainTextEdit()
        self.body_format_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.body_format_input.setPlainText(prefs['body_format'] or BODY_FORMAT)
        self.body_format_input.setFixedHeight(150)
        layout.addWidget(self.body_format_input)

        layout.addWidget(QLabel(
            '<b>笔记头部模板</b> (only added once for new note, supports: {title}, {authors_str}):'))
        self.note_header_format_input = QPlainTextEdit()
        self.note_header_format_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.note_header_format_input.setPlainText(prefs.get('note_header_format', '') or NOTE_HEADER_FORMAT)
        self.note_header_format_input.setFixedHeight(80)
        layout.addWidget(self.note_header_format_input)

        reset_btn = QPushButton("恢复默认模板")
        reset_btn.clicked.connect(self.reset_to_defaults)
        layout.addWidget(reset_btn)

        layout.addStretch()
        return tab

    def _create_var_ref_widget(self) -> QWidget:
        widget = QWidget()
        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(10, 2, 2, 2)
        vlayout.setSpacing(2)

        f_opt_str = "'" + "', '".join(FORMAT_OPTIONS) + "'"
        strs = []
        char_count = 0
        start_idx = 0
        for idx in range(len(f_opt_str)):
            char_count += 1
            if char_count > 100 and f_opt_str[idx] == " ":
                strs.append(f_opt_str[start_idx:idx])
                start_idx = idx
                char_count = 0
        strs.append(f_opt_str[start_idx:])
        vlayout.addWidget(create_selectable_label("<br/>".join(strs)))

        vlayout.addWidget(create_selectable_label(
            "Times with 'local' prefix use local timezone. Others use UTC. 'now' variables show current time."))
        vlayout.addWidget(create_selectable_label(
            "All times (except 'now') are when the highlight was made, not the current time."))
        vlayout.addWidget(create_selectable_label(
            "<b>Tip:</b> {notes_quoted} for notes with blank lines, {callout_quote} for Obsidian callout."))

        widget.setLayout(vlayout)
        return widget

    def _toggle_var_ref(self):
        visible = not self.var_ref_widget.isVisible()
        self.var_ref_widget.setVisible(visible)
        self.var_toggle_btn.setText("▼ 隐藏变量参考" if visible else "▶ 显示变量参考")

    def _create_vault_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        layout.setSpacing(8)

        mode_info = QLabel(
            "<b>发送模式对比：</b><br/><br/>"
            "<b>URI 模式</b>：仅能新建独立笔记，不支持追加/修改现有笔记。需要 Obsidian 正在运行，每次发送会切换到 Obsidian 窗口。零权限要求。<br/><br/>"
            "<b>Direct Write 模式</b>：支持新建笔记 + 追加/前置内容到现有笔记。无需打开 Obsidian，后台静默写入。需要 Obsidian 库文件夹的读写权限。<br/><br/>"
            "<b>推荐</b>：整书精读、多次高亮汇总到同一笔记 → 使用 Direct Write 模式"
        )
        mode_info.setWordWrap(True)
        mode_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(mode_info)

        basic_group = QGroupBox("基本设置")
        basic_layout = QVBoxLayout()
        basic_layout.setSpacing(4)

        basic_layout.addWidget(QLabel('<b>Obsidian vault name:</b> (for URI mode)'))
        self.vault_input = QLineEdit()
        self.vault_input.setText(prefs['vault_name'])
        self.vault_input.setPlaceholderText("Obsidian vault name...")
        basic_layout.addWidget(self.vault_input)

        basic_layout.addWidget(QLabel('<b>Obsidian vault absolute path:</b> (for direct write)'))
        self.vault_path_input = QLineEdit()
        self.vault_path_input.setText(prefs.get('vault_path', ''))
        self.vault_path_input.setPlaceholderText(r"C:\Users\you\Obsidian\YourVault")
        basic_layout.addWidget(self.vault_path_input)

        self.use_direct_chk = QCheckBox(
            "Enable direct write into vault (bypasses Obsidian URI)")
        self.use_direct_chk.setChecked(bool(prefs.get('use_direct_write', False)))
        self.use_direct_chk.stateChanged.connect(self._update_vault_options)
        basic_layout.addWidget(self.use_direct_chk)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        direct_group = QGroupBox("Direct Write 选项")
        direct_layout = QVBoxLayout()
        direct_layout.setSpacing(4)

        self.open_after_chk = QCheckBox("Open note in Obsidian after write")
        self.open_after_chk.setChecked(bool(prefs.get('open_obsidian_after_write', False)))
        direct_layout.addWidget(self.open_after_chk)

        self.prepend_chk = QCheckBox("PREPEND new content (uncheck to APPEND)")
        self.prepend_chk.setChecked(bool(prefs.get('prepend_on_write', False)))
        direct_layout.addWidget(self.prepend_chk)

        direct_group.setLayout(direct_layout)
        layout.addWidget(direct_group)
        self.direct_group = direct_group

        sort_group = QGroupBox("排序设置")
        sort_layout = QVBoxLayout()
        sort_layout.setSpacing(4)

        sort_layout.addWidget(QLabel("<b>Sort key:</b> Sort order for highlights in same note."))
        sort_layout.addWidget(create_selectable_label("Options: timestamp, location, date, time, chapter"))
        self.sort_input = QLineEdit()
        self.sort_input.setText(prefs['sort_key'])
        sort_layout.addWidget(self.sort_input)

        sort_group.setLayout(sort_layout)
        layout.addWidget(sort_group)

        self._update_vault_options()
        layout.addStretch()
        return tab

    def _update_vault_options(self):
        use_direct = self.use_direct_chk.isChecked()
        self.vault_input.setEnabled(not use_direct)
        self.vault_path_input.setEnabled(use_direct)
        self.open_after_chk.setEnabled(use_direct)
        self.prepend_chk.setEnabled(use_direct)

    def _create_advanced_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        layout.setSpacing(8)

        note_group = QGroupBox("笔记设置")
        note_layout = QVBoxLayout()
        note_layout.setSpacing(4)

        note_layout.addWidget(QLabel('<b>Maximum note size</b> (0 = unlimited):'))
        self.max_size_input = QLineEdit()
        self.max_size_input.setText(str(prefs['max_note_size']))
        note_layout.addWidget(self.max_size_input)

        self.copy_header_checkbox = QCheckBox(
            "Include header in each split note")
        self.copy_header_checkbox.setChecked(prefs['copy_header'])
        note_layout.addWidget(self.copy_header_checkbox)

        note_group.setLayout(note_layout)
        layout.addWidget(note_group)

        send_group = QGroupBox("发送设置")
        send_layout = QVBoxLayout()
        send_layout.setSpacing(4)

        time_row = QHBoxLayout()
        time_row.addWidget(QLabel('<b>Last send time:</b>'))
        self.time_input = QLineEdit()
        self.time_input.setText(prefs['last_send_time'])
        self.time_input.setReadOnly(True)
        time_row.addWidget(self.time_input)
        self.set_time_now_button = QPushButton("Now")
        self.set_time_now_button.clicked.connect(self.set_time_now)
        time_row.addWidget(self.set_time_now_button)
        send_layout.addLayout(time_row)

        send_layout.addWidget(QLabel('<b>Time to wait</b> between sends (seconds):'))
        self.sleep_time_input = QLineEdit()
        self.sleep_time_input.setText(str(prefs['sleep_secs']))
        send_layout.addWidget(self.sleep_time_input)

        send_group.setLayout(send_layout)
        layout.addWidget(send_group)

        ui_group = QGroupBox("界面选项")
        ui_layout = QVBoxLayout()
        ui_layout.setSpacing(4)

        self.show_confirmation_checkbox = QCheckBox("Confirm before sending all highlights")
        self.show_confirmation_checkbox.setChecked(prefs['confirm_send_all'])
        ui_layout.addWidget(self.show_confirmation_checkbox)

        self.show_count_checkbox = QCheckBox("Show count after sending")
        self.show_count_checkbox.setChecked(prefs['highlights_sent_dialog'])
        ui_layout.addWidget(self.show_count_checkbox)

        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)

        web_group = QGroupBox("Web 用户设置")
        web_layout = QVBoxLayout()
        web_layout.setSpacing(4)

        self.web_user_checkbox = QCheckBox("Send web user's highlights")
        self.web_user_checkbox.setChecked(prefs['web_user'])
        self.web_user_checkbox.stateChanged.connect(self._update_web_options)
        web_layout.addWidget(self.web_user_checkbox)

        web_layout.addWidget(QLabel('<b>Web username:</b>'))
        self.web_user_name_input = QLineEdit()
        self.web_user_name_input.setText(prefs['web_user_name'])
        self.web_user_name_input.setPlaceholderText("* for default")
        web_layout.addWidget(self.web_user_name_input)

        web_group.setLayout(web_layout)
        layout.addWidget(web_group)

        debug_group = QGroupBox("调试")
        debug_layout = QVBoxLayout()
        debug_layout.setSpacing(4)

        self.linux_xdg_checkbox = QCheckBox("Use xdg-open (Linux only)")
        self.linux_xdg_checkbox.setChecked(prefs['use_xdg_open'])
        self.linux_xdg_checkbox.setEnabled(sys.platform.startswith('linux'))
        debug_layout.addWidget(self.linux_xdg_checkbox)

        self.file_logging_checkbox = QCheckBox("Enable file logging")
        self.file_logging_checkbox.setChecked(prefs.get('enable_file_logging', False))
        debug_layout.addWidget(self.file_logging_checkbox)

        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)

        layout.addStretch()
        return tab

    def _update_web_options(self):
        enabled = self.web_user_checkbox.isChecked()
        self.web_user_name_input.setEnabled(enabled)

    def set_time_now(self):
        prefs["last_send_time"] = time.strftime(TIME_FORMAT, time.localtime())
        self.time_input.setText(prefs['last_send_time'])

    def reset_to_defaults(self):
        self.body_format_input.setPlainText(BODY_FORMAT)
        self.note_header_format_input.setPlainText(NOTE_HEADER_FORMAT)

    def save_settings(self):
        prefs['title_format'] = self.title_format_input.text()
        body = self.body_format_input.toPlainText()
        prefs['body_format'] = body if body.strip() else BODY_FORMAT
        header = self.note_header_format_input.toPlainText()
        prefs['note_header_format'] = header if header.strip() else NOTE_HEADER_FORMAT

        prefs['vault_name'] = self.vault_input.text()
        prefs['vault_path'] = self.vault_path_input.text().strip()
        prefs['use_direct_write'] = bool(self.use_direct_chk.isChecked())
        prefs['open_obsidian_after_write'] = bool(self.open_after_chk.isChecked())
        prefs['prepend_on_write'] = bool(self.prepend_chk.isChecked())
        prefs['sort_key'] = self.sort_input.text()

        max_size = self.max_size_input.text()
        try:
            prefs['max_note_size'] = int(max_size) if max_size.strip() else 0
        except ValueError:
            prefs['max_note_size'] = 20000
        prefs['copy_header'] = self.copy_header_checkbox.isChecked()

        prefs['confirm_send_all'] = self.show_confirmation_checkbox.isChecked()
        prefs['highlights_sent_dialog'] = self.show_count_checkbox.isChecked()
        prefs['use_xdg_open'] = self.linux_xdg_checkbox.isChecked()
        prefs['enable_file_logging'] = self.file_logging_checkbox.isChecked()

        username = self.web_user_name_input.text()
        prefs['web_user_name'] = "*" if username == "" else username
        prefs['web_user'] = self.web_user_checkbox.isChecked()

        sleep_time = self.sleep_time_input.text()
        try:
            prefs['sleep_secs'] = float(sleep_time)
        except:
            txt = f'Could not parse "{sleep_time}". The time to wait between sending highlights will not be changed. ' + \
                f'Old value of "{prefs["sleep_secs"]}" will be kept.'
            warning_dialog(self, "Invalid Time", txt, show=True)

        send_time = self.time_input.text()
        try:
            time.mktime(time.strptime(send_time, TIME_FORMAT))
            prefs['last_send_time'] = send_time
        except:
            txt = f'Could not parse time "{send_time}". Either it is formatted improperly or the year is too high' + \
                f' or low.\n\n Keeping previous time "{prefs["last_send_time"]}" instead.'
            warning_dialog(self, "Invalid Time", txt, show=True)

    def ok_button(self):
        self.save_settings()
        self.accept()

    def cancel_button(self):
        self.reject()
