"""Encoder tuning UI module.

Regroup all required classes to manage the encoder tuning for the FFB Engine.

Module : encoder_tuning_ui
Authors : vincent
"""
import random
import math
import PyQt6.QtGui
import PyQt6.QtCore
import PyQt6.QtWidgets
import PyQt6.QtCharts
import biquad
import base_ui


class AdvancedTweakUI(base_ui.WidgetUI, base_ui.CommunicationHandler):
    """Manage the UI to tune the encoder."""

    NB_SAMPLE_NORMAL_GRAPH = 3000
    NB_SAMPLE_DISPLAY_KEEP = 10

    def __init__(self, parent: "AdvancedTuningDialog" = None, axis_instance: int = 0):
        """Initialize the init with the dialog parent and the axisUI linked on the encoder."""
        base_ui.WidgetUI.__init__(self, parent, "encoder_tune.ui")
        base_ui.CommunicationHandler.__init__(self)
        self.parent_dlg = parent
        self.axis_instance = axis_instance
        self.pushButton_compute.clicked.connect(self.suggest_settings)
        self.pushButton_restoreDefault.clicked.connect(self.restore_default_min_speed)

        self.comboBox_profileSelected.currentIndexChanged.connect(self.change_profile)

        # When spinbox are setted, redraw the graph
        self.spinBox_speedFreq.valueChanged.connect(self.simulate_min_speed)
        self.doubleSpinBox_speedQ.valueChanged.connect(self.simulate_min_speed)
        self.spinBox_accelFreq.valueChanged.connect(self.draw_accel_factor)
        self.doubleSpinBox_accelQ.valueChanged.connect(self.draw_accel_factor)

        # Refresh UI on settings update
        self.spinBox_encRes.valueChanged.connect(self.compute_speed)
        self.spinBox_maxSpeed.valueChanged.connect(self.compute_speed)
        self.spinBox_minDeg.valueChanged.connect(self.compute_speed)
        self.spinBox_minSec.valueChanged.connect(self.compute_speed)

        self.register_callback(
            "axis",
            "cpr",
            self.spinBox_encRes.setValue,
            self.axis_instance,
            int,
        )

        self.register_callback(
            "axis",
            "filterProfile_id",
            self.received_profile,
            self.axis_instance,
            int,
        )

        self.register_callback(
            "axis",
            "filterAccel",
            self.filter_accel_cb,
            self.axis_instance,
        )

        self.register_callback(
            "axis",
            "filterSpeed",
            self.filter_speed_cb,
            self.axis_instance,
        )

        self.min_randomize_value = []
        self.min_speed_detectable = 0
        self.min_speed_wanted = 0
        self.average_sample_toread_min = 0
        self.nb_pulse_at_max_speed = 0
        self.max_speed_deg_sec = 0
        self.first_profile_id = -1

    def filter_accel_cb(self,val):
        """Callback to set accel related filter values"""
        f,q100 = map(float,val.split(":"))
        self.doubleSpinBox_accelQ.setValue(q100 / 100.0)
        self.spinBox_accelFreq.setValue(int(f))

    def filter_speed_cb(self,val):
        """Callback to set speed related filter values"""
        f,q100 = map(float,val.split(":"))
        self.doubleSpinBox_speedQ.setValue(q100 / 100.0)
        self.spinBox_speedFreq.setValue(int(f))

    def setEnabled(self, a0: bool) -> None:  # pylint: disable=unused-argument, invalid-name
        """Enable the item."""
        return super().setEnabled(a0)

    def showEvent(self, a0: PyQt6.QtGui.QShowEvent) -> None:  # pylint: disable=unused-argument, invalid-name
        """Show event, reload the settings and show the settings."""
        self.load_profile()
        return super().showEvent(a0)

    def hideEvent(self, a0) -> None:  # pylint: disable=unused-argument, invalid-name
        """Hide event, hide the dialog."""
        self.log("Axis: closed tuning windows, click on save flash")
        if self.first_profile_id != self.comboBox_profileSelected.currentIndex() :
            msg = PyQt6.QtWidgets.QMessageBox(self)
            msg.setIcon(PyQt6.QtWidgets.QMessageBox.Icon.Information)
            msg.setText("Profile changed !\nDon't forget to save in flash.")
            msg.exec()
        return super().hideEvent(a0)

    def load_profile(self):
        """Load the profile : compute the speed to init the UI and load data from board."""
        self.send_commands(
            "axis",
            ["filterSpeed", "filterAccel","cpr"],
            self.axis_instance
        )
        self.compute_speed()
        self.send_command("axis", "filterProfile_id", self.axis_instance)

    def received_profile(self, profile_idx):
        """Change the combobox value when we received the profile value and load filter settings."""
        self.comboBox_profileSelected.setCurrentIndex(profile_idx)
        self.first_profile_id = profile_idx

    def change_profile(self, idx):
        """Called only when the profile change"""
        self.send_value("axis","filterProfile_id", idx, instance = self.axis_instance)
        
        self.send_commands(
            "axis",
            ["filterSpeed", "filterAccel"],
            self.axis_instance
        )

    def suggest_settings(self):
        """Suggests a profile depending on the entered resolution"""
        enc_resolution = self.spinBox_encRes.value()
        if enc_resolution <= 20000:
            self.comboBox_profileSelected.setCurrentIndex(0)
        elif enc_resolution < 0xffff:
            self.comboBox_profileSelected.setCurrentIndex(1)
        else :
            self.comboBox_profileSelected.setCurrentIndex(2)

    def compute_speed(self):
        """Compute all the factor from the hardware init."""
        enc_resolution = self.spinBox_encRes.value()
        ffb_rate = self.spinBox_ffbRate.value()
        max_speed = self.spinBox_maxSpeed.value()
        min_speed_degree = self.spinBox_minDeg.value()
        min_speed_duration = self.spinBox_minSec.value()

        if min_speed_duration <= 0 or ffb_rate <= 0 or enc_resolution <= 0:
            return # Illegal parameter values

        # compute the min speed detectable by the encoder in rpm : 1 position at the ffb rate
        self.min_speed_detectable = (
            360.0 / enc_resolution
        ) * ffb_rate  # °/s detectable by encoder
        self.min_speed_detectable *= 60.0 / 360
        self.label_minDetectable.setText(f"{self.min_speed_detectable:.4f}")

        # compute the min speed wanted by the user in rpm
        self.min_speed_wanted = (min_speed_degree / 360.0) / (min_speed_duration / 60.0)
        self.label_minWanted.setText(f"{self.min_speed_wanted:.4f}")

        # compute how many sample we need to average to be able to
        # read the minimum speed : smoothing effect on speed
        self.average_sample_toread_min = (
            self.min_speed_detectable / self.min_speed_wanted
        )
        self.average_sample_toread_min = max(1, round(self.average_sample_toread_min))
        self.label_sampleAvg.setText(str(self.average_sample_toread_min))

        # compute the range for max speed
        self.nb_pulse_at_max_speed = (enc_resolution * max_speed) / (60.0 * ffb_rate)
        self.label_maxPulse.setText(f"{self.nb_pulse_at_max_speed:.4f}")

        # init the randomize structure for graph display
        self.min_randomize_value.clear()
        i = 1
        self.max_speed_deg_sec = round(max_speed * 360 / 60)
        nb_pulse_max = round(self.nb_pulse_at_max_speed)
        scale = 1
        if nb_pulse_max != 0 :
            scale = self.max_speed_deg_sec / nb_pulse_max
        while i <= AdvancedTweakUI.NB_SAMPLE_NORMAL_GRAPH:
            rand = round(math.sin(i/200) * random.triangular(-nb_pulse_max, nb_pulse_max, 0))
            self.min_randomize_value.append(rand * scale)
            i += 1
        self.simulate_min_speed()

    def restore_default_min_speed(self):
        """Restore the default min speed."""
        self.load_profile()
        self.spinBox_maxSpeed.setValue(80)
        self.spinBox_minDeg.setValue(15)
        self.spinBox_minSec.setValue(5)
        self.suggest_settings()


    def simulate_min_speed(self):
        """Compute and draw graph when the button."""
        # if self.label_sampleAvg.text() == '0':
        #    self.computeSpeed()
        self.draw_simulation_min()
        self.draw_speed_random()
        self.draw_accel_factor()

    def draw_simulation_min(self):
        """Draw the min curve."""
        avg_samples = int(self.label_sampleAvg.text())
        freq = self.spinBox_speedFreq.value()
        q_factor = self.doubleSpinBox_speedQ.value()
        min_rps = float(self.label_minWanted.text())
        rps = float(self.label_minDetectable.text())

        if q_factor == 0.0 or avg_samples == 0:
            return

        # Chart setup
        chart = PyQt6.QtCharts.QChart()
        chart.setBackgroundRoundness(5)
        chart.setMargins(PyQt6.QtCore.QMargins(0, 0, 0, 0))
        chart.legend().hide()
        chart.setBackgroundBrush(
            PyQt6.QtWidgets.QApplication.instance().palette().window()
        )

        font = PyQt6.QtGui.QFont()
        font.setPixelSize(7)

        chart_x_axis = PyQt6.QtCharts.QValueAxis()
        chart_x_axis.setMax(100)
        chart_x_axis.setLabelsFont(font)
        chart_x_axis.setTitleText("Time (ms)")
        chart_x_axis.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance()
                .palette()
                .dark()
                .color()
                .green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                128,
            )
        )
        chart.addAxis(chart_x_axis, PyQt6.QtCore.Qt.AlignmentFlag.AlignBottom)

        chart_y_axis_forces = PyQt6.QtCharts.QValueAxis()
        chart_y_axis_forces.setMin(0)
        chart_y_axis_forces.setLabelsFont(font)
        chart_y_axis_forces.setTitleText("Min Speed (rpm)")
        chart_y_axis_forces.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance()
                .palette()
                .dark()
                .color()
                .green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                64,
            )
        )
        chart.addAxis(chart_y_axis_forces, PyQt6.QtCore.Qt.AlignmentFlag.AlignLeft)

        for axe in chart.axes():
            axe.setTitleBrush(PyQt6.QtWidgets.QApplication.instance().palette().text())
            axe.setLabelsBrush(PyQt6.QtWidgets.QApplication.instance().palette().text())

        self.graph_min.setChart(chart)

        q_line3 = PyQt6.QtCharts.QLineSeries()
        q_line3.setColor(
            PyQt6.QtGui.QColor(  # White
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance()
                .palette()
                .dark()
                .color()
                .green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                255,
            )
        )
        chart.addSeries(q_line3)
        q_line3.attachAxis(chart_y_axis_forces)
        q_line3.attachAxis(chart_x_axis)

        q_line2 = PyQt6.QtCharts.QLineSeries()
        q_line2.setColor(
            PyQt6.QtGui.QColor(  # magenta
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                0,
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                255,
            )
        )
        chart.addSeries(q_line2)
        q_line2.attachAxis(chart_y_axis_forces)
        q_line2.attachAxis(chart_x_axis)
        local_filter = biquad.Biquad(0, freq / 1000.0, q_factor, 0)
        local_filter.calcBiquad()

        q_line = PyQt6.QtCharts.QLineSeries()
        q_line.setColor(
            PyQt6.QtGui.QColor(  # cyan
                0,
                PyQt6.QtWidgets.QApplication.instance()
                .palette()
                .dark()
                .color()
                .green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                255,
            )
        )
        chart.addSeries(q_line)
        q_line.attachAxis(chart_y_axis_forces)
        q_line.attachAxis(chart_x_axis)

        maxy = 0
        for i in range(100):
            if ((i + 10) % avg_samples) == 0 and i < 80:
                value = rps
            else:
                value = 0
            filtered_value = local_filter.compute(value)
            maxy = max(maxy, value, min_rps)
            q_line3.append(i, min_rps)
            q_line2.append(i, filtered_value)
            q_line.append(i, value)
        chart_y_axis_forces.setMax(maxy * 1.01)

    def draw_speed_random(self):
        """Draw the simulation on a random stream and apply filter."""
        freq = self.spinBox_speedFreq.value()
        q_factor = self.doubleSpinBox_speedQ.value()

        if len(self.min_randomize_value) < 200 or q_factor == 0.0:
            return

        # Chart setup
        chart = PyQt6.QtCharts.QChart()
        chart.setBackgroundRoundness(5)
        chart.setMargins(PyQt6.QtCore.QMargins(0, 0, 0, 0))
        chart.legend().hide()
        chart.setBackgroundBrush(
            PyQt6.QtWidgets.QApplication.instance().palette().window()
        )

        font = PyQt6.QtGui.QFont()
        font.setPixelSize(7)

        chart_x_axis = PyQt6.QtCharts.QValueAxis()
        chart_x_axis.setMax(AdvancedTweakUI.NB_SAMPLE_NORMAL_GRAPH)
        chart_x_axis.setLabelsFont(font)
        chart_x_axis.setTitleText("Time")
        chart_x_axis.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance()
                .palette()
                .dark()
                .color()
                .green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                128,
            )
        )
        chart.addAxis(chart_x_axis, PyQt6.QtCore.Qt.AlignmentFlag.AlignBottom)

        chart_y_axis_forces = PyQt6.QtCharts.QValueAxis()
        chart_y_axis_forces.setMin(0)
        chart_y_axis_forces.setMax(self.max_speed_deg_sec + 10)
        chart_y_axis_forces.setLabelsFont(font)
        chart_y_axis_forces.setTitleText("Speed (°/s)")
        chart_y_axis_forces.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance()
                .palette()
                .dark()
                .color()
                .green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                64,
            )
        )
        chart.addAxis(chart_y_axis_forces, PyQt6.QtCore.Qt.AlignmentFlag.AlignLeft)

        for axe in chart.axes():
            axe.setTitleBrush(PyQt6.QtWidgets.QApplication.instance().palette().text())
            axe.setLabelsBrush(PyQt6.QtWidgets.QApplication.instance().palette().text())

        self.graph_random.setChart(chart)

        q_line = PyQt6.QtCharts.QLineSeries()
        q_line.setColor(
            PyQt6.QtGui.QColor(  # cyan
                0,
                PyQt6.QtWidgets.QApplication.instance()
                .palette()
                .dark()
                .color()
                .green(),
                0,
                255,
            )
        )
        chart.addSeries(q_line)
        q_line.attachAxis(chart_y_axis_forces)
        q_line.attachAxis(chart_x_axis)

        q_line2 = PyQt6.QtCharts.QLineSeries()
        q_line2.setColor(
            PyQt6.QtGui.QColor(  # magenta
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                0,
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                255,
            )
        )
        chart.addSeries(q_line2)
        q_line2.attachAxis(chart_y_axis_forces)
        q_line2.attachAxis(chart_x_axis)
        local_filter = biquad.Biquad(0, freq / 1000.0, q_factor, 0)
        local_filter.calcBiquad()

        max_filter = 0
        max_value = 0
        for i in range(AdvancedTweakUI.NB_SAMPLE_NORMAL_GRAPH):
            filter_result = local_filter.compute(self.min_randomize_value[i])
            max_filter = max(max_filter, filter_result)
            max_value = max(max_value, self.min_randomize_value[i])
            if i % AdvancedTweakUI.NB_SAMPLE_DISPLAY_KEEP == 0:
                q_line.append(i, max_value)
                q_line2.append(i, max_filter)
                max_value = 0
                max_filter = 0

    def draw_accel_factor(self):
        """Draw the simulation for the accel on the speed random stream and apply filter."""
        freq = self.spinBox_accelFreq.value()
        q_factor = self.doubleSpinBox_accelQ.value()

        if len(self.min_randomize_value) < 200 or q_factor == 0.0:
            return

        # Chart setup
        chart = PyQt6.QtCharts.QChart()
        chart.setBackgroundRoundness(5)
        chart.setMargins(PyQt6.QtCore.QMargins(0, 0, 0, 0))
        chart.legend().hide()
        chart.setBackgroundBrush(
            PyQt6.QtWidgets.QApplication.instance().palette().window()
        )

        font = PyQt6.QtGui.QFont()
        font.setPixelSize(7)

        chart_x_axis = PyQt6.QtCharts.QValueAxis()
        chart_x_axis.setMax(AdvancedTweakUI.NB_SAMPLE_NORMAL_GRAPH)
        chart_x_axis.setLabelsFont(font)
        chart_x_axis.setTitleText("Time")
        chart_x_axis.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance()
                .palette()
                .dark()
                .color()
                .green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                128,
            )
        )
        chart.addAxis(chart_x_axis, PyQt6.QtCore.Qt.AlignmentFlag.AlignBottom)

        chart_y_axis_forces = PyQt6.QtCharts.QValueAxis()
        max_range = (self.max_speed_deg_sec + 1) * 1000
        chart_y_axis_forces.setMin(-max_range)
        chart_y_axis_forces.setMax(max_range)
        chart_y_axis_forces.setLabelsFont(font)
        chart_y_axis_forces.setTitleText("Accel (°/s2)")
        chart_y_axis_forces.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance()
                .palette()
                .dark()
                .color()
                .green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                64,
            )
        )
        chart.addAxis(chart_y_axis_forces, PyQt6.QtCore.Qt.AlignmentFlag.AlignLeft)

        for axe in chart.axes():
            axe.setTitleBrush(PyQt6.QtWidgets.QApplication.instance().palette().text())
            axe.setLabelsBrush(PyQt6.QtWidgets.QApplication.instance().palette().text())

        self.graph_accel.setChart(chart)

        q_line = PyQt6.QtCharts.QLineSeries()
        q_line.setColor(
            PyQt6.QtGui.QColor(  # cyan
                0,
                PyQt6.QtWidgets.QApplication.instance()
                .palette()
                .dark()
                .color()
                .green(),
                0,
                255,
            )
        )
        chart.addSeries(q_line)
        q_line.attachAxis(chart_y_axis_forces)
        q_line.attachAxis(chart_x_axis)

        q_line2 = PyQt6.QtCharts.QLineSeries()
        q_line2.setColor(
            PyQt6.QtGui.QColor(  # magenta
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                0,
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                255,
            )
        )
        chart.addSeries(q_line2)
        q_line2.attachAxis(chart_y_axis_forces)
        q_line2.attachAxis(chart_x_axis)
        local_filter = biquad.Biquad(0, freq / 1000.0, q_factor, 0)
        local_filter.calcBiquad()

        for i in range(AdvancedTweakUI.NB_SAMPLE_NORMAL_GRAPH):
            if i > 1:
                data = self.min_randomize_value[i] - self.min_randomize_value[i - 1] 
            else:
                data = 0
            data = data * 1000
            filter_response = local_filter.compute(data)
            if i % AdvancedTweakUI.NB_SAMPLE_DISPLAY_KEEP == 0:
                q_line.append(i, data)
                q_line2.append(i, filter_response)

class AdvancedTuningDialog(PyQt6.QtWidgets.QDialog):
    """Manage the dialog box for the encoder UI.

    The dialogbox is open in non modal item.
    """

    def __init__(self, parent_ui: "axis_ui.AxisUI" = None, axis_instance: int = 0):
        """Construct the with an axis, the tuning is by axis."""
        PyQt6.QtWidgets.QDialog.__init__(self, parent_ui)
        self.axis_ui = parent_ui
        self.advanced_tweak_ui = AdvancedTweakUI(self, axis_instance)
        self.layout = PyQt6.QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.advanced_tweak_ui)
        self.setLayout(self.layout)
        self.setWindowTitle("Advanced encoder tuning")
        self.setModal(True)

    def setEnabled(self, a0: bool) -> None:  # pylint: disable=unused-argument, invalid-name
        """Enable all the widget in the tuned UI."""
        self.advanced_tweak_ui.setEnabled(a0)
        return super().setEnabled(a0)

    def display(self):
        """Show the dialog box for the tuned UI."""
        self.show()
        self.raise_()
        self.activateWindow()
