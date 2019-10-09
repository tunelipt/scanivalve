import sys
from PyQt5.QtWidgets import (QLabel, QGridLayout, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, qApp, QMenu,
                             QGroupBox, QPushButton, QApplication, QSlider, QMainWindow, QSplashScreen,
                             QAction, QMessageBox, QDialog)
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QPixmap, QIcon, QRegExpValidator, QDoubleValidator, QIntValidator, QValidator
from PyQt5 import QtTest

import time

import scanivalve as scani

class ScaniGUI(QMainWindow):

    def __init__(self, parent=None):

        self.dev = None
        self.model = None
        self.connected = False

        super(ScaniGUI, self).__init__(parent)
        
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        vb = QVBoxLayout()
        hb1 = QHBoxLayout()
        self.scanigr = QGroupBox("Rede")
        self.confgr = QGroupBox("Config")
        hb1.addWidget(self.scanigr)
        vb1 = QVBoxLayout()
        hb2 = QHBoxLayout()
        hb2.addWidget(QLabel("IP"))
        self.ip_ed = QLineEdit("191.30.80.131")
        hb2.addWidget(self.ip_ed)
        vb1.addLayout(hb2)
        self.connbut = QPushButton("Conectar")
        self.connbut.clicked.connect(self.connect)
        
        vb1.addWidget(self.connbut)
        self.scanigr.setLayout(vb1)
                      
        hb1.addWidget(self.confgr)
        vb.addLayout(hb1)

        self.zerobut = QPushButton("Hard Zero")
        self.zerobut.clicked.connect(self.hard_zero)
        self.zerobut.setEnabled(False)
        vb.addWidget(self.zerobut)

        self.listsbut = QPushButton("LIST S")
        self.listsbut.clicked.connect(self.listS)
        self.listsbut.setEnabled(False)
        vb.addWidget(self.listsbut)
        
        self.okbut = QPushButton("Ok")
        vb.addWidget(self.okbut)

        
        #self.szerobut.QPushButton("Soft Zero")
        #self.szerobut.setEnabled(False)
        
        
        gr1 = QGridLayout()
        vb2 = QVBoxLayout()
        
        gr1.addWidget(QLabel("FPS"), 0, 0)
        gr1.addWidget(QLabel("PERIOD"), 1, 0)
        gr1.addWidget(QLabel("AVG"), 2, 0)
        
        self.fps_ed = QLineEdit("1")
        self.fps_val = QIntValidator(1, 2147483647)
        self.fps_ed.setValidator(self.fps_val)
        self.fps_ed.textChanged.connect(self.check_state)
        self.fps_ed.textChanged.emit(self.fps_ed.text())
        
        self.period_ed = QLineEdit("500")
        self.period_val = QIntValidator(150, 62500)
        self.period_ed.setValidator(self.period_val)
        self.period_ed.textChanged.connect(self.check_state)
        self.period_ed.textChanged.emit(self.period_ed.text())

        self.avg_ed = QLineEdit("1")
        self.avg_val = QIntValidator(1, 240)
        self.avg_ed.setValidator(self.avg_val)
        self.avg_ed.textChanged.connect(self.check_state)
        self.avg_ed.textChanged.emit(self.avg_ed.text())

        self.freqlab = QLabel("")
        self.ttotlab = QLabel("")
        
        
        gr1.addWidget(self.fps_ed, 0, 1)
        gr1.addWidget(self.period_ed, 1, 1)
        gr1.addWidget(self.avg_ed, 2, 1)
        gr1.addWidget(QLabel("Freq (Hz)"), 3, 0)
        gr1.addWidget(self.freqlab, 3, 1)
        gr1.addWidget(QLabel("Tempo (s)"), 4, 0)
        gr1.addWidget(self.ttotlab, 4, 1)
        
                      
        self.confgr.setEnabled(False)

        vb2.addLayout(gr1)
        self.confbut = QPushButton("Configurar")
        self.confbut.clicked.connect(self.config)
        
        vb2.addWidget(self.confbut)
        
        self.confgr.setLayout(vb2)
        
        self.widget.setLayout(vb)
    def ipaddr(self):
        return self.ip_ed.text().strip()
        
        
    def connect(self):
        if self.connected:
            self.connbut.setText("Conectar")
            self.confgr.setEnabled(False)
            self.zerobut.setEnabled(False)
            self.listsbut.setEnabled(False)
            self.dev.close()
            self.dev = None
            self.connected = False
            
        else:
            ip = self.ipaddr()
            if scani.check_server(ip, 23, 2):
                try:
                    self.dev = scani.Scanivalve(ip)
                except:
                    QMessageBox.warning(self, "Erro", "Não foi possível conectar com o Scanivalve")
                    return

                try:
                    self.model = self.dev.get_model()
                    lists = self.dev.list_any_map("S")
                except:
                    QMessageBox.warning(self, "Problemas com Scanivalve",
                                        "Problemas na configuração do Scanivalve")
                    return
                fps = lists['FPS']
                avg = lists['AVG']
                period = lists['PERIOD']
                self.fps_ed.setText(fps)
                self.period_ed.setText(period)
                self.avg_ed.setText(avg)

                self.freqlab.setText(str(1/self.dev.dt))
                self.ttotlab.setText(str(self.dev.dt*int(fps)))
                
                if self.model=='3017':
                    self.period_val.setBottom(500)
                    self.avg_val.setTop(32767)
                else:
                    self.period_val.setBottom(150)
                    self.avg_val.setTop(240)
                    
                    
                self.connbut.setText("DESconectar")
                self.confgr.setEnabled(True)
                self.listsbut.setEnabled(True)
                self.zerobut.setEnabled(True)
                self.connected = True
                return
            else:
                QMessageBox.warning(self, "Sem conexão", "Não foi possível conectar com o scanivalve")
                return
    def check_state(self, *args, **kwargs):
        sender = self.sender()
        validator = sender.validator()
        state = validator.validate(sender.text(), 0)[0]
        if state == QValidator.Acceptable:
            color = '#c4df9b' # green
            #elif state == QtGui.QValidator.Intermediate:
            #    color = '#fff79a' # yellow
        else:
            color = '#f6989d' # red
        sender.setStyleSheet('QLineEdit { background-color: %s }' % color)
        
    def config(self):
        avg = self.avg_ed.text()
        state = self.avg_val.validate(avg, 0)[0]
        if state != QValidator.Acceptable:
            QMessageBox.warning(self, "Valor ilegal", "AVG está fora dos valores permitidos")
            return

        period = self.period_ed.text()
        state = self.period_val.validate(period, 0)[0]
        if state != QValidator.Acceptable:
            QMessageBox.warning(self, "Valor ilegal", "PERIOD está fora dos valores permitidos")
            return

        fps = self.fps_ed.text()
        state = self.fps_val.validate(fps, 0)[0]
        if state != QValidator.Acceptable:
            QMessageBox.warning(self, "Valor ilegal", "FPS está fora dos valores permitidos")
            return

        self.dev.config(FPS=int(fps), AVG=int(avg), PERIOD=int(period))

        self.freqlab.setText("{:05.3f}".format(1/self.dev.dt))
        self.ttotlab.setText("{:05.3f}".format(self.dev.dt * int(fps)))
        
        return None
    def hard_zero(self):
        if self.dev is not None:
            self.dev.hard_zero()
            self.setEnabled(False)
            QtTest.QTest.qWait(15000)
            self.setEnabled(True)
        return None
    
    def listS(self):
        if self.dev is not None:
            lists = self.dev.list_any("S")
            s = '\n'.join([' '.join(l) for l in lists])
            QMessageBox.information(self, "LIST S", s)
        return None
    
        
    def scanivalve(self):
        return self.dev
    
                    
        

if __name__=='__main__':
    app = QApplication([])

    s = ScaniGUI()
    s.show()

    sys.exit(app.exec_())
    
