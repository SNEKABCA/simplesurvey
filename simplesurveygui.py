from __future__ import division, print_function
import sssettings
import sys
import math
import utm
import fractions

"""
Simple Survey program

Copyright 2018 Michael Torrie
torriem@gmail.com

Licensed under the GPLv3
"""

# load either PySide or PyQt using wrapper module
from qt5pick import QtCore, QtGui, QtWidgets, Slot, Signal, QtPositioning, load_ui, QtNetwork, QtSerialPort

# TODO: some kind of search path for these files
SERIAL_BAUD_UI = 'serialbaud.ui'
SERVER_DIALOG_UI = 'serverdialog.ui'
SIMPLE_SURVEY_UI = 'simplesurvey.ui'

def footinch(metres):
    if metres < 0:
        sign = '-'
        metres = -metres
    else: sign = ''

    feet = int(metres * 39.3701 / 12)
    print (feet)
    if feet:
        feet = "%d' " % feet
    else:
        feet = ""

    inches = int(metres * 39.3701) % 12
    if inches:
        inches = '%d' % inches
    else:
        inches = ''

    decimal = int((metres * 39.3701 - int(metres * 39.3701)) * 16)
    
    if decimal:
        gcd = fractions.gcd(decimal, 16)
        frac = "-%d/%d" % (decimal / gcd, 16/ gcd)
    else:
        frac = ''

    return '%s%s%s%s"' % (sign,feet, inches, frac)

def get_zone_number(lat, lon):
    """
    algorithm borrowed from utm module

    where possible it returns a floating point pseudo utm zone
    so that our local grid always lines up with due north
    """

    if 56 <= lat < 64 and 3 <= lon < 12:
        return 32

    if 72 <= lat <= 84 and lon >= 0:
        if lon <= 9: return 31
        elif lon <= 21: return 33
        elif lon <= 33: return 35
        elif lon <= 42: return 37

    return (lon + 180) / 6 + 1

class SerialBaudDialog(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super(SerialBaudDialog, self).__init__(*args, **kwargs)
        #TODO: pull this in from qsettings
        self._speed = 9600
        load_ui(SERIAL_BAUD_UI, self)


    def get_speed(self):
        return self._speed

    def set_speed(self, speed):
        self._speed = speed
        self.speed_picker.setCurrentText(str(speed))

    speed = property(get_speed, set_speed)

    @Slot(str)
    def on_speed_picker_activated(self, speed_txt):
        speed = int(speed_txt)
        if speed > 0:
            self._speed = speed
        else:
            QtWidgets.QMessageBox.critical(self, 'Invalid speed!','Baudrate you entered is not valid! Please pick or enter a valid speed.',QtWidgets.QMessageBox.Ok)
            return False

    @Slot(str)
    def on_speed_picker_highlighted(self,speed_txt):
        self._speed = int(speed_txt)

class ServerDialog(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super(ServerDialog, self).__init__(*args, **kwargs)
        self._hostname = None
        self._port = 0
        load_ui(SERVER_DIALOG_UI, self)

    def get_hostname(self):
        return self._hostname

    def set_hostname(self, hostname):
        self._hostname = hostname
        self.host_box.setText(hostname)

    def get_port(self):
        return self._port

    def set_port(self, port):
        self._port = port
        self.port_spin.setValue(port)

    hostname = property(get_hostname, set_hostname)
    port = property(get_port, set_port)

    @Slot(str)
    def on_host_box_textChanged(self,text):
        self._hostname = text

    @Slot(int)
    def on_port_spin_valueChanged(self,portno):
        self._port = portno

class SimpleSurveyGui(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super(SimpleSurveyGui, self).__init__(*args, **kwargs)

        self.nmea_source = None
        self.nmea_logfile = None
        self.serialport = None
        self.tcpSocket = None

        #nmea_source.error.connect(self.error)

        self.utm_zone = None
        self.start = None      #QPositionInfo
        self.start_pos = None  #UTM coordinates
        self.mark = None       #UTM coordinates
        self.mark_pos = None   #QPositionInfo
        self.altitude = None
        self.start_altitude = None
        self.metric = True
        self.position = None
        
        self.settings = sssettings.SSSettings()

        load_ui(SIMPLE_SURVEY_UI, self)


        self.speed_dialog = SerialBaudDialog(self)
        self.speed_dialog.hide()
        self.speed = int(self.settings.value('serial/baud',9600))
        self.speed_dialog.speed = self.speed

        self.server_dialog = ServerDialog(self)
        self.server_dialog.hide()

        if self.settings.value('server/hostname'):
            self.server_dialog.hostname = self.settings.value('server/hostname')
            self.server_dialog.port = int(self.settings.value('server/port',9999))
        
        self.on_source_label_linkActivated('dummy')
        self.gps_source_pick.setItemData(0,'system')
        self.gps_source_pick.setItemData(1,'simulate')
        self.gps_source_pick.setItemData(2,'server')

        last_path = self.settings.value('source')
        if last_path:
            pick = self.gps_source_pick.findData(last_path)
        else:
            pick = 0

        self.last_source = pick
        self.gps_source_pick.setCurrentIndex(pick)
        self.on_gps_source_pick_activated(pick,True)

    def reset_mark(self):
        self.mark = None
        self.mark_pos = None

        self.mark_easting.clear()
        self.mark_northing.clear()
        self.mark_bearing.clear()
        self.mark_distance.clear()
        self.mark_elevation.clear()
        self.mark_slope.clear()

    def reset_start(self):
        self.reset_mark()
        self.mark_button.setEnabled(False)
        
        self.start = None
        self.start_pos = None
        self.utm_zone = None

        self.start_easting.clear()
        self.start_northing.clear()
        self.start_bearing.clear()
        self.start_distance.clear()
        self.start_elevation.clear()
        self.start_slope.clear()


    @Slot()
    def on_start_button_clicked(self):
        if not self.position: return

        lat = self.position[0]
        lon = self.position[1]

        self.utm_zone = get_zone_number(lat, lon)
        print (self.utm_zone)

        (easting, northing, _, _) = utm.from_latlon(
                 lat, lon,
                 force_zone_number=self.utm_zone)

        self.start = (northing, easting) #TODO: switch these around throughout

        self.start_pos = self.position
        self.start_altitude = self.altitude

        self.reset_mark()
        self.mark_button.setEnabled(True)

    @Slot()
    def on_mark_button_clicked(self):

        lat = self.position[0]
        lon = self.position[1]

        (easting, northing, _, _) = utm.from_latlon(
                 lat, lon,
                 force_zone_number=self.utm_zone)

        self.mark = (northing, easting) #TODO: switch these around throughout

        self.mark_pos = self.position
        self.mark_altitude = self.altitude

    @Slot(str)
    def on_source_label_linkActivated(self, link):
        #print ("clicked on link %s" % link)
        ports = QtSerialPort.QSerialPortInfo.availablePorts()
        for x in range(3,self.gps_source_pick.count()):
            self.gps_source_pick.removeItem(x)

        self.serial_ports = {}
        for port in ports:
            self.serial_ports[port.portName()] = port.systemLocation()
            self.gps_source_pick.addItem(port.portName(), port.systemLocation())

    #@Slot(str)
    #def on_gps_source_pick_activated(self, port_name):
    #    print (port_name)

    @Slot(int)
    def on_gps_source_pick_activated(self, item_number, dontask = False):
        path = self.gps_source_pick.itemData(item_number)

        print (path)

        if path == 'system':
            self._cleanup_sources()
            self.nmea_source = QtPositioning.QGeoPositionInfoSource.createDefaultSource(self)
            if not self.nmea_source: return

        elif path == 'simulate':
            self._cleanup_sources()
            self.nmea_logfile = QtCore.QFile('test2.nmea')
            self.nmea_source = QtPositioning.QNmeaPositionInfoSource(QtPositioning.QNmeaPositionInfoSource.SimulationMode)
            self.nmea_source.setDevice(self.nmea_logfile)
            self.nmea_source.setUpdateInterval(0)
        elif path == 'server':
            if not dontask:
                # only ask for host and port if we're not resuming from
                # last known settings
                self.setEnabled(False)
                self.server_dialog.setEnabled(True)
                self.server_dialog.show()
                result = self.server_dialog.exec()
                self.server_dialog.hide()
                self.setEnabled(True)

                if not result:
                    # reset selection to last one
                    self.gps_source_pick.setCurrentIndex(item_number)
                    return

            hostname = self.server_dialog.hostname
            port = self.server_dialog.port

            self._cleanup_sources()
            self.nmea_source = None
            self.tcpSocket = QtNetwork.QTcpSocket(self)
            self.tcpSocket.error.connect(self.tcp_error)
            self.tcpSocket.connectToHost(hostname, port)

            self.nmea_source = QtPositioning.QNmeaPositionInfoSource(QtPositioning.QNmeaPositionInfoSource.RealTimeMode)
            self.nmea_source.setDevice(self.tcpSocket)
            self.nmea_source.setUpdateInterval(0)

            self.settings.setValue('server/hostname', hostname)
            self.settings.setValue('server/port', port)

        else: #assume serial
            if not dontask:
                self.setEnabled(False)
                self.speed_dialog.setEnabled(True)
                self.speed_dialog.show()
                result = self.speed_dialog.exec()
                self.speed_dialog.hide()
                self.setEnabled(True)
                if not result:
                    #reset to the last source
                    self.gps_source_pick.setCurrentIndex(item_number)
                    return

            baud_rate = self.speed_dialog.speed

            self._cleanup_sources()
            self.nmea_source = None
            self.serialport = QtSerialPort.QSerialPort(path,self)
            self.serialport.setBaudRate(baud_rate,self.serialport.AllDirections)
            self.serialport.setFlowControl(self.serialport.NoFlowControl)
            self.nmea_source = QtPositioning.QNmeaPositionInfoSource(QtPositioning.QNmeaPositionInfoSource.RealTimeMode)
            self.nmea_source.setDevice(self.serialport)
            self.nmea_source.setUpdateInterval(0)
            self.settings.setValue('serial/baud',baud_rate)



        self.latitude_disp.clear()
        self.longitude_disp.clear()
        self.altitude_disp.clear()
        self.heading_disp.clear()
        self.reset_start()
        self.nmea_source.positionUpdated.connect(self.position_updated)
        self.nmea_source.updateTimeout.connect(self.update_timeout)
        self.nmea_source.startUpdates()
        self.last_source = item_number

        self.settings.setValue('source',path)

        #todo clear mark and start

    def _cleanup_sources(self):
        if self.nmea_source:
            del self.nmea_source
            self.nmea_source = None

        if self.nmea_logfile:
            self.nmea_logfile.close()
            del self.nmea_logfile
            self.nmea_logfile = None

        if self.tcpSocket:
            self.tcpSocket.close()
            del self.tcpSocket
            self.tcpSocket = None

        if self.serialport:
            self.serialport.close()
            del self.serialport
            self.serialport = None

    @Slot(QtNetwork.QAbstractSocket.SocketError)
    def tcp_error(self, socketerror):
        QtWidgets.QMessageBox.critical(self, 'Could not connect to host','Could not establish a TCP/IP connection to the GPS unit.  Please make sure the host or IP address and port number are correct.',QtWidgets.QMessageBox.Ok)
        self.gps_source_pick.setCurrentIndex(0)
        self.on_gps_source_pick_activated(0)

    @Slot(bool)
    def on_units_metres_toggled(self, state):
        self.metric = state

    @Slot(bool)
    def on_units_feet_toggled(self, state):
        self.metric = not state

    @Slot(QtPositioning.QGeoPositionInfo)
    def position_updated(self, position_info):
        #(lat, lon) = (position_info.coordinate().latitude(), 
        #              position_info.coordinate().longitude())

        # Using a fractional UTM zone creates a pseudo UTM zone where
        # north is closer to real north.

        self.latitude_disp.setText("%f" % position_info.coordinate().latitude())
        self.longitude_disp.setText("%f" % position_info.coordinate().longitude())
        if not math.isnan(position_info.coordinate().altitude()):
            self.altitude = position_info.coordinate().altitude()

        if self.altitude:
            if self.metric:
                self.altitude_disp.setText('%.2f m' % self.altitude)
            else:
                self.altitude_disp.setText(footinch(self.altitude))

        if position_info.hasAttribute(position_info.Direction):
            self.heading_disp.setText('%.1f deg' % position_info.attribute(position_info.Direction))

        #if position_info.hasAttribute(position_info.GroundSpeed):
        #    print (position_info.attribute(position_info.GroundSpeed) * 1.61)

        self.position = (position_info.coordinate().latitude(),
                         position_info.coordinate().longitude())

        if self.utm_zone: #start button has been pressed
            (easting, northing, _, _) = utm.from_latlon(
                 position_info.coordinate().latitude(), 
                 position_info.coordinate().longitude(),
                 force_zone_number=self.utm_zone)

            if not self.start_altitude:
                self.start_altitude = self.altitude

            deltan = (northing - self.start[0])
            deltae = (easting - self.start[1])
            if deltan < 0: 
                deltan_dir = "South"
                deltan = -deltan
            else: deltan_dir = "North"

            if deltae < 0: 
                deltae_dir = "West"
                deltae = -deltae
            else: deltae_dir = "East"

            if self.metric:
                self.start_northing.setText("%.3f m %s" % (deltan,deltan_dir))
                self.start_easting.setText('%.3f m %s' % (deltae,deltae_dir))
            else:
                self.start_northing.setText('%s %s' % (footinch(deltan), deltan_dir))
                self.start_easting.setText('%s %s' % (footinch(deltae), deltae_dir))

            bearing = ( 360 - math.degrees(math.atan2(northing - self.start[0],
                                         easting - self.start[1])) +
                        90 ) % 360

            self.start_bearing.setText(u'%.1f\u00b0' % bearing)

            distance = math.sqrt((northing - self.start[0]) *
                                 (northing - self.start[0]) +
                                 (easting - self.start[1]) *
                                 (easting - self.start[1]))

            if self.metric:
                self.start_distance.setText('%.3f m' % distance)
            else:
                self.start_distance.setText(footinch(distance))

            if self.altitude and self.start_altitude:
                if self.metric:
                    self.start_elevation.setText('%.2f m' % (self.altitude - self.start_altitude))
                else:
                    self.start_elevation.setText(footinch(self.altitude - self.start_altitude))
                if distance > 0:
                    slope_percent = (self.altitude - self.start_altitude) / distance
                    slope_angle = math.degrees(math.atan(slope_percent))
                    self.start_slope.setText(u"{:.1%} or {:.1f}\u00b0".format(slope_percent,
                                                                             slope_angle))
                    

            if self.mark: #mark button has been pressed
                (easting, northing, _, _) = utm.from_latlon(
                     position_info.coordinate().latitude(), 
                     position_info.coordinate().longitude(),
                     force_zone_number=self.utm_zone)

                if not self.mark_altitude:
                    self.mark_altitude = self.altitude

                deltan = (northing - self.mark[0])
                deltae = (easting - self.mark[1])
                if deltan < 0: 
                    deltan_dir = "South"
                    deltan = -deltan
                else: deltan_dir = "North"

                if deltae < 0: 
                    deltae_dir = "West"
                    deltae = - deltae
                else: deltae_dir = "East"

                if self.metric:
                    self.mark_northing.setText("%.3f m %s" % (deltan,deltan_dir))
                    self.mark_easting.setText('%.3f m %s' % (deltae,deltae_dir))
                else:
                    self.mark_northing.setText('%s %s' % (footinch(deltan), deltan_dir))
                    self.mark_easting.setText('%s %s' % (footinch(deltae), deltae_dir))

                bearing = ( 360 - math.degrees(math.atan2(northing - self.mark[0],
                                             easting - self.mark[1])) +
                            90 ) % 360

                self.mark_bearing.setText(u'%.1f\u00b0' % bearing)

                distance = math.sqrt((northing - self.mark[0]) *
                                     (northing - self.mark[0]) +
                                     (easting - self.mark[1]) *
                                     (easting - self.mark[1]))
                if self.metric:
                    self.mark_distance.setText('%.3f m' % distance)
                else:
                    self.mark_distance.setText(footinch(distance))

                if self.altitude and self.start_altitude:
                    if self.metric:
                        self.mark_elevation.setText('%.2f m' % (self.altitude - self.mark_altitude))
                    else:
                        self.mark_elevation.setText(footinch(self.altitude - self.mark_altitude))
                    if distance > 0:
                        slope_percent = (self.altitude - self.mark_altitude) / distance
                        slope_angle = math.degrees(math.atan(slope_percent))
                        self.mark_slope.setText(u"{:.1%} or {:.1f}\u00b0".format(slope_percent,
                                                                                 slope_angle))

    @Slot()
    def update_timeout(self):
        print ("timed out")

    @Slot(QtPositioning.QGeoPositionInfoSource.Error)
    def error(self, positioningError):
        print(positioningError)

if __name__ == "__main__":
    import signal
    app = QtWidgets.QApplication(sys.argv)

    QtCore.QCoreApplication.setOrganizationName("Simple Survey")
    QtCore.QCoreApplication.setApplicationName("Simple Survey")

    def ctrl_break(signum, frame):
        t.close()

    signal.signal(signal.SIGINT, ctrl_break)

    t = SimpleSurveyGui()
    t.setWindowTitle('Simple Survey')
    t.show()
    app.exec_()


