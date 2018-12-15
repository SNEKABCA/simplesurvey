#Simple Survey
##Introduction
This program is a simple GUI that works with NMEA GPS data sources to allow simply surveying.  With a suitably accurate RTK GPS source, it's designed to replace a tape measure and transit for simple surveying tasks, such as measuring out a square plan for constructing a building, or making a flat pad to pour concrete onto. To that end, this program allows for making relative measurements in three dimensions from a starting point.
##License
Simple Survey is licensed under the terms of the GNU GPLv3.
##Requirements
Simple Survey requires Python 3.4 or greater, and PyQt5 for Python 3 installed. Should work on any platform that supports PyQt5.  Currently PySide2 does not expose the QtPositioning API.
##How to use
You'll need an RTK GPS receiver capable of transmitting NMEA sentences by serial or TCP/IP connection to the laptop this program will run on.  RMC and GGA sentences are all you need. If your GPS receiver is mounted on a tripod, a plumb bob hanging from the underside can help you accurately measure a position.

Run the "simplesurvey.py" file and use the GUI connect to the host/port or serial port and it should start displaying latitude, longitude, and elevation data.  Click "Start" to mark a beginning position.  Now as you move the receiver, you will get measurements relative to that starting position.  If you need subsequent relative measurements, you can click "Mark" to mark a point to measure from, while still seeing measurements against the original start position also.

The relative measurements are given in north and south offsets from the starting position, as well as the total distance and bearing from start. To make the math simpler, Simple Survey turns latitude and longitude into a pseudo UTM coordinate, with the pseudo zone centered on the start longitude. This way we can avoid UTM grid distortion away from the central longitude.
##Limitations
To minimize grid distortion, relative distances being measured are really intended to be no more than hundreds of feet.

Height or elevation displayed by Simple Survey is GPS height above the ellipsoid, not orthographic height above sea level. But for relative measuring it will be as accurate as your GPS source.
##Future
An app on a laptop is of limited use in the field.  The next version of this program will be written in QtQuick, probably entirely in Javascript, and should be portable to Android.  Using the built-in location services, combined with the Lefebure NTRIP Client for Android, should allow the use of many RTK systems such as the Reach RS, Piksi, etc, on an Android device.