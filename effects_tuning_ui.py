"""Encoder tuning UI module.

Regroup all required classes to manage the encoder tuning for the FFB Engine.

Module : encoder_tuning_ui
Authors : vincent
"""
import math
import PyQt6.QtGui
import PyQt6.QtCore
import PyQt6.QtWidgets
import PyQt6.QtCharts
import base_ui

class Crosshairs():
    
    def __init__(self, chart: PyQt6.QtCharts.QChart, scene: PyQt6.QtWidgets.QGraphicsScene,
        color: PyQt6.QtGui.QColor):
        self.m_xline = PyQt6.QtWidgets.QGraphicsLineItem()
        self.m_chart = chart

        self.m_xline.setPen(color)
        self.m_xline.setZValue(11)

        # add lines and text to scene
        scene.addItem(self.m_xline)
    
    def update_position(self, metrics):
        point = PyQt6.QtCore.QPointF(metrics, 0)
        position = self.m_chart.mapToPosition(point, self.m_chart.series()[0])

        x_line = PyQt6.QtCore.QLineF(position.x(), self.m_chart.plotArea().top(),position.x(), self.m_chart.plotArea().bottom())
        self.m_xline.setLine(x_line)

        if not(self.m_chart.plotArea().contains(position)):
            self.m_xline.hide()
        else:
            self.m_xline.show()

class AdvancedFFBTuneUI(base_ui.WidgetUI, base_ui.CommunicationHandler):
    """Manage the UI to tune the encoder."""

    def __init__(self, parent: 'AdvancedFFBTuneDialog' = None):
        """Initialize the init with the dialog parent and the axisUI linked on the encoder."""
        base_ui.WidgetUI.__init__(self, parent, "effects_tuning.ui")
        base_ui.CommunicationHandler.__init__(self)
        self.parent_dlg = parent
        self.springgain = 1
        self.dampergain = 1
        self.frictiongain = 1
        self.inertiagain = 1
        self.damper_internal_scale = 1
        self.inertia_internal_scale = 1
        self.friction_internal_scale = 1
        self.damper_internal_factor = 1
        self.inertia_internal_factor = 1
        self.friction_internal_factor = 1
        self.friction_pct_speed_rampup = 1
        self.timer = PyQt6.QtCore.QTimer(self)
        self.cross_hairs_spring : Crosshairs = None
        self.cross_hairs_inertia : Crosshairs = None
        self.cross_hairs_damper : Crosshairs = None
        self.cross_hairs_friction : Crosshairs = None

        # on slider change
        self.horizontalSlider_friction_smooth.valueChanged.connect(lambda val : self.slider_changed(val,self.horizontalSlider_friction_smooth,"frictionPctSpeedToRampup"))
        self.horizontalSlider_spring_gain.valueChanged.connect(lambda val : self.slider_changed(val,self.horizontalSlider_spring_gain,"spring"))
        self.horizontalSlider_damper_gain.valueChanged.connect(lambda val : self.slider_changed(val,self.horizontalSlider_damper_gain,"damper"))
        self.horizontalSlider_friction_gain.valueChanged.connect(lambda val : self.slider_changed(val,self.horizontalSlider_friction_gain,"friction"))
        self.horizontalSlider_inertia_gain.valueChanged.connect(lambda val : self.slider_changed(val,self.horizontalSlider_inertia_gain,"inertia"))

        # on filter change
        self.spinBox_damper_freq.valueChanged.connect(lambda val : self.filter_changed(val,"damper_f",1))
        self.doubleSpinBox_damper_q.valueChanged.connect(lambda val : self.filter_changed(val,"damper_q",100))
        self.spinBox_friction_freq.valueChanged.connect(lambda val : self.filter_changed(val,"friction_f",1))
        self.doubleSpinBox_friction_q.valueChanged.connect(lambda val : self.filter_changed(val,"friction_q",100))
        self.spinBox_inertia_freq.valueChanged.connect(lambda val : self.filter_changed(val,"inertia_f",1))
        self.doubleSpinBox_inertia_q.valueChanged.connect(lambda val : self.filter_changed(val,"inertia_q",100))

        # on button
        self.pushButton_restore.clicked.connect(self.restore_default)

        # add timer handler
        self.timer.timeout.connect(self.updateTimer)
        
    def setEnabled(self, a0: bool) -> None: # pylint: disable=unused-argument, invalid-name
        """Enable the item."""
        return super().setEnabled(a0)

    def showEvent(self, a0: PyQt6.QtGui.QShowEvent) -> None: # pylint: disable=unused-argument, invalid-name
        """Show event, reload the settings and show the settings."""
        self.add_callbacks()
        self.load_settings()
        return super().showEvent(a0)
    
    def add_callbacks(self):
        # register effect command
        self.register_callback("fx", "frictionPctSpeedToRampup",lambda val : self.update_slider(val,self.horizontalSlider_friction_smooth),0,int)

        # register gain factor and scale
        self.register_callback("fx","spring",self.set_spring_scaler_cb,0,str,typechar="!")
        self.register_callback("fx","damper",self.set_damper_scaler_cb,0,str,typechar="!")
        self.register_callback("fx","inertia",self.set_inertia_scaler_cb,0,str,typechar="!")
        self.register_callback("fx","friction",self.set_friction_scaler_cb,0,str,typechar="!")

        self.register_callback("fx","spring",lambda val : self.update_slider(val,self.horizontalSlider_spring_gain),0,int)
        self.register_callback("fx","damper",lambda val : self.update_slider(val,self.horizontalSlider_damper_gain),0,int)
        self.register_callback("fx","friction",lambda val : self.update_slider(val,self.horizontalSlider_friction_gain),0,int)
        self.register_callback("fx","inertia",lambda val : self.update_slider(val,self.horizontalSlider_inertia_gain),0,int)

        # register internal factor for scaler and factor
        self.register_callback("fx","scaler_friction",self.set_internal_friction_scale,0,str,typechar="!")
        self.register_callback("fx","scaler_damper",self.set_internal_damper_scale,0,str,typechar="!")
        self.register_callback("fx","scaler_inertia",self.set_internal_inertia_scale,0,str,typechar="!")

        self.register_callback("fx","scaler_friction",self.set_internal_friction_factor,0,str)
        self.register_callback("fx","scaler_damper",self.set_internal_damper_factor,0,str)
        self.register_callback("fx","scaler_inertia",self.set_internal_inertia_factor,0,str)

        # register biquad factor
        self.register_callback("fx","damper_f",self.spinBox_damper_freq.setValue,0,int)
        self.register_callback("fx","damper_q",lambda val : self.doubleSpinBox_damper_q.setValue((float)(val) / 100.0),0,str)
        self.register_callback("fx","friction_f",self.spinBox_friction_freq.setValue,0,int)
        self.register_callback("fx","friction_q",lambda val : self.doubleSpinBox_friction_q.setValue((float)(val) / 100.0),0,str)
        self.register_callback("fx","inertia_f",self.spinBox_inertia_freq.setValue,0,int)
        self.register_callback("fx","inertia_q",lambda val : self.doubleSpinBox_inertia_q.setValue((float)(val) / 100.0),0,str)

        # register pos, accel, speed
        self.register_callback("axis","curpos",self.get_pos_metrics,0,int)
        self.register_callback("axis","curspd",self.get_speed_metrics,0,int)
        self.register_callback("axis","curaccel",self.get_accel_metrics,0,int)

    def hideEvent(self, a0) -> None: # pylint: disable=unused-argument, invalid-name
        """Hide event, hide the dialog."""
        self.timer.stop()
        self.remove_callbacks()
        self.send_commands("fx",["spring","damper","friction","inertia","frictionPctSpeedToRampup"],0)
        self.log("FFB: closed tuning windows, click on save flash")
        
        msg = PyQt6.QtWidgets.QMessageBox(self)
        msg.setIcon(PyQt6.QtWidgets.QMessageBox.Icon.Information)
        msg.setText("Don't forget to save in flash.")
        msg.exec()
        return super().hideEvent(a0)

    def load_settings(self):
        """Load the settings."""
        self.send_commands("fx",["scaler_friction","scaler_damper","scaler_inertia",
                                "spring","damper","friction","inertia"],0,typechar="!")
        self.send_commands("fx",["scaler_friction","scaler_damper","scaler_inertia","frictionPctSpeedToRampup",
                                "spring","damper","friction","inertia",
                                "damper_f","damper_q","friction_f","friction_q","inertia_f","inertia_q"],0)

        self.get_value_async("main","id",self.get_main_id,0,int)
    
    def get_main_id(self, id):
        """Setup axis number from main class and start polling metrics on the axis."""
        if id == 1:
            self.spinBox_axis.setMaximum(0)
        elif id == 2:
            self.spinBox_axis.setMaximum(1)
        self.timer.start(100)
  
    def restore_default(self):
        self.horizontalSlider_spring_gain.setValue(64)
        self.horizontalSlider_inertia_gain.setValue(127)
        self.horizontalSlider_damper_gain.setValue(64)
        self.horizontalSlider_friction_gain.setValue(254)

        self.horizontalSlider_friction_smooth.setValue(25)

        self.spinBox_inertia_freq.setValue(15)
        self.doubleSpinBox_inertia_q.setValue(0.20)
        self.spinBox_damper_freq.setValue(30)
        self.doubleSpinBox_damper_q.setValue(0.40)
        self.spinBox_friction_freq.setValue(50)
        self.doubleSpinBox_friction_q.setValue(0.20)

    def updateTimer(self):
        self.send_commands("axis",["curpos","curspd","curaccel"],self.spinBox_axis.value())

    def extract_scaler(self, gain_default, repl) :
        infos = {key:value for (key,value) in [entry.split(":") for entry in repl.split(",")]}
        if "scale" in infos:
            gain_default = float(infos["scale"]) if float(infos["scale"]) > 0 else gain_default
        return gain_default

    def set_spring_scaler_cb(self,repl):
        self.springgain = self.extract_scaler(self.springgain, repl)

    def set_damper_scaler_cb(self,repl):
        self.dampergain = self.extract_scaler(self.dampergain, repl)

    def set_friction_scaler_cb(self,repl):
        self.frictiongain = self.extract_scaler(self.frictiongain, repl)

    def set_inertia_scaler_cb(self,repl):
        self.inertiagain = self.extract_scaler(self.inertiagain, repl)

    def set_internal_friction_scale(self, repl):
        self.friction_internal_scale = self.extract_scaler(1, repl)

    def set_internal_damper_scale(self, repl):
        self.damper_internal_scale = self.extract_scaler(1, repl)

    def set_internal_inertia_scale(self, repl):
        self.inertia_internal_scale = self.extract_scaler(1, repl)

    def set_internal_friction_factor(self, value):
        self.friction_internal_factor = float(value)

    def set_internal_damper_factor(self, value):
        self.damper_internal_factor = float(value)

    def set_internal_inertia_factor(self, value):
        self.inertia_internal_factor = float(value)

    def set_friction_pct_speed_rampup(self,value):
        self.friction_pct_speed_rampup = value

    def update_slider(self,val,slider : PyQt6.QtWidgets.QSlider):
        #skip the slider update if value is the same
        if (slider.value() == val) : return
        
        #update the slider value and the graph
        slider.setValue(val)
        self.slider_changed(val, slider)
    
    def slider_changed(self,val,slider : PyQt6.QtWidgets.QSlider, command = None):

        #send value to the board
        if command :
            self.send_value("fx", command, val)

        #update graph if the slider is used by a graph
        if slider == self.horizontalSlider_spring_gain :
            self.draw_graph_spring()
        if slider == self.horizontalSlider_inertia_gain :
            self.draw_graph_inertia()
        if slider == self.horizontalSlider_damper_gain :
            self.draw_graph_damper()
        if slider == self.horizontalSlider_friction_gain or \
            slider == self.horizontalSlider_friction_smooth :
            self.draw_graph_friction()

    def filter_changed(self, val, filter, scale = 1):
        if val != 0 :
            self.send_value("fx", filter, val * scale)

    def get_pos_metrics(self, value):
        value = 100 * value / 32767
        self.cross_hairs_spring.update_position(value)
    
    def get_speed_metrics(self, value):
        value = 60 * value / 360.0 
        self.cross_hairs_damper.update_position(value)
        self.cross_hairs_friction.update_position(value)

    def get_accel_metrics(self, value):
        self.cross_hairs_inertia.update_position(value)

    def draw_graph_spring(self):
        """Draw the effects graph response."""
        scaler = self.springgain * (1+self.horizontalSlider_spring_gain.value()) / 256.0
        color = PyQt6.QtGui.QColor("darkcyan")
        chart = self.draw_effect_conditional(
            -100,
            100,
            "wheel range (%)",
            -32767,
            32767,
            "torque",
            300,
            self.graph_spring,
            color,
            scaler,
            1
        )
        color.setAlpha(128)
        self.cross_hairs_spring = Crosshairs(chart, self.graph_spring.scene(), color)

    def draw_graph_inertia(self):
        """Draw the effects graph response."""
        scaler = self.inertia_internal_factor * self.inertia_internal_scale * self.inertiagain * (1+self.horizontalSlider_inertia_gain.value()) / 256.0
        color = PyQt6.QtGui.QColor("darkmagenta")
        chart = self.draw_effect_conditional(
            -30000,
            30000,
            "acceleration (deg/s2)",
            -32767,
            32767,
            "torque",
            300,
            self.graph_inertia,
            color,
            scaler,
            1
        )
        color.setAlpha(128)
        self.cross_hairs_inertia = Crosshairs(chart, self.graph_inertia.scene(),color)
    
    def draw_graph_damper(self):
        """Draw the effects graph response."""
        scaler = self.damper_internal_factor * self.damper_internal_scale * self.dampergain * (1+self.horizontalSlider_damper_gain.value()) / 256.0
        color = PyQt6.QtGui.QColor("limegreen")
        chart = self.draw_effect_conditional(
            -300,
            300,
            "speed (rpm)",
            -300 * 360 / 60.0,
            300 * 360 / 60.0,
            "torque",
            300,
            self.graph_damper,
            color,
            scaler,
            1
        )
        color.setAlpha(128)
        self.cross_hairs_damper = Crosshairs(chart, self.graph_damper.scene(),color)

    def draw_graph_friction(self):
        """Draw the effects graph response."""
        scaler = self.friction_internal_factor * self.friction_internal_scale
        color = PyQt6.QtGui.QColor("limegreen")
        chart = self.draw_effect_conditional(
            -130,
            130,
            "speed (rpm)",
            -120 * 360 / 60.0,
            120 * 360 / 60.0,
            "torque",
            300,
            self.graph_friction,
            color,
            scaler,
            0
        )
        color.setAlpha(128)
        self.cross_hairs_friction = Crosshairs(chart, self.graph_friction.scene(),color)

    def draw_effect_conditional(self, x_min, x_max, x_label, start_data, end_data, y_label, nb_point_plot, qwidget, color, effect_gain, cond_frict):
        """Draw a generic effect in a qwidget : the effect response on the metrics range."""
        # Chart setup full range
        chart = PyQt6.QtCharts.QChart()
        chart.setBackgroundRoundness(5)
        chart.setMargins(PyQt6.QtCore.QMargins(0, 0, 0, 0))
        chart.legend().hide()
        chart.setBackgroundBrush(PyQt6.QtWidgets.QApplication.instance().palette().window())

        font = PyQt6.QtGui.QFont()
        font.setPixelSize(10)

        chart_x_axis = PyQt6.QtCharts.QValueAxis()
        chart_x_axis.setMin(x_min)
        chart_x_axis.setMax(x_max)
        chart_x_axis.setLabelsFont(font)
        chart_x_axis.setTitleText(x_label)
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
        chart_y_axis_forces.setTitleText(y_label)
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
        q_line.setColor(color)

        chart.addSeries(q_line)
        q_line.attachAxis(chart_y_axis_forces)
        q_line.attachAxis(chart_x_axis)

        interval_effect = (end_data - start_data) / nb_point_plot
        interval_pos = (x_max - x_min) / nb_point_plot
        for i in range(0, nb_point_plot):
            axis_pos = x_min + (i * interval_pos)
            axis_affect = start_data + (i * interval_effect)
            if (cond_frict) :
                effect_value = self.calc_condition_effect_force(axis_affect, effect_gain)
            else:
                effect_value = self.calc_friction_effect_force(axis_affect, effect_gain)
            q_line.append(axis_pos, effect_value)

        return chart

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

    def calc_friction_effect_force(self, metric, scale):
        """Compute the friction effect for a metric."""
        offset = 0
        dead_band = 0
        negative_coefficient = 32767
        positive_coefficient = 32767
        force = 0

        speed = metric * scale

        pct_friction = self.horizontalSlider_friction_smooth.value()
        speed_rampup_pct = round((pct_friction / 100.0) * 32767)  # sinusoidal to 30

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
            force = force *  self.frictiongain * (1+self.horizontalSlider_friction_gain.value()) / 256.0

        return force


class AdvancedFFBTuneDialog(PyQt6.QtWidgets.QDialog):
    """Manage the dialog box for the encoder UI.

    The dialogbox is open in non modal item.
    """

    def __init__(self, parent_ui: base_ui.WidgetUI = None):
        """Construct the with an axis, the tuning is by axis."""
        PyQt6.QtWidgets.QDialog.__init__(self, parent_ui)
        self.advanced_tweak_ui = AdvancedFFBTuneUI(self)
        self.layout = PyQt6.QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.advanced_tweak_ui)
        self.setLayout(self.layout)
        self.setWindowTitle("Advanced ffb tuning")
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
