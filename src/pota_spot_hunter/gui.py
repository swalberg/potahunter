from typing import Protocol

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .domain import Spot
from .rig import RigController
from .spot_state import SpotState


class Logger(Protocol):
    def send_spot(self, spot: Spot) -> None:
        ...


class MainWindow(QMainWindow):
    HEADERS = ["Call", "Freq", "Band", "Mode", "Park", "Comments", "After Trying"]

    def __init__(
        self,
        spots: list[Spot],
        state: SpotState,
        rig: RigController,
        logger: Logger,
        spot_source=None,
        refresh_seconds: int = 60,
    ) -> None:
        super().__init__()
        self.setWindowTitle("POTA Spot Hunter")
        self.all_spots = spots
        self.visible_spots = spots
        self.state = state
        self.rig = rig
        self.logger = logger
        self.spot_source = spot_source
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_spots)
        if self.spot_source is not None:
            self.refresh_timer.start(refresh_seconds * 1000)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(lambda row, column: self.handle_row_activated(row))

        self.status_label = QLabel("Ready")

        root = QWidget()
        layout = QVBoxLayout(root)
        toolbar = QHBoxLayout()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_spots)
        toolbar.addWidget(refresh_button)
        toolbar.addWidget(QPushButton("Settings"))
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
            """
        )
        self.render_spots()

    def refresh_spots(self) -> None:
        if self.spot_source is None:
            self.render_spots()
            return
        try:
            self.all_spots = self.spot_source.fetch()
        except Exception as exc:
            self.status_label.setText(f"POTA refresh failed: {exc}")
            return
        self.status_label.setText(f"Loaded {len(self.all_spots)} POTA spots")
        self.render_spots()

    def render_spots(self) -> None:
        self.visible_spots = self.state.visible_spots(self.all_spots)
        self.table.setRowCount(len(self.visible_spots))
        for row, spot in enumerate(self.visible_spots):
            values = [
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
            self.table.setCellWidget(row, 6, actions)
        self.table.resizeColumnsToContents()

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
        self.table.selectRow(row)
        self.status_label.setText(
            f"{spot.activator} {spot.park} on {spot.frequency_khz / 1000:.3f} {spot.mode} selected"
        )

    def mark_worked(self, spot: Spot) -> None:
        self.state.mark_worked(spot)
        self.status_label.setText(f"{spot.activator} marked worked")
        self.render_spots()

    def mark_cant_hear(self, spot: Spot) -> None:
        self.state.mark_cant_hear(spot)
        self.status_label.setText(f"{spot.activator} ignored temporarily")
        self.render_spots()
