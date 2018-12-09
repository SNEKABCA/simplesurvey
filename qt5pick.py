import os

#Choose which Qt binding to use
if 'WHICH_QT' in os.environ and \
   os.environ['WHICH_QT'].lower() != "pyqt" or \
   not 'WHICH_QT' in os.environ:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets, QtUiTools, QtPositioning, QtNetwork, QtSerialPort
        from PySide2.QtCore import Slot, Signal, QMetaObject, Property
        from pyside_dynamic import UiLoader

        def load_ui(ui_file, widget, widget_mapping = None):
            if widget_mapping is None:
                widget_mapping = {}

            loader = UiLoader(widget, widget_mapping )
            top_widget = loader.load(ui_file)
            QMetaObject.connectSlotsByName(widget)

        USE_PYSIDE = True
    except ImportError:
        USE_PYSIDE = False
if not USE_PYSIDE:
    from PyQt5 import QtCore, QtGui, uic, QtWidgets, QtPositioning, QtNetwork, QtSerialPort
    from PyQt5.QtCore import pyqtSlot as Slot
    from PyQt5.QtCore import pyqtSignal as Signal
    from PyQt5.QtCore import pyqtProperty as Property

    def load_ui(ui_file, widget, widget_mapping = None):
        uic.loadUi(ui_file, widget)

#from blocksignalqt import BlockSignal

if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QWidget()
    b = QtWidgets.QLabel(w)
    b.setText("Hello World!")
    w.setGeometry(100,100,200,50)
    b.move(50,20)
    if USE_PYSIDE:
        w.setWindowTitle("PySide2")
    else:
        w.setWindowTitle("PyQt5")

    w.show()
    sys.exit(app.exec_())



