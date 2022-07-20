"""effect monitoring module for UI.

Regroup all required classes to monitor the effect in a graph.

Module : effects_graph_ui
Authors : vincent
"""
import json
import PyQt6.QtWidgets
import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtCharts
import base_ui


class EffectsGraphUI(base_ui.WidgetUI, base_ui.CommunicationHandler):
    """Manage the UI graph and the event."""

    def __init__(self, dlg=None):
        """Init graph component and communication tools."""
        base_ui.WidgetUI.__init__(self, dlg, "effects_graph.ui")
        base_ui.CommunicationHandler.__init__(self)

        self.max_datapoints = 1000
        self.max_datapoints_visible_time = 30

        self.start_time = 0
        self.chart_last_x = 0

        # Chart setup
        self.chart = PyQt6.QtCharts.QChart()
        self.chart.setBackgroundRoundness(5)
        self.chart.setMargins(PyQt6.QtCore.QMargins(0, 0, 0, 0))

        self.chart_xaxis = PyQt6.QtCharts.QValueAxis()
        self.chart_xaxis.setMax(10)
        self.chart_xaxis.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                128,
            )
        )
        self.chart.addAxis(self.chart_xaxis, PyQt6.QtCore.Qt.AlignmentFlag.AlignBottom)

        self.chart_yaxis_forces = PyQt6.QtCharts.QValueAxis()
        self.chart_yaxis_forces.setMin(-32767)
        self.chart_yaxis_forces.setMax(32767)
        self.chart_yaxis_forces.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                64,
            )
        )
        self.chart.addAxis(
            self.chart_yaxis_forces, PyQt6.QtCore.Qt.AlignmentFlag.AlignLeft
        )

        self.chart.legend().setLabelBrush(
            PyQt6.QtWidgets.QApplication.instance().palette().text()
        )
        for ax in self.chart.axes():
            ax.setLabelsBrush(
                PyQt6.QtWidgets.QApplication.instance().palette().text()
            )

        self.chart.setBackgroundBrush(PyQt6.QtWidgets.QApplication.instance().palette().window())
        self.graphWidget_Forces.setChart(self.chart)

        # Setup the Qline for the the effect
        effect_name = [
            "Constant",
            "Ramp",
            "Square",
            "Sine",
            "Triangle",
            "Saw Tooth Up",
            "Saw Tooth Down",
            "Spring",
            "Damper",
            "Inertia",
            "Friction",
            "Custom",
        ]
        effect_color = [
            PyQt6.QtGui.QColorConstants.DarkBlue,
            PyQt6.QtGui.QColorConstants.DarkCyan,
            PyQt6.QtGui.QColorConstants.DarkGray,
            PyQt6.QtGui.QColorConstants.DarkGreen,
            PyQt6.QtGui.QColorConstants.DarkMagenta,
            PyQt6.QtGui.QColorConstants.DarkRed,
            PyQt6.QtGui.QColorConstants.DarkYellow,
            PyQt6.QtGui.QColorConstants.Blue,
            PyQt6.QtGui.QColorConstants.Red,
            PyQt6.QtGui.QColorConstants.Green,
            PyQt6.QtGui.QColorConstants.Yellow,
            PyQt6.QtGui.QColorConstants.Black,
        ]
        self.lines = []
        for i in range(12):
            q_line = PyQt6.QtCharts.QLineSeries()
            q_line.setColor(effect_color[i])
            q_line.setName(effect_name[i])
            self.lines.append(q_line)
            self.chart.addSeries(q_line)
            q_line.attachAxis(self.chart_yaxis_forces)
            q_line.attachAxis(self.chart_xaxis)

        # Setup the timer to get data
        self.timer = PyQt6.QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_timer)  # pylint: disable=no-value-for-parameter

    def showEvent(self, event):  # pylint: disable=invalid-name, unused-argument
        """Display the UI and start calling board  for data."""
        self.init_ui()
        self.timer.start(100)

    # Tab is hidden
    def hideEvent(self, event):  # pylint: disable=invalid-name, unused-argument
        """Stop the timer on close event."""
        self.timer.stop()

    def update_timer(self):
        """Call the board to get instant data."""
        self.get_value_async("fx", "effectsForces", self.display_data)

    def display_data(self, data):
        """Decode the json data received."""
        json_data = json.loads("[" + data.replace('\n',',') + "]")
        if len(json_data) == 12:
            self.update_current(json_data)

    def init_ui(self):
        """Init the ui by clear all data in series."""
        # clear graph
        self.start_time = PyQt6.QtCore.QTime.currentTime()
        self.chart_last_x = 0
        for i in range(12):
            self.lines[i].clear()

    def update_current(self, forces):
        """Display on graph the response of the board."""
        try:
            self.chart_last_x = (
                self.start_time.msecsTo(PyQt6.QtCore.QTime.currentTime()) / 1000
            )
            index = 0
            for i in forces:
                self.lines[index].append(self.chart_last_x, forces[index])
                if self.lines[index].count() > self.max_datapoints:
                    self.lines[index].remove(0)
                index += 1

            self.chart_xaxis.setMax(self.chart_last_x)
            self.chart_xaxis.setMin(
                max(
                    self.lines[0].at(0).x(),
                    max(0, self.chart_last_x - self.max_datapoints_visible_time),
                )
            )

        except Exception as exception:  # pylint: disable broad-except
            self.log("Monitor can't parse data: " + str(exception))


class EffectsGraphDialog(PyQt6.QtWidgets.QDialog):
    """Manage the dialog box to display the UI."""

    def __init__(self, main=None):
        """Create the dialogbox."""
        PyQt6.QtWidgets.QDialog.__init__(self, main)
        self.graph_ui = EffectsGraphUI(self)
        self.layout = PyQt6.QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.graph_ui)
        self.setLayout(self.layout)
        self.setWindowTitle("Effects graphics")

    def setEnabled(self, a0: bool) -> None:  # pylint: disable=invalid-name
        """Enable the UI, or disable it depends on message."""
        self.graph_ui.setEnabled(a0)
        return super().setEnabled(a0)

    def display(self):
        """Display the dialogbox."""
        self.show()
        self.raise_()
        self.activateWindow()
