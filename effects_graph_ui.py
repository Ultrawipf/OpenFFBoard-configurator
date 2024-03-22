"""effect monitoring module for UI.

Regroup all required classes to monitor the effect in a graph.

Module : effects_graph_ui
Authors : vincent
"""
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
        self.parent = dlg

        self.max_datapoints = 1000
        self.max_datapoints_visible_time = 30

        self.start_time = 0
        self.chart_last_x = 0

        self.axistorque_enabled = False
        self.totaltorqe_line = None

        self.axis = 0
        self.spinBox_axis.valueChanged.connect(self.setAxis)

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

        # Output axis
        self.chart_yaxis_output = PyQt6.QtCharts.QValueAxis()
        self.chart_yaxis_output.setMin(-10)
        self.chart_yaxis_output.setMax(10)

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
            PyQt6.QtGui.QColorConstants.Gray,
        ]
        self.lines = []
        for i in range(12):
            q_line = PyQt6.QtCharts.QLineSeries()
            q_line.setUseOpenGL(True)
            q_line.setColor(effect_color[i])
            q_line.setName(effect_name[i])
            self.lines.append(q_line)
            self.chart.addSeries(q_line)
            q_line.attachAxis(self.chart_yaxis_forces)
            q_line.attachAxis(self.chart_xaxis)

        # Setup the timer to get data
        self.timer = PyQt6.QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_timer)  # pylint: disable=no-value-for-parameter
    
    def set_total_output_display(self,enable: bool):
        """Enable or disable the axis torque line"""
        if enable and self.totaltorqe_line == None:
            self.axistorque_enabled = enable
            self.chart.addAxis(
            self.chart_yaxis_output, PyQt6.QtCore.Qt.AlignmentFlag.AlignRight
            )
            q_line = PyQt6.QtCharts.QLineSeries()
            q_line.setUseOpenGL(True)
            q_line.setColor(PyQt6.QtGui.QColorConstants.Svg.coral)
            q_line.setName("Output torque (Y2)")
            self.totaltorqe_line = q_line
            self.chart.addSeries(q_line)
            q_line.attachAxis(self.chart_yaxis_output)
            q_line.attachAxis(self.chart_xaxis)
        elif not enable and self.totaltorqe_line != None:
            self.chart.removeSeries(self.totaltorqe_line)
            self.chart.removeAxis(self.chart_yaxis_output)
            del self.totaltorqe_line
            self.totaltorqe_line = None

    def set_output_axis_range(self,val: int):
        """Changes the right Y axis scaling"""
        self.chart_yaxis_output.setMin(-val)
        self.chart_yaxis_output.setMax(val)

    def reset(self):
        # Clear
        self.start_time = PyQt6.QtCore.QTime.currentTime()
        self.chart_last_x = 0
        for i in range(12):
            self.lines[i].clear()
        if self.totaltorqe_line != None:
            self.totaltorqe_line.clear()

    def setAxis(self,axis):
        # Reset
        self.reset()
        self.axis = axis

    def setEnabled(self, a0: bool) -> None:
        if not a0 and self.isVisible() and self.timer.isActive : 
            self.hide()
        return super().setEnabled(a0)

    def showEvent(self, event):  # pylint: disable=invalid-name, unused-argument
        """Display the UI and start calling board  for data."""
        self.init_ui()
        self.timer.start(100)

    # Tab is hidden
    def hideEvent(self, event):  # pylint: disable=invalid-name, unused-argument
        """Stop the timer on close event."""
        if self.timer.isActive : 
            self.timer.stop()
        self.parent.hide()
        return super().hideEvent(event)

    def update_timer(self):
        """Call the board to get instant data."""
        self.get_value_async("fx", "effectsForces", self.display_data,adr=self.axis)
        if self.totaltorqe_line != None:
            self.get_value_async("axis","curtorque",callback=self.axistorque_cb,instance=self.axis,conversion=int)

    def axistorque_cb(self,val):
        if not self.totaltorqe_line != None:
            return
        self.add_data_to_series(self.totaltorqe_line,val)
        maxval = abs(max(list(self.totaltorqe_line.points()),key=lambda v:abs(v.y())).y())
        self.set_output_axis_range(max(10,maxval)) # Autorange


    def display_data(self, data):
        """Decode the data received."""
        #data = data.replace('\n',',')
        forces = [ int(e.split(":")[0]) for e in data.split("\n") ]
        effects = [ int(e.split(":")[1]) for e in data.split("\n") ]
        #json_data = json.loads("[" + data + "]")
        if len(forces) == 12:
            self.update_current(forces)
            self.update_effect_stats(effects)

    def cmdflags(self,flags):
        if flags & base_ui.CommunicationHandler.CMDFLAG_GETADR:
            # enable axis selection
            self.spinBox_axis.setEnabled(True)

    def init_ui(self):
        """Init the ui by clear all data in series."""
        # clear graph
        self.reset()
        self.get_value_async("fx", "cmdinfo", self.cmdflags,adr=17,conversion=int)

    def update_effect_stats(self,dat):
        self.spinBox_1.setValue(dat[0])
        self.spinBox_2.setValue(dat[1])
        self.spinBox_3.setValue(dat[2])
        self.spinBox_4.setValue(dat[3])
        self.spinBox_5.setValue(dat[4])
        self.spinBox_6.setValue(dat[5])
        self.spinBox_7.setValue(dat[6])
        self.spinBox_8.setValue(dat[7])
        self.spinBox_9.setValue(dat[8])
        self.spinBox_10.setValue(dat[9])
        self.spinBox_11.setValue(dat[10])
        self.spinBox_12.setValue(dat[11])

    def add_data_to_series(self,line,val):
        line.append(self.chart_last_x, val)
        if line.count() > self.max_datapoints:
            line.remove(0)

    def update_current(self, forces):
        """Display on graph the response of the board."""
        try:
            self.chart_last_x = (
                self.start_time.msecsTo(PyQt6.QtCore.QTime.currentTime()) / 1000
            )
            index = 0
            for i in forces:
                self.add_data_to_series(self.lines[index],forces[index])
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
    
    def set_max_axes(self,axes):
        self.graph_ui.spinBox_axis.setMaximum(axes)

    def setEnabled(self, a0: bool) -> None:  # pylint: disable=invalid-name
        """Enable the UI, or disable it depends on message."""
        if not a0:
            self.close()
        self.graph_ui.setEnabled(a0)
        return super().setEnabled(a0)

    def display(self):
        """Display the dialogbox."""
        self.show()
        self.raise_()
        self.activateWindow()

    def set_total_output_display(self,enabled: bool):
        self.graph_ui.set_total_output_display(enabled)
