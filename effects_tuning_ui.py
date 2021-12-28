"""Encoder tuning UI module.

Regroup all required classes to manage the encoder tuning for the FFB Engine.

Module : encoder_tuning_ui
Authors : vincent
"""
import math
import random
import PyQt6.QtGui
import PyQt6.QtCore
import PyQt6.QtWidgets
import PyQt6.QtCharts
import biquad
import base_ui

class AdvancedTweakUI(base_ui.WidgetUI, base_ui.CommunicationHandler):
    """Manage the UI to tune the encoder."""

    def __init__(
        self, parent: 'AdvancedTuningDialog' = None, axis_instance: int = 0
    ):
        """Initialize the init with the dialog parent and the axisUI linked on the encoder."""
        base_ui.WidgetUI.__init__(self, parent, "encoder_tune.ui")
        base_ui.CommunicationHandler.__init__(self)
        self.parent_dlg = parent
        self.axis_instance = axis_instance
        self.pushButton_loadSettings.clicked.connect(self.load_settings)
        self.pushButton_compute.clicked.connect(self.compute_speed)
        self.pushButton_restoreDefault.clicked.connect(self.restore_default_min_speed)
        self.pushButton_restoreDefaultEffect.clicked.connect(self.simulate_effect)
        self.pushButton_save.clicked.connect(self.save_settings)

        self.spinBox_speedFreq.valueChanged.connect(self.simulate_min_speed)
        self.doubleSpinBox_speedQ.valueChanged.connect(self.simulate_min_speed)
        self.doubleSpinBox_speedScaler.valueChanged.connect(self.simulate_min_speed)

        self.spinBox_pctFrictionRampUp.valueChanged.connect(self.draw_all_effects)

        self.register_callback(
            "axis",
            "filterSpeed_freq",
            self.spinBox_speedFreq.setValue,
            self.axis_instance,
            int,
        )
        self.register_callback(
            "axis",
            "filterSpeed_q",
            lambda q: self.doubleSpinBox_speedQ.setValue(q / 100.0),
            self.axis_instance,
            int,
        )
        self.register_callback(
            "axis",
            "scaleSpeed",
            self.doubleSpinBox_speedScaler.setValue,
            self.axis_instance,
            int,
        )
        self.register_callback(
            "fx",
            "frictionPctSpeedToRampup",
            self.spinBox_pctFrictionRampUp.setValue,
            0,
            int,
        )

        self.min_randomize_value = []
        self.min_speed_detectable = 0
        self.min_speed_wanted = 0
        self.average_sample_toread_min = 0
        self.nb_pulse_at_max_speed = 0
        self.speed_scaler = 0
        self.min_speed_rescale = 0

    def setEnabled(self, a0: bool) -> None: # pylint: disable=unused-argument, invalid-name
        """Enable the item."""
        return super().setEnabled(a0)

    def showEvent(self, a0: PyQt6.QtGui.QShowEvent) -> None: # pylint: disable=unused-argument, invalid-name
        """Show event, reload the settings and show the settings."""
        self.load_settings()
        return super().showEvent(a0)

    def hideEvent(self, a0) -> None: # pylint: disable=unused-argument, invalid-name
        """Hide event, hide the dialog."""
        return super().hideEvent(a0)

    def load_settings(self):
        """Load the settings : compute the speed to init the UI and load data from board."""
        self.compute_speed()
        self.send_commands(
            "axis",
            ["filterSpeed_freq", "filterSpeed_q", "scaleSpeed"],
            self.axis_instance,
        )
        self.send_command("fx", "frictionPctSpeedToRampup", self.axis_instance)

    def save_settings(self):
        """Save the data in the board."""
        freq = self.spinBox_speedFreq.value()
        q_factor = self.doubleSpinBox_speedQ.value()
        speedscaler = self.doubleSpinBox_speedScaler.value()
        pctfric = self.spinBox_pctFrictionRampUp.value()
        self.send_value("axis", "filterSpeed_freq", freq, instance=self.axis_instance)
        self.send_value(
            "axis", "filterSpeed_q", round(q_factor * 100), instance=self.axis_instance
        )
        self.send_value(
            "axis", "scaleSpeed", round(speedscaler), instance=self.axis_instance
        )
        self.send_value("fx", "frictionPctSpeedToRampup", pctfric)
        self.parent_dlg.close()

    def compute_speed(self):
        """Compute all the factor from the hardware init."""
        enc_resolution = self.spinBox_encRes.value()
        #wheel_range = self.spinBox_whRange.value()     Not used the init
        ffb_rate = self.spinBox_ffbRate.value()
        max_speed = self.spinBox_maxSpeed.value()
        min_speed_degree = self.spinBox_minDeg.value()
        min_speed_duration = self.spinBox_minSec.value()

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

        # if the number of sample is 1, speed don't need to be smooth reduce smoothing (250)
        if self.average_sample_toread_min == 1:
            self.spinBox_speedFreq.setValue(250)
            self.doubleSpinBox_speedQ.setValue(0.55)
        else:
            self.spinBox_speedFreq.setValue(25)
            self.doubleSpinBox_speedQ.setValue(0.6)
            # if freq = 25, smoothing is on 35 samples, max value is 0,063
            # if freq = 50, smoothing is on 18 samples , max value is 0,121
            # if freq = 100, smoothing is on 9 samples , max value is 0,243
            # TODO: brainstorm on how have to be the filtering

        # compute the scaler for max speed
        self.nb_pulse_at_max_speed = (enc_resolution * max_speed) / (60.0 * ffb_rate)
        self.label_maxPulse.setText(f"{self.nb_pulse_at_max_speed:.4f}")

        self.speed_scaler = (32767 / self.nb_pulse_at_max_speed) * 0.99
        self.doubleSpinBox_speedScaler.setValue(self.speed_scaler)

        # init the randomize structure for graph display
        self.min_randomize_value.clear()
        i = 1
        while i <= 200:
            self.min_randomize_value.append(
                random.randint(0, round(self.nb_pulse_at_max_speed))
            )
            i += 1
        self.simulate_min_speed()

    def compute_speed_effect(self):
        """Compute the speed law pass filter."""
        rps = float(self.label_minDetectable.text())

        # compute the rampup for friction at low speed to smooth torque and remove oscillation
        if (
            self.doubleSpinBox_speedQ.value() == 0
            or self.average_sample_toread_min == 0
        ):
            return

        # simulate a low signal and get the max value of the filter's output
        local_filter = biquad.Biquad(
            0,
            self.spinBox_speedFreq.value() / 1000.0,
            self.doubleSpinBox_speedQ.value(),
            0,
        )
        local_filter.calcBiquad()
        minsample = 0
        for i in range(50):
            if ((i + 10) % self.average_sample_toread_min) == 0 and i < 80:
                value = rps
            else:
                value = 0
            filtered_value = local_filter.compute(value)
            minsample = max(minsample, filtered_value)
        self.min_speed_rescale = minsample * self.doubleSpinBox_speedScaler.value()
        self.label_minSpeedRescale.setText(f"{self.min_speed_rescale:.4f}")

        # comute the min
        signal_to_not_oscillate = 0.01 / 30
        phase_rad = math.asin((signal_to_not_oscillate * 2) - 1)
        pct_friction = round(
            self.min_speed_rescale * (100 / 32767) * (1 / (0.5 + phase_rad / math.pi))
        )
        pct_friction = max(pct_friction, 3)
        self.spinBox_pctFrictionRampUp.setValue(pct_friction)

    def restore_default_min_speed(self):
        """Restore the default min speed."""
        self.spinBox_speedFreq.setValue(25.0)
        self.doubleSpinBox_speedQ.setValue(0.6)
        self.doubleSpinBox_speedScaler.setValue(40)
        self.draw_simulation_min()
        self.draw_simulation_random()
        self.simulate_effect()
        self.spinBox_pctFrictionRampUp.setValue(5)
        self.draw_all_effects()

    def simulate_min_speed(self):
        """Compute and draw graph when the button."""
        # if self.label_sampleAvg.text() == '0':
        #    self.computeSpeed()
        self.draw_simulation_min()
        self.draw_simulation_random()
        self.simulate_effect()

    def simulate_effect(self):
        """Compute and draw the effect : inertia and damper."""
        # compute the speedEffect when a simulation is done because filter change
        self.compute_speed_effect()
        self.draw_all_effects()

    def draw_all_effects(self):
        """Draw the effects graph response."""
        scaler = round(self.doubleSpinBox_speedScaler.value())
        max_encoder_range = round(self.nb_pulse_at_max_speed * scaler)
        max_encoder_range = min(max_encoder_range, 32767)
        self.draw_effect(
            -32767,
            32767,
            -max_encoder_range,
            max_encoder_range,
            300,
            self.graph_effects,
        )
        max_encoder_range = min(max_encoder_range, 1000)
        self.draw_effect(
            -1000,
            1000,
            -max_encoder_range,
            max_encoder_range,
            100,
            self.graph_effectsZoom,
        )

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
        chart.setBackgroundBrush(PyQt6.QtWidgets.QApplication.instance().palette().window())

        font = PyQt6.QtGui.QFont()
        font.setPixelSize(7)

        chart_x_axis = PyQt6.QtCharts.QValueAxis()
        chart_x_axis.setMax(100)
        chart_x_axis.setLabelsFont(font)
        chart_x_axis.setTitleText("Time (ms)")
        chart_x_axis.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                128,
            )
        )
        chart.addAxis(chart_x_axis, PyQt6.QtCore.Qt.AlignmentFlag.AlignBottom)

        chart_y_axis_forces = PyQt6.QtCharts.QValueAxis()
        chart_y_axis_forces.setMin(0)
        chart_y_axis_forces.setLabelsFont(font)
        chart_y_axis_forces.setTitleText("Min Speed")
        chart_y_axis_forces.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                64,
            )
        )
        chart.addAxis(chart_y_axis_forces, PyQt6.QtCore.Qt.AlignmentFlag.AlignLeft)

        for axe in chart.axes():
            axe.setTitleBrush(
                PyQt6.QtWidgets.QApplication.instance().palette().text()
            )
            axe.setLabelsBrush(
                PyQt6.QtWidgets.QApplication.instance().palette().text()
            )

        self.graph_min.setChart(chart)

        q_line3 = PyQt6.QtCharts.QLineSeries()
        q_line3.setColor(
            PyQt6.QtGui.QColor( #White
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                255,
            )
        )
        chart.addSeries(q_line3)
        q_line3.attachAxis(chart_y_axis_forces)
        q_line3.attachAxis(chart_x_axis)

        q_line2 = PyQt6.QtCharts.QLineSeries()
        q_line2.setColor(
            PyQt6.QtGui.QColor( #magenta
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
            PyQt6.QtGui.QColor( #cyan
                0,
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
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

    def draw_simulation_random(self):
        """Draw the simulation on a random stream and apply filter."""
        scaler = round(self.doubleSpinBox_speedScaler.value())
        freq = self.spinBox_speedFreq.value()
        q_factor = self.doubleSpinBox_speedQ.value()

        if len(self.min_randomize_value) < 200 or q_factor == 0.0:
            return

        # Chart setup
        chart = PyQt6.QtCharts.QChart()
        chart.setBackgroundRoundness(5)
        chart.setMargins(PyQt6.QtCore.QMargins(0, 0, 0, 0))
        chart.legend().hide()
        chart.setBackgroundBrush(PyQt6.QtWidgets.QApplication.instance().palette().window())

        font = PyQt6.QtGui.QFont()
        font.setPixelSize(7)

        chart_x_axis = PyQt6.QtCharts.QValueAxis()
        chart_x_axis.setMax(200)
        chart_x_axis.setLabelsFont(font)
        chart_x_axis.setTitleText("Time")
        chart_x_axis.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                128,
            )
        )
        chart.addAxis(chart_x_axis, PyQt6.QtCore.Qt.AlignmentFlag.AlignBottom)

        chart_y_axis_forces = PyQt6.QtCharts.QValueAxis()
        chart_y_axis_forces.setMin(0)
        chart_y_axis_forces.setMax(32767)
        chart_y_axis_forces.setLabelsFont(font)
        chart_y_axis_forces.setTitleText("Max Speed")
        chart_y_axis_forces.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                64,
            )
        )
        chart.addAxis(chart_y_axis_forces, PyQt6.QtCore.Qt.AlignmentFlag.AlignLeft)

        for axe in chart.axes():
            axe.setTitleBrush(
                PyQt6.QtWidgets.QApplication.instance().palette().text()
            )
            axe.setLabelsBrush(
                PyQt6.QtWidgets.QApplication.instance().palette().text()
            )

        self.graph_random.setChart(chart)

        q_line = PyQt6.QtCharts.QLineSeries()
        q_line.setColor(
            PyQt6.QtGui.QColor( #cyan
                0,
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                0,
                255,
            )
        )
        chart.addSeries(q_line)
        q_line.attachAxis(chart_y_axis_forces)
        q_line.attachAxis(chart_x_axis)

        q_line2 = PyQt6.QtCharts.QLineSeries()
        q_line2.setColor(
            PyQt6.QtGui.QColor( #magenta
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

        q_line3 = PyQt6.QtCharts.QLineSeries()
        q_line3.setColor(
            PyQt6.QtGui.QColor( #cyan
                0,
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                255,
            )
        )
        chart.addSeries(q_line3)
        q_line3.attachAxis(chart_y_axis_forces)
        q_line3.attachAxis(chart_x_axis)

        for i in range(200):
            q_line.append(i, self.min_randomize_value[i] * scaler)
            q_line2.append(i, local_filter.compute(self.min_randomize_value[i]) * scaler)
            q_line3.append(i, self.min_randomize_value[i])

    def draw_effect(self, min_range, max_range, start_data, end_data, nb_point_plot, qwidget):
        """Draw a generic effect in a qwidget : the effect response on the metrics range."""
        # Chart setup full range
        chart = PyQt6.QtCharts.QChart()
        chart.setBackgroundRoundness(5)
        chart.setMargins(PyQt6.QtCore.QMargins(0, 0, 0, 0))
        chart.legend().hide()
        chart.setBackgroundBrush(PyQt6.QtWidgets.QApplication.instance().palette().window())

        font = PyQt6.QtGui.QFont()
        font.setPixelSize(7)

        chart_x_axis = PyQt6.QtCharts.QValueAxis()
        chart_x_axis.setMin(min_range)
        chart_x_axis.setMax(max_range)
        chart_x_axis.setLabelsFont(font)
        chart_x_axis.setTitleText("Normalized Speed")
        chart_x_axis.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                128,
            )
        )
        chart.addAxis(chart_x_axis, PyQt6.QtCore.Qt.AlignmentFlag.AlignBottom)

        chart_y_axis_forces = PyQt6.QtCharts.QValueAxis()
        chart_y_axis_forces.setLabelsFont(font)
        chart_y_axis_forces.setMin(-32770)
        chart_y_axis_forces.setMax(32770)
        chart_y_axis_forces.setTitleText("Normalized Torque")
        chart_y_axis_forces.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                64,
            )
        )
        chart.addAxis(chart_y_axis_forces, PyQt6.QtCore.Qt.AlignmentFlag.AlignLeft)

        for axe in chart.axes():
            axe.setTitleBrush(
                PyQt6.QtWidgets.QApplication.instance().palette().text()
            )
            axe.setLabelsBrush(
                PyQt6.QtWidgets.QApplication.instance().palette().text()
            )

        qwidget.setChart(chart)

        q_line = PyQt6.QtCharts.QLineSeries()
        q_line.setColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                0,
                0,
                255,
            )
        )
        chart.addSeries(q_line)
        q_line.attachAxis(chart_y_axis_forces)
        q_line.attachAxis(chart_x_axis)

        q_line2 = PyQt6.QtCharts.QLineSeries()
        q_line2.setColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                0,
                255,
            )
        )
        chart.addSeries(q_line2)
        q_line2.attachAxis(chart_y_axis_forces)
        q_line2.attachAxis(chart_x_axis)

        interval = (end_data - start_data) / nb_point_plot
        for i in range(0, nb_point_plot):
            axis_pos = round(start_data + (i * interval))
            if abs(axis_pos) > self.min_speed_rescale:
                damper = self.calc_condition_effect_force(axis_pos, 1)
                friction = self.friction_effect_force(axis_pos, 1)
                q_line.append(axis_pos, damper)
                q_line2.append(axis_pos, friction)
            else:
                q_line.append(axis_pos, 0)
                q_line2.append(axis_pos, 0)

    def calc_condition_effect_force(self, metric, scale):
        """Compute the force for a metric value and a scale."""
        offset = 0
        dead_band = 0
        negative_coefficient = 32767
        positive_coefficient = 32767
        positive_saturation = positive_coefficient
        negative_saturation = negative_coefficient
        force = 0

        # Effect is only active outside deadband + offset
        if abs(metric - offset) > dead_band:
            coefficient = negative_coefficient
            if metric > offset:
                coefficient = positive_coefficient

            coefficient /= 0x7FFF
            # rescale the coefficient of effect

            # remove offset/deadband from metric to compute force
            metric = metric - (offset + (dead_band * (-1 if metric < offset else 1)))

            force = coefficient * scale * (float)(metric)

            if force > positive_saturation:
                force = positive_saturation

            if force < -negative_saturation:
                force = -negative_saturation

        return force

        # effect friction to simulate

    def friction_effect_force(self, metric, scale):
        """Compute the friction effect for a metric."""
        offset = 0
        dead_band = 0
        negative_coefficient = 32767
        positive_coefficient = 32767
        force = 0

        speed = metric * scale

        pct_friction = self.spinBox_pctFrictionRampUp.value()
        speed_rampup_pct = round((pct_friction / 100) * 32767)  # sinusoidal to 30

        # Effect is only active outside deadband + offset
        if abs(speed - offset) > dead_band:

            # remove offset/deadband from metric to compute force
            speed -= offset + (dead_band * (-1 if speed < offset else 1))

            # check if speed is in the 0..x% to rampup, if is this range,
            # apply a sinusoidale function to smooth the torque
            # slow near 0, slow around the X% rampup
            rampup_factor = 1.0
            if (
                abs(speed) < speed_rampup_pct
            ):  # if speed in the range to rampup we apply a sinus curbe to ramup

                # we start to compute the normalized angle (speed / normalizedSpeed@5%)
                # and translate it of -1/2PI to translate sin on 1/2 periode
                phase_rad = math.pi * (
                    (abs(speed) / speed_rampup_pct) - 0.5
                )

                rampup_factor = (1 + math.sin(phase_rad)) / 2
                # sin value is -1..1 range, we translate it to 0..2 and we scale it by 2

            sign = 1 if speed >= 0 else -1
            coeff = negative_coefficient if speed < 0 else positive_coefficient
            force = coeff * rampup_factor * sign

        return force


class AdvancedTuningDialog(PyQt6.QtWidgets.QDialog):
    """Manage the dialog box for the encoder UI.

    The dialogbox is open in non modal item.
    """

    def __init__(self, parent_ui: base_ui.WidgetUI = None, axis_instance:int = 0):
        """Construct the with an axis, the tuning is by axis."""
        PyQt6.QtWidgets.QDialog.__init__(self, parent_ui)
        self.advanced_tweak_ui = AdvancedTweakUI(self, axis_instance)
        self.layout = PyQt6.QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.advanced_tweak_ui)
        self.setLayout(self.layout)
        self.setWindowTitle("Advanced encoder tuning")

    def setEnabled(self, a0: bool) -> None:  # pylint: disable=unused-argument, invalid-name
        """Enable all the widget in the tuned UI."""
        self.advanced_tweak_ui.setEnabled(a0)
        return super().setEnabled(a0)

    def display(self):
        """Show the dialog box for the tuned UI."""
        self.show()
        self.raise_()
        self.activateWindow()
