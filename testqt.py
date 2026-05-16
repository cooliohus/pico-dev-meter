import sys
from PyQt6.QtWidgets import QApplication, QWidget
#from PySide5.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)
label = QLabel("Hello World!")
label.show()
app.exec()