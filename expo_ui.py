"""Expo curve tuning UI module.
Displays an exponential curve preview for effect torque postprocessing

Module : expo_ui
Authors : Yannick
"""

import math
import PyQt6.QtGui
import PyQt6.QtCore
import PyQt6.QtWidgets
import PyQt6.QtCharts
import base_ui


class ExpoTuneUI(base_ui.WidgetUI, base_ui.CommunicationHandler):

    def __init__(self, parent: 'ExpoTuneDialog' = None,axis : int = 0):
        base_ui.WidgetUI.__init__(self, parent, "expo.ui")
        base_ui.CommunicationHandler.__init__(self)
        
        self.axis = axis
        self.exposcale = 0
        self.expo = 1

        self.register_callback("axis","expo",self.exponentCb,self.axis,int)
        self.register_callback("axis","exposcale",self.exposcaleCb,self.axis,int)
        self.horizontalSlider_expo.setMinimum(-127)
        self.horizontalSlider_expo.setMaximum(127)
        self.horizontalSlider_expo.valueChanged.connect(self.expoSliderCb)
        self.pushButton_reset.clicked.connect(lambda x : self.exponentCb(0))

        self.chart = PyQt6.QtCharts.QChart()
        self.chart_y_axis = PyQt6.QtCharts.QValueAxis()
        self.chart_x_axis = PyQt6.QtCharts.QValueAxis()
        self.makeGraph()

    def exposcaleCb(self,val):
        self.exposcale = val

    def expoSliderCb(self,val):
        self.send_value("axis","expo",val,instance=self.axis)
        self.updateExponent(val)

    def exponentCb(self,val):
        self.horizontalSlider_expo.setValue(val)

    def updateExponent(self,val):
        if self.exposcale == 0:
            return # Or get scaler again
        # expoValInt = val
        if(val == 0):
            self.expo = 1
        else:
        
            valF = abs(val / self.exposcale)
            if(val < 0):
                self.expo = 1.0/(1.0+valF)
            else:
                self.expo = 1+valF

        self.doubleSpinBox_exponent.setValue(self.expo)

        self.updateCurve(self.expo)
	
    def makeGraph(self):
        

        self.chart.setBackgroundRoundness(5)
        self.chart.setMargins(PyQt6.QtCore.QMargins(0, 0, 0, 0))
        self.chart.legend().hide()
        self.chart.setBackgroundBrush(PyQt6.QtWidgets.QApplication.instance().palette().window())

        font = PyQt6.QtGui.QFont()
        font.setPixelSize(10)
        
        self.chart_x_axis.setMin(-1)
        self.chart_x_axis.setMax(1)
        self.chart_x_axis.setLabelsFont(font)
        self.chart_x_axis.setTitleText("Input")
        self.chart_x_axis.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                128,
            )
        )
        self.chart.addAxis(self.chart_x_axis, PyQt6.QtCore.Qt.AlignmentFlag.AlignBottom)

        
        self.chart_y_axis.setLabelsFont(font)
        self.chart_y_axis.setMin(-1)
        self.chart_y_axis.setMax(1)
        self.chart_y_axis.setTitleText("Output")
        self.chart_y_axis.setGridLineColor(
            PyQt6.QtGui.QColor(
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().red(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().green(),
                PyQt6.QtWidgets.QApplication.instance().palette().dark().color().blue(),
                64,
            )
        )
        self.chart.addAxis(self.chart_y_axis, PyQt6.QtCore.Qt.AlignmentFlag.AlignLeft)
        for axe in self.chart.axes():
            axe.setTitleBrush(
                PyQt6.QtWidgets.QApplication.instance().palette().text()
            )
            axe.setLabelsBrush(
                PyQt6.QtWidgets.QApplication.instance().palette().text()
            )
        self.graph_expo.setChart(self.chart)

    def updateCurve(self,exponent):


        q_line = PyQt6.QtCharts.QLineSeries()
        q_line.setColor(PyQt6.QtGui.QColor("darkcyan"))
        self.chart.removeAllSeries()

        self.chart.addSeries(q_line)
        q_line.attachAxis(self.chart_y_axis)
        q_line.attachAxis(self.chart_x_axis)

         # Draw graph

        xv = [i / 100 for i in range(-100,100,1)]
        for x in xv:
            y = self.calcExpo(x,self.expo)
        # yv = [self.calcExpo(i,self.expo) for i in xv]
            q_line.append(x,y)
        


    def calcExpo(self,x,expo):
        if x < 0:
            return -pow(-x,expo)
        else:
            return pow(x,expo)


    def init_ui(self):
        self.send_commands("axis",["exposcale","expo"],self.axis)


    
class ExpoTuneDialog(PyQt6.QtWidgets.QDialog):
    def __init__(self, parent_ui: 'base_ui.WidgetUI' = None,axis : int = 0):
        PyQt6.QtWidgets.QDialog.__init__(self, parent_ui)
        self.expo_ui = ExpoTuneUI(self,axis)
        self.layout = PyQt6.QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.expo_ui)
        self.setLayout(self.layout)
        self.setWindowTitle("Expo curve tuning")
        self.setModal(True)

        self.enabled = False

        self.expo_ui.pushButton_close.clicked.connect(self.close)

    def setEnabled(self,a0 : bool):
        self.enabled = a0
        # if a0:
        #     self.expo_ui.init_ui()
        return super().setEnabled(a0)
    
    def display(self):
        """Show the dialog box"""
        if not self.enabled:
            return # Ignore
        self.show()
        self.raise_()
        self.activateWindow()
        self.expo_ui.init_ui()