from __future__ import division, print_function
import sys
import math
import utm
import fractions


# load either PySide or PyQt using wrapper module
from qt5pick import QtCore, QtGui, QtWidgets, Slot, Signal, QtPositioning, load_ui, QtNetwork


def footinch(metres):
    if metres < 0:
        sign = '-'
        metres = -metres
    else: sign = ''

    feet = int(metres / 3.2808)
    if feet:
        feet = "%d' " % feet
    else:
        feet = ""

    inches = int(metres * 39.3701) % 12
    if inches:
        inches = '%d ' % inches
    else:
        inches = ''

    decimal = int((metres * 39.3701 - int(metres * 39.3701)) * 16)
    
    if decimal:
        gcd = fractions.gcd(decimal, 16)
        frac = "%d/%d" % (decimal / gcd, 16/ gcd)
    else:
        frac = ''

    return '%s%s%s"' % (feet, inches, frac)

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

class PositionTest(QtWidgets.QWidget):

    def __init__(self, mode, qiodevice, interval, *args, **kwargs):
        super(PositionTest, self).__init__(*args, **kwargs)
        #self.logfile = QtCore.QFile('/tmp/test.nmea')

        #self.nmea_source = QtPositioning.QNmeaPositionInfoSource(QtPositioning.QNmeaPositionInfoSource.SimulationMode)
        #self.nmea_source = QtPositioning.QNmeaPositionInfoSource(mode)
        #self.nmea_source.setDevice(qiodevice)
        #self.nmea_source.setUpdateInterval(interval)

        self.nmea_source = QtPositioning.QGeoPositionInfoSource.createDefaultSource(self)

        self.nmea_source.positionUpdated.connect(self.position_updated)
        self.nmea_source.updateTimeout.connect(self.update_timeout)
        #nmea_source.error.connect(self.error)

        self.utm_zone = None
        self.start = None      #QPositionInfo
        self.start_pos = None  #UTM coordinates
        self.mark = None       #UTM coordinates
        self.mark_pos = None   #QPositionInfo
        self.altitude = None
        self.start_altitude = None
        self.metric = True

        load_ui('simplesurvey.ui', self)

        self.nmea_source.startUpdates()

    @Slot()
    def on_start_button_clicked(self):
        self.utm_zone = 12.3828636667

        lat = self.position.coordinate().latitude()
        lon = self.position.coordinate().longitude()

        self.utm_zone = get_zone_number(lat, lon)
        print (self.utm_zone)

        (easting, northing, _, _) = utm.from_latlon(
                 lat, lon,
                 force_zone_number=self.utm_zone)

        self.start = (northing, easting) #TODO: switch these around throughout

        self.start_pos = self.position
        if math.isnan(self.start_pos.coordinate().altitude()):
            self.start_altitude = None
        else:
            self.start_altitude = self.start_pos.coordinate().altitude()

        self.mark = None
        self.mark_pos = None
        self.mark_button.setProperty('enabled', True)

    @Slot()
    def on_mark_button_clicked(self):
        print ("mark clicked.") 

        lat = self.position.coordinate().latitude()
        lon = self.position.coordinate().longitude()

        (easting, northing, _, _) = utm.from_latlon(
                 lat, lon,
                 force_zone_number=self.utm_zone)

        self.mark = (northing, easting) #TODO: switch these around throughout

        self.mark_pos = self.position
        if math.isnan(self.mark_pos.coordinate().altitude()):
            self.mark_altitude = None
        else:
            self.mark_altitude = self.mark_pos.coordinate().altitude()

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

        self.position = position_info

        if self.utm_zone: #start button has been pressed
            (easting, northing, _, _) = utm.from_latlon(
                 position_info.coordinate().latitude(), 
                 position_info.coordinate().longitude(),
                 force_zone_number=self.utm_zone)

            if not self.start_altitude:
                self.start_altitude = self.altitude

            deltan = (northing - self.start[0])
            deltae = (easting - self.start[1])
            if deltan < 0: deltan_dir = "South"
            else: deltan_dir = "North"

            if deltae < 0: deltae_dir = "West"
            else: deltae_dir = "East"

            if self.metric:
                self.start_northing.setText("%.3f m %s" % (deltan,deltae_dir))
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
            if self.mark: #mark button has been pressed
                (easting, northing, _, _) = utm.from_latlon(
                     position_info.coordinate().latitude(), 
                     position_info.coordinate().longitude(),
                     force_zone_number=self.utm_zone)

                if not self.mark_altitude:
                    self.mark_altitude = self.altitude

                deltan = (northing - self.mark[0])
                deltae = (easting - self.mark[1])
                if deltan < 0: deltan_dir = "South"
                else: deltan_dir = "North"

                if deltae < 0: deltae_dir = "West"
                else: deltae_dir = "East"

                if self.metric:
                    self.mark_northing.setText("%.3f m %s" % (deltan,deltae_dir))
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




    @Slot()
    def update_timeout(self):
        print ("timed out")

    @Slot(QtPositioning.QGeoPositionInfoSource.Error)
    def error(self, positioningError):
        print(positioningError)

if __name__ == "__main__":
    import signal
    app = QtWidgets.QApplication(sys.argv)
    nmea = QtCore.QFile('test1.nmea')
    #t = PositionTest(QtPositioning.QNmeaPositionInfoSource.RealTimeMode, nmea, 500)
    t = PositionTest(QtPositioning.QNmeaPositionInfoSource.SimulationMode, nmea, 0)

    def ctrl_break(signum, frame):
        t.close()

    signal.signal(signal.SIGINT, ctrl_break)
    t.setWindowTitle('Simple Survey')
    t.show()
    app.exec_()


