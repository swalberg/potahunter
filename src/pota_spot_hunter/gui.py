from datetime import datetime, timezone
from typing import Protocol

from PySide6.QtCore import QEvent, QObject, QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .domain import Spot
from .rig import RigController
from .settings import AppSettings, save_settings
from .spot_state import SpotState


class Logger(Protocol):
    def send_spot(self, spot: Spot) -> None:
        ...

    def log_qso(self, spot: Spot, rst_sent: str, rst_received: str | None = None) -> None:
        ...


class SpotSource(Protocol):
    def fetch(self) -> list[Spot]:
        ...


class RefreshWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, spot_source: SpotSource) -> None:
        super().__init__()
        self.spot_source = spot_source

    def run(self) -> None:
        try:
            self.finished.emit(self.spot_source.fetch())
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    HEADERS = ["Age", "Call", "Freq", "Band", "Mode", "Park", "Comments", "After Trying"]

    def __init__(
        self,
        spots: list[Spot],
        state: SpotState,
        rig: RigController,
        logger: Logger,
        spot_source: SpotSource | None = None,
        refresh_seconds: int = 60,
        settings: AppSettings | None = None,
        settings_path=None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("POTA Spot Hunter")
        self.all_spots = spots
        self.visible_spots = spots
        self.state = state
        self.rig = rig
        self.logger = logger
        self.selected_spot_key = None
        self.show_qrt = False
        self.selected_modes: set[str] = set()
        self.mode_checkboxes: dict[str, QCheckBox] = {}
        self.spot_source = spot_source
        self.settings = settings or AppSettings(
            refresh_seconds=refresh_seconds,
            ignore_minutes=state.ignore_minutes,
        )
        self.settings_path = settings_path
        self.refresh_thread: QThread | None = None
        self.refresh_worker: RefreshWorker | None = None
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_spots)
        if self.spot_source is not None:
            self.refresh_timer.start(self.settings.refresh_seconds * 1000)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(lambda row, column: self.handle_row_activated(row))
        self.table.installEventFilter(self)

        self.status_label = QLabel("Ready")

        root = QWidget()
        layout = QVBoxLayout(root)
        toolbar = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_spots)
        toolbar.addWidget(self.refresh_button)
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        toolbar.addWidget(self.settings_button)
        self.show_qrt_checkbox = QCheckBox("Show QRT")
        self.show_qrt_checkbox.setChecked(self.show_qrt)
        self.show_qrt_checkbox.toggled.connect(self.set_show_qrt)
        toolbar.addWidget(self.show_qrt_checkbox)
        self.mode_filter_label = QLabel("Modes:")
        toolbar.addWidget(self.mode_filter_label)
        self.mode_filter_layout = QHBoxLayout()
        toolbar.addLayout(self.mode_filter_layout)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        layout.addWidget(self.table)
        layout.addWidget(self.status_label)
        self.setCentralWidget(root)

        self.setStyleSheet(
            """
            QHeaderView::section {
                background: #eef2f7;
                color: #111827;
                font-weight: 600;
                padding: 6px;
            }
            QTableWidget::item:selected {
                background: #dbeafe;
                color: #111827;
            }
            QPushButton {
                background: #ffffff;
                color: #111827;
                border: 1px solid #9ca3af;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background: #f3f4f6;
                border-color: #6b7280;
            }
            QPushButton:pressed {
                background: #e5e7eb;
                color: #111827;
            }
            QCheckBox {
                color: #111827;
                background: #ffffff;
                border: 1px solid #9ca3af;
                border-radius: 4px;
                padding: 4px 8px;
                spacing: 4px;
            }
            QCheckBox:hover {
                background: #f3f4f6;
                border-color: #6b7280;
            }
            QCheckBox::indicator {
                width: 12px;
                height: 12px;
                border: 1px solid #6b7280;
                background: #ffffff;
            }
            QCheckBox::indicator:checked {
                background: #2563eb;
                border-color: #1d4ed8;
            }
            QLabel {
                color: #111827;
            }
            """
        )
        self.render_spots()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.table and event.type() == QEvent.Type.KeyPress:
            if (
                event.key() == Qt.Key.Key_W
                and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            ):
                self.complete_selected_qso()
                return True
            handlers = {
                Qt.Key.Key_J: self.move_selection_down,
                Qt.Key.Key_Down: self.move_selection_down,
                Qt.Key.Key_K: self.move_selection_up,
                Qt.Key.Key_Up: self.move_selection_up,
                Qt.Key.Key_Space: self.activate_selected_spot,
                Qt.Key.Key_W: self.mark_selected_worked,
                Qt.Key.Key_N: self.mark_selected_cant_hear,
            }
            handler = handlers.get(event.key())
            if handler is not None:
                handler()
                return True
        return super().eventFilter(watched, event)

    def selected_or_first_row(self) -> int | None:
        if not self.visible_spots:
            return None
        row = self.table.currentRow() if self.has_spot_selection() else 0
        if row < 0 or row >= len(self.visible_spots):
            row = 0
        self.table.selectRow(row)
        return row

    def has_spot_selection(self) -> bool:
        return (
            self.table.selectionModel().hasSelection()
            and 0 <= self.table.currentRow() < len(self.visible_spots)
        )

    def move_selection_down(self) -> None:
        if not self.has_spot_selection():
            self.selected_or_first_row()
            self.table.setFocus()
            return
        row = self.selected_or_first_row()
        if row is None:
            return
        self.table.selectRow(min(row + 1, len(self.visible_spots) - 1))
        self.table.setFocus()

    def move_selection_up(self) -> None:
        if not self.has_spot_selection():
            self.selected_or_first_row()
            self.table.setFocus()
            return
        row = self.selected_or_first_row()
        if row is None:
            return
        self.table.selectRow(max(row - 1, 0))
        self.table.setFocus()

    def activate_selected_spot(self) -> None:
        row = self.selected_or_first_row()
        if row is None:
            return
        self.handle_row_activated(row)

    def mark_selected_worked(self) -> None:
        row = self.selected_or_first_row()
        if row is None:
            return
        self.mark_worked(self.visible_spots[row])

    def mark_selected_cant_hear(self) -> None:
        row = self.selected_or_first_row()
        if row is None:
            return
        self.mark_cant_hear(self.visible_spots[row])

    def default_qso_report(self, spot: Spot) -> str:
        if spot.mode == "CW":
            return "599"
        return "59"

    def complete_selected_qso(self) -> None:
        row = self.selected_or_first_row()
        if row is None:
            return
        spot = self.visible_spots[row]
        dialog = CompleteQsoDialog(spot, self.default_qso_report(spot), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        rst_sent, rst_received = dialog.reports()
        try:
            self.logger.log_qso(spot, rst_sent, rst_received)
        except Exception as exc:
            self.status_label.setText(f"{spot.activator}: {exc}")
            return
        self.state.mark_worked(spot)
        if self.selected_spot_key == spot.key:
            self.selected_spot_key = None
        self.status_label.setText(f"{spot.activator} logged and marked worked")
        self.render_spots()

    def format_spot_age(self, spot: Spot, now: datetime | None = None) -> str:
        if spot.spotted_at is None:
            return ""
        current = now or datetime.now(timezone.utc)
        spotted_at = spot.spotted_at
        if spotted_at.tzinfo is None:
            spotted_at = spotted_at.replace(tzinfo=timezone.utc)
        elapsed_seconds = max(
            0,
            int((current - spotted_at.astimezone(timezone.utc)).total_seconds()),
        )
        elapsed_minutes = elapsed_seconds // 60
        if elapsed_minutes < 60:
            return f"{elapsed_minutes}m"
        hours = elapsed_minutes // 60
        minutes = elapsed_minutes % 60
        return f"{hours}h {minutes}m"

    def sort_spots_by_age(self, spots: list[Spot]) -> list[Spot]:
        def spotted_at_utc(spot: Spot) -> datetime:
            if spot.spotted_at is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            if spot.spotted_at.tzinfo is None:
                return spot.spotted_at.replace(tzinfo=timezone.utc)
            return spot.spotted_at.astimezone(timezone.utc)

        return sorted(
            spots,
            key=lambda spot: (spot.spotted_at is not None, spotted_at_utc(spot)),
            reverse=True,
        )

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            new_settings = dialog.to_settings()
            save_settings(new_settings, self.settings_path)
        except Exception as exc:
            self.status_label.setText(f"Settings error: {exc}")
            return
        self.settings = new_settings
        self.state.ignore_minutes = self.settings.ignore_minutes
        if self.spot_source is not None:
            self.refresh_timer.start(self.settings.refresh_seconds * 1000)
        self.status_label.setText("Settings saved")

    def refresh_spots(self) -> None:
        if self.spot_source is None:
            self.render_spots()
            return
        if self.refresh_thread is not None:
            return
        self.refresh_button.setEnabled(False)
        self.status_label.setText("Refreshing POTA spots...")
        self.refresh_thread = QThread(self)
        self.refresh_worker = RefreshWorker(self.spot_source)
        self.refresh_worker.moveToThread(self.refresh_thread)
        self.refresh_thread.started.connect(self.refresh_worker.run)
        self.refresh_worker.finished.connect(self.handle_refresh_success)
        self.refresh_worker.failed.connect(self.handle_refresh_failure)
        self.refresh_worker.finished.connect(self.refresh_thread.quit)
        self.refresh_worker.failed.connect(self.refresh_thread.quit)
        self.refresh_thread.finished.connect(self.refresh_worker.deleteLater)
        self.refresh_thread.finished.connect(self.refresh_thread.deleteLater)
        self.refresh_thread.finished.connect(self._clear_refresh_worker)
        self.refresh_thread.start()

    def handle_refresh_success(self, spots: list[Spot]) -> None:
        self.all_spots = spots
        self.status_label.setText(f"Loaded {len(self.all_spots)} POTA spots")
        self.refresh_button.setEnabled(True)
        self.render_spots()

    def handle_refresh_failure(self, message: str) -> None:
        self.status_label.setText(f"POTA refresh failed: {message}")
        self.refresh_button.setEnabled(True)

    def _clear_refresh_worker(self) -> None:
        self.refresh_thread = None
        self.refresh_worker = None

    def closeEvent(self, event) -> None:
        if self.refresh_thread is not None:
            self.refresh_thread.quit()
            if not self.refresh_thread.wait(12000):
                event.ignore()
                return
            self._clear_refresh_worker()
            self.refresh_button.setEnabled(True)
        self.refresh_timer.stop()
        super().closeEvent(event)

    def render_spots(self) -> None:
        self.sync_mode_filters()
        self.visible_spots = self.sort_spots_by_age(
            self.filter_spots(self.state.visible_spots(self.all_spots))
        )
        self.table.setRowCount(len(self.visible_spots))
        for row, spot in enumerate(self.visible_spots):
            values = [
                self.format_spot_age(spot),
                spot.activator,
                f"{spot.frequency_khz / 1000:.3f}",
                spot.band,
                spot.mode,
                spot.park,
                spot.comments,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, column, item)

            worked_button = QPushButton("Worked")
            worked_button.clicked.connect(lambda checked=False, s=spot: self.mark_worked(s))
            cant_hear_button = QPushButton("Can't Hear")
            cant_hear_button.clicked.connect(lambda checked=False, s=spot: self.mark_cant_hear(s))
            actions = QWidget()
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.addWidget(worked_button)
            action_layout.addWidget(cant_hear_button)
            self.table.setCellWidget(row, 7, actions)
        self.table.resizeColumnsToContents()
        self.restore_selected_spot()
        self.table.setFocus()

    def filter_spots(self, spots: list[Spot]) -> list[Spot]:
        return [
            spot
            for spot in spots
            if (self.show_qrt or not spot.is_qrt)
            and (not self.mode_checkboxes or spot.mode in self.selected_modes)
        ]

    def sync_mode_filters(self) -> None:
        for mode in sorted({spot.mode for spot in self.all_spots}):
            if mode in self.mode_checkboxes:
                continue
            self.selected_modes.add(mode)
            checkbox = QCheckBox(mode)
            checkbox.setChecked(True)
            checkbox.toggled.connect(
                lambda checked, selected_mode=mode: self.set_mode_visible(selected_mode, checked)
            )
            self.mode_checkboxes[mode] = checkbox
            self.mode_filter_layout.addWidget(checkbox)

    def set_show_qrt(self, checked: bool) -> None:
        self.show_qrt = checked
        self.render_spots()

    def set_mode_visible(self, mode: str, checked: bool) -> None:
        if checked:
            self.selected_modes.add(mode)
        else:
            self.selected_modes.discard(mode)
        self.render_spots()

    def restore_selected_spot(self) -> None:
        if self.selected_spot_key is None:
            self.table.clearSelection()
            return
        for row, spot in enumerate(self.visible_spots):
            if spot.key == self.selected_spot_key:
                self.table.selectRow(row)
                return
        self.table.clearSelection()

    def handle_row_activated(self, row: int) -> None:
        if row < 0 or row >= len(self.visible_spots):
            return
        spot = self.visible_spots[row]
        try:
            self.rig.tune(spot.frequency_khz, spot.mode)
            self.logger.send_spot(spot)
        except Exception as exc:
            self.status_label.setText(f"{spot.activator}: {exc}")
            return
        self.selected_spot_key = spot.key
        self.table.selectRow(row)
        self.status_label.setText(
            f"{spot.activator} {spot.park} on {spot.frequency_khz / 1000:.3f} {spot.mode} selected"
        )

    def mark_worked(self, spot: Spot) -> None:
        self.state.mark_worked(spot)
        if self.selected_spot_key == spot.key:
            self.selected_spot_key = None
        self.status_label.setText(f"{spot.activator} marked worked")
        self.render_spots()

    def mark_cant_hear(self, spot: Spot) -> None:
        self.state.mark_cant_hear(spot)
        if self.selected_spot_key == spot.key:
            self.selected_spot_key = None
        self.status_label.setText(f"{spot.activator} ignored temporarily")
        self.render_spots()


class CompleteQsoDialog(QDialog):
    def __init__(self, spot: Spot, default_report: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Log {spot.activator}")

        self.rst_sent = QLineEdit(default_report)
        self.rst_received = QLineEdit(default_report)
        self.rst_sent.selectAll()
        self.rst_sent.setFocus()
        self.sent_label = QLabel("Sent RST")
        self.received_label = QLabel("Received RST")
        for label in (self.sent_label, self.received_label):
            label.setMinimumWidth(90)
            label.setStyleSheet("color: #111827;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow(self.sent_label, self.rst_sent)
        layout.addRow(self.received_label, self.rst_received)
        layout.addRow(buttons)

    def reports(self) -> tuple[str, str]:
        return self.rst_sent.text().strip(), self.rst_received.text().strip()


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.setWindowTitle("Settings")

        self.refresh_seconds = QSpinBox()
        self.refresh_seconds.setRange(1, 3600)
        self.refresh_seconds.setValue(settings.refresh_seconds)

        self.ignore_minutes = QSpinBox()
        self.ignore_minutes.setRange(0, 1440)
        self.ignore_minutes.setValue(settings.ignore_minutes)

        self.logger_host = QLineEdit(settings.logger_host)

        self.logger_port = QSpinBox()
        self.logger_port.setRange(1, 65535)
        self.logger_port.setValue(settings.logger_port)

        self.omnirig_rig_number = QSpinBox()
        self.omnirig_rig_number.setRange(1, 2)
        self.omnirig_rig_number.setValue(settings.omnirig_rig_number)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow("Refresh seconds", self.refresh_seconds)
        layout.addRow("Ignore minutes", self.ignore_minutes)
        layout.addRow("Logger host", self.logger_host)
        layout.addRow("Logger port", self.logger_port)
        layout.addRow("OmniRig rig number", self.omnirig_rig_number)
        layout.addRow(buttons)

    def to_settings(self) -> AppSettings:
        return AppSettings(
            refresh_seconds=self.refresh_seconds.value(),
            ignore_minutes=self.ignore_minutes.value(),
            logger_host=self.logger_host.text(),
            logger_port=self.logger_port.value(),
            omnirig_rig_number=self.omnirig_rig_number.value(),
        ).validate()
