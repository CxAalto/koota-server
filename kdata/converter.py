"""Various converters for raw data.

This module provides for postprocessing of raw data.  Basically, it
provides classes that take an iterator of raw data ((datetime, str)
tuples), and returns iterators over preprocessed data in some sort of
tabular format.  Each converter has these methods:

Converter(iterator[, time])
    New method of usage.

converter.run()
    New method of usage.  Instantiating an object as above and running
    like this has the same effect as Converter.convert() (below), but
    will handle errors.  Error messages are placed in converter.errors
    and converter.error_dict.  TODO: finish documenting this.  TODO:
    more flexible error handling in in this method.

Converter.convert(iterator[, time])
    The argument to this function should be an iterator over
    (datetime, str) tuples.  The datetime.datetime is the raw data
    packet time (when data was recceived by the server).  The str
    is the raw string data which the device has sent to the server.
    The return value is an iterator over tuples, each tuple
    represents one row of output as Python objects.

    This is the core logic of this module.  Each converter class
    should overwrite this function to implement its logic.
    Typically, it would be something like: json decode the string
    data, extract info, yield one or more lines.

Converter.header2()
    Returns the output column names, list of strings.  Used in csv, for
    example.  The default implementation just returns self.header.
    (It's a bit hackish to have both header attribute and header2 method,
    but things changed and a quick hack was introduced pending a final
    solution).

Converter.name()
    Returns the human-readable name of the converter.

Converter.desc
    Human-readable description of the converter.

To make a new converter, you would basically:

- Look to find a similar converter (for example, all of the Purple
  Robot ones are similar)
- Build on (copy or subclass) that.
- Change the convert() method
- Change the header (header attribute)


This file, when run a a script, provides a simple command line interface
(at the bottom).

To access data from Python code, there is no shortcut method right now,
you should do this.  There is an example script at the bottom of this
file.:

- import converter
- converter_class = converter.PRScreen  # for example
- header = converter_class.header2()
- Without error handling (run this if you want to handle them yourself):
  for row in converter_class.convert(rows):
      ... # do something with each row
- There is a second option with error handling:
  converter = converter_class(rows)
  for row in converter.run():
      ... # do something with each row
  # At the end
  converter.errors
  converter.errors_dict
"""

from __future__ import print_function

from six import iteritems, itervalues, string_types
from six.moves import zip

from base64 import urlsafe_b64encode
from calendar import timegm
import collections
import csv
from datetime import datetime, timedelta
from hashlib import sha256
import itertools
try:
    from ujson import dumps, loads
except:
    from json import loads, dumps
from math import log
import time
import time as mod_time
import sys

import logging
logger = logging.getLogger(__name__)


# Make a safe-hash function.  This can be used to hide identifiers.
# This currently uses sha256 + a random secret salt for security.  We
# go through thees steps to a) ensure that we never use a hard-coded
# salt, and b) not depend on django.
try:
    from django.conf import settings
    SALT = settings.SALT
    del settings
except:
    # Make a random salt that changes on every invocation.  This is
    # not stable (changes every time the process runs), but is the
    # safest option until there is some way to specify things.  So far
    # there is no point where comparing across invocations is
    # important.
    import random
    SALT = bytes(bytearray((random.randint(0, 255) for _ in range(32))))
def safe_hash(data):
    """Make a safe hash function for identifiers."""
    if not isinstance(data, bytes):
        data = data.encode('utf8')
    return urlsafe_b64encode(sha256(SALT+data).digest()[:9]).decode('ascii')



# This is defined in kdata/views_admin.py.  Copied here so that there are no dependencies.
def human_bytes(x):
    """Add proper binary prefix to number in bytes, returning string"""
    if x <= 0:
        return '%6.2f %-3s'%(x, 'B')
    unit_list = [ 'B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']
    exponent = int(log(x, 1024))
    quotient = x / 1024**exponent
    return '%6.2f %-3s'%(quotient, unit_list[exponent])


class _Converter(object):
    per_page = 25
    header = [ ]
    desc = ""
    @classmethod
    def name(cls):
        """Shortcut to return class name on either object or instance"""
        return cls.__name__
    @classmethod
    def header2(cls):
        """Return header, either dynamic or static."""
        if hasattr(cls, 'header') and cls.header:
            return cls.header
        return ['time'] + [x[0].lower() for x in cls.fields]
    def __init__(self, rows=None, time=lambda x: x):
        # Warning: during template rendering this is used in a variable as "_Converter.name"
        pass
        self.rows = rows
        self.time = time
        self.errors = [ ]
        self.errors_dict = collections.defaultdict(int)
    def run(self):
        """Run through the conversion.

        If any errors are raised during conversion, do not fail.
        Instead, log those errors and continue.  This is a wrapper
        around the direct "convert" statements.  When this method is
        being used, the converter class must be instantiated with the
        rows/time arguments that .convert() takes.
        """
        # Convert the rows into an iterator explicitely here.  For
        # objects like querysets or generators, this has no effect.
        # But for lists/tuples, if we don't do this, every repitition
        # of the while loop *restarts*, which is not what we want.  By
        # making the iterator here, each repitition in the loop below
        # starts where the previous left off.
        rows = iter(self.rows)
        # Until we are exhausted (we get to the break)
        while True:
            try:
                # Iterate through yielding everything.
                for x in self.convert(rows, self.time):
                    yield x
                # If we manage to finish, break loop and we are done.
                # Everything is simple.
                break
            # If there was exception, do something with it, then
            # restart the while loop.  It will break when iterator
            # exhausted.  The handling colud be improved later.
            except Exception as e:
                if len(self.errors) < 100:
                    logger.error("Exception in %s", self.__class__.__name__)
                    import traceback
                    logger.error(e)
                    logger.error(traceback.format_exc())
                    self.errors.append(e)
                self.errors_dict[str(e)] += 1
                #self.errors_emit_error(e)
                # Possibly we need to prevent each next traceback from
                # storing the previous traceback, too.
                del e

class Raw(_Converter):
    header = ['time', 'data']
    desc = "Raw data packets"

    def convert(self, queryset, time=lambda x:x):
        for dt, data in queryset:
            yield time(timegm(dt.utctimetuple())), data

class MurataBSN(_Converter):
    _header = ['time',
              'hr', 'rr', 'sv', 'hrv', 'ss',
              'status', 'bbt0', 'bbt1', 'bbt2',
              'time2',
             ]
    _header_debug = ['row_i', 'delta_i', 'time_packet', 'offset_s',
                     'xml_start_time',]
    device_class = 'MurataBSN'
    @classmethod
    def header2(cls):
        if cls.debug:
            return cls._header + cls._header_debug
        return cls._header
    desc = "Murata sleep sensors, basic information."
    debug = False
    safe = False
    def convert(self, rows, time=lambda x:x):
        from defusedxml.ElementTree import fromstring as xml_fromstring
        from dateutil import parser as date_parser
        count = 0
        for ts_packet, data in rows:
            unixtime_packet = timegm(ts_packet.timetuple())
            # Do various XML parsing
            doc = xml_fromstring(data)
            node = doc[0][0]
            device_id = node.attrib['id']
            start_time = doc[0][0][0][0].attrib['time']
            ts = date_parser.parse(start_time)
            values = doc[0][0][0][0][9]
            # This is O(n_rows) in memory here.  n_rows is supposed to
            # be always small (~90 max).  Should this assumption be
            # violated, we need a two-pass method.  Just save
            # last_row_i on the first pass, then do second pass.
            rows = [ ]
            reader = csv.reader(values.text.split('\n'))
            for row in reader:
                if not row: continue
                rows.append(row)
            last_time_i = int(rows[-1][0])
            for row in rows:
                #count += 1 ; print count
                unixtime = timegm(ts.timetuple()) + int(row[0])
                # The actual data.  In safe mode, replace everything
                # with null strings.
                data_values = tuple(row[1:])
                if self.safe:
                    data_values = tuple( "" for _ in data_values )
                # These values are used for debuging.  In debug mode,
                # include a bunch of extra data.  In normal mode,
                # include the field time2, which is the time as
                # calcultaed from the packet.
                unixtime_from_packet = unixtime_packet - ( last_time_i - int(row[0]))
                if not self.debug:
                    extra_data = (time(unixtime_from_packet), )
                else:
                    extra_data = (
                        time(unixtime_from_packet),
                        int(row[0]),
                        last_time_i - int(row[0]),
                        time(unixtime_packet),
                        unixtime_from_packet-unixtime,
                        start_time,
                    )
                # Compose and return columns
                yield (time(unixtime), ) + data_values + extra_data
class MurataBSNDebug(MurataBSN):
    desc = "Murata sleep sensors with extra debugging info."
    debug = True
class MurataBSNSafe(MurataBSN):
    desc = "Murata sleep sensors with debugging info and data removed."
    safe = True
    debug = True



class PRProbes(_Converter):
    header = ['time', 'packet_time', 'probe', 'data']
    desc = "Purple Robot raw JSON data, divided into each probe"
    device_class = 'PurpleRobot'
    def convert(self, queryset, time=lambda x:x):
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                yield (time(probe['TIMESTAMP']),
                       time(timegm(ts.utctimetuple())),
                       probe['PROBE'].split('.')[-1],
                       dumps(probe))

class PRBattery(_Converter):
    header = ['time', 'level', 'plugged']
    desc = "Battery level"
    device_class = 'PurpleRobot'
    def convert(self, queryset, time=lambda x:x):
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.BatteryProbe':
                    yield (time(probe['TIMESTAMP']),
                           int(probe['level']),
                           int(probe['plugged']),
                          )
class PRScreen(_Converter):
    header = ['time', 'onoff']
    desc = "Screen on/off times"
    device_class = 'PurpleRobot'
    def convert(self, queryset, time=lambda x:x):
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.ScreenProbe':
                    yield (time(probe['TIMESTAMP']),
                           int(probe['SCREEN_ACTIVE']),
                          )
class PRWifi(_Converter):
    """WifiAccessPointsProbe converter.

    This is a bit complex because we handle several cases (and handle
    them twice).
    - Current network is handled differently from the list of all
      networks.
    - hash if the class attribute "safe" is set.
    """
    header = ['time', 'essid', 'bssid', 'current', 'strength']
    desc = "Wifi networks found"
    device_class = 'PurpleRobot'
    safe = False
    def convert(self, queryset, time=lambda x:x):
        safe = self.safe
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.WifiAccessPointsProbe':
                    ts = time(probe['TIMESTAMP'])
                    # Emit a special row for CURRENT_SSID
                    if 'CURRENT_BSSID' in probe \
                       and probe['CURRENT_BSSID'] != '00:00:00:00:00:00':
                        current_ssid = probe['CURRENT_SSID']
                        # On some devices the current SSID is quoted.
                        # Json decode it in that case.
                        if current_ssid.startswith('"'):
                            current_ssid = loads(current_ssid)
                        # Handle hashing if we are in safe mode.  In
                        # safe mode, hash the things, but *only* if it
                        # is non-null.  So, this is actually two
                        # levels of conditional.
                        if safe:
                            current_ssid = (safe_hash(current_ssid)
                                            if current_ssid else current_ssid)
                            current_bssid = (safe_hash(probe['CURRENT_BSSID'])
                                             if safe else probe['CURRENT_BSSID'])
                        yield (ts,
                               current_ssid,
                               current_bssid,
                               1,
                               probe['CURRENT_RSSI'],
                           )
                    for ap_info in probe['ACCESS_POINTS']:
                        # Again, two layers of conditionals because we
                        # only hash if non-null.
                        ssid = ap_info['SSID']
                        bssid = ap_info['BSSID']
                        if safe:
                            ssid  = safe_hash(ssid)  if ssid else ssid
                            bssid = safe_hash(bssid) if bssid else bssid
                        yield (ts,
                               ssid,
                               bssid,
                               0,
                               ap_info['LEVEL'],
                               )
class PRWifiSafe(PRWifi):
    safe = True
class PRBluetooth(_Converter):
    header = ['time',
              'bluetooth_name',
              'bluetooth_address',
              'major_class',
              'minor_class',
              ]
    desc = "Bluetooth devices found"
    device_class = 'PurpleRobot'
    safe = False
    def convert(self, queryset, time=lambda x:x):
        safe = self.safe
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.BluetoothDevicesProbe':
                    ts = time(probe['TIMESTAMP'])
                    for dev_info in probe['DEVICES']:
                        # available keys:
                        # {"BLUETOOTH_NAME":"2a1327a019948590cccc3ff20fe3dbdb",
                        #  "BOND_STATE":"Not Paired",
                        #  "DEVICE MAJOR CLASS":"0x00000100 Computer",
                        #  "BLUETOOTH_ADDRESS":"6841398ddc6f2cee644a3bcf39b894d2",
                        #  "DEVICE MINOR CLASS":"0x0000010c Laptop"}
                        name = dev_info.get('BLUETOOTH_NAME', '')
                        address = dev_info.get('BLUETOOTH_ADDRESS', '')
                        if safe:
                            name = safe_hash(name)
                            address = safe_hash(address)
                        yield (ts,
                               name,
                               address,
                               dev_info.get('DEVICE MAJOR CLASS',''),
                               dev_info.get('DEVICE MINOR CLASS',''),
                               )
class PRBluetoothSafe(PRBluetooth):
    safe = True
class PRStepCounter(_Converter):
    header = ['time', 'step_count', 'last_boot']
    desc = "Step counter"
    device_class = 'PurpleRobot'
    def convert(self, queryset, time=lambda x:x):
        last_boot = 0
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.RobotHealthProbe':
                    last_boot = probe['LAST_BOOT']/1000
                    yield (time(probe['TIMESTAMP']), '', time(last_boot))
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.StepCounterProbe':
                    yield (time(probe['TIMESTAMP']+last_boot),
                           probe['STEP_COUNT'],
                           )
class PRDeviceInUse(_Converter):
    header = ['time', 'in_use']
    desc = "Purple Robot DeviceInUseFeature"
    device_class = 'PurpleRobot'
    def convert(self, queryset, time=lambda x:x):
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.features.DeviceInUseFeature':
                    yield (time(probe['TIMESTAMP']),
                           int(probe['DEVICE_ACTIVE']))
class PRLocation(_Converter):
    desc = 'Purple Robot location probe (builtin.LocationProbe)'
    header = ['time', 'provider', 'lat', 'lon', 'accuracy']
    def convert(self, queryset, time=lambda x:x):
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.LocationProbe':
                    yield (time(probe['TIMESTAMP']),
                           probe['PROVIDER'],
                           probe['LATITUDE'],
                           probe['LONGITUDE'],
                           probe['ACCURACY'],
                           )
class PRAccelerometer(_Converter):
    desc = 'Purple Robot Accelerometer (builtin.AccelerometerProbe).  Some metadata is not yet included here.'
    header = ['event_timestamp', 'normalized_timestamp', 'x', 'y', 'z', 'accuracy']
    device_class = 'PurpleRobot'
    def convert(self, queryset, time=lambda x:x):
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.AccelerometerProbe':
                    #yield probe['MAXIMUM_RANGE']
                    #probe['RESOLUTION']
                    for t1, t2, x, y, z, a in zip(probe['EVENT_TIMESTAMP'],
                                                  probe['NORMALIZED_TIMESTAMP'],
                                                  probe['X'],
                                                  probe['Y'],
                                                  probe['Z'],
                                                  probe['ACCURACY'],
                                              ):
                        yield time(t1), time(t2), x, y, z, a
class PRLightProbe(_Converter):
    desc = 'Purple Robot Light Probe (builtin.LightProbe).  Some metadata is not yet included here.'
    header = ['event_timestamp', 'lux', 'accuracy']
    device_class = 'PurpleRobot'
    def convert(self, queryset, time=lambda x:x):
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.LightProbe':
                    for t, l, a in zip(probe['EVENT_TIMESTAMP'],
                                       probe['LUX'],
                                       probe['ACCURACY'],
                                       ):
                        yield time(t), l, a


class PRTimestamps(_Converter):
    desc = 'All actual data timestamps of all PR probes'
    header = ['time',
              'packet_time',
              'probe',]
    device_class = 'PurpleRobot'
    def convert(self, queryset, time=lambda x:x):
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                yield (time(probe['TIMESTAMP']),
                       time(timegm(ts.utctimetuple())),
                       probe['PROBE'].rsplit('.',1)[-1])
class PRRunningSoftware(_Converter):
    header = ['time', 'package_name', 'task_stack_index', 'package_category', ]
    desc = "All software currently running"
    device_class = 'PurpleRobot'
    def convert(self, queryset, time=lambda x:x):
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.RunningSoftwareProbe':
                    probe_ts = time(probe['TIMESTAMP'])
                    for software in probe['RUNNING_TASKS']:
                        yield (probe_ts,
                               software['PACKAGE_NAME'],
                               software['TASK_STACK_INDEX'],
                               software['PACKAGE_CATEGORY'],
                              )
class PRSoftwareInformation(_Converter):
    header = ['time',
              'package_name',
              'app_name',
              'package_version_name',
              'package_version_code',]
    desc = "All software installed"
    device_class = 'PurpleRobot'
    def convert(self, queryset, time=lambda x:x):
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.SoftwareInformationProbe':
                    probe_ts = time(probe['TIMESTAMP'])
                    for software in probe['INSTALLED_APPS']:
                        yield (probe_ts,
                               software['PACKAGE_NAME'],
                               software['APP_NAME'],
                               software.get('PACKAGE_VERSION_NAME'),
                               software['PACKAGE_VERSION_CODE'],
                              )
class PRCallHistoryFeature(_Converter):
    header = ['time', 'window_index',
              'window_size', 'total', 'new_count', 'min_duration',
              'max_duration', 'avg_duration', 'total_duration',
              'std_deviation', 'incoming_count', 'outgoing_count',
              'incoming_ratio', 'ack_ratio', 'ack_count', 'stranger_count',
              'acquiantance_count', 'acquaintance_ratio', ]
    desc = "Aggregated call info"
    device_class = 'PurpleRobot'
    def convert(self, queryset, time=lambda x:x):
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.features.CallHistoryFeature':
                    ts = time(probe['TIMESTAMP'])
                    for i, window in enumerate(probe['WINDOWS']):
                        yield (ts,
                               i,
                               window['WINDOW_SIZE'],
                               window['TOTAL'],
                               window['NEW_COUNT'],
                               window['MIN_DURATION'],
                               window['MAX_DURATION'],
                               window['AVG_DURATION'],
                               window['TOTAL_DURATION'],
                               window['STD_DEVIATION'],
                               window['INCOMING_COUNT'],
                               window['OUTGOING_COUNT'],
                               window['INCOMING_RATIO'],
                               window['ACK_RATIO'],
                               window['ACK_COUNT'],
                               window['STRANGER_COUNT'],
                               window['ACQUIANTANCE_COUNT'],
                               window['ACQUAINTANCE_RATIO'],
                              )
class PRSunriseSunsetFeature(_Converter):
    header = ['time', 'is_day', 'sunrise', 'sunset', 'day_duration']
    desc = "Sunrise and sunset info at current location"
    device_class = 'PurpleRobot'
    def convert(self, queryset, time=lambda x:x):
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.features.SunriseSunsetFeature':
                    yield (time(probe['TIMESTAMP']),
                           probe['IS_DAY'],
                           time(probe['SUNRISE']/1000.),
                           time(probe['SUNSET']/1000.),
                           probe['DAY_DURATION']/1000.,
                    )
class PRCommunicationEventProbe(_Converter):
    desc = 'Purple Robot Communication Event Probe'
    header = ['time',
              'communication_type',
              'communication_direction',
              'number',
              'duration']
    desc = "Communication Event Probe"
    device_class = 'PurpleRobot'
    no_number = False
    def convert(self, queryset, time=lambda x:x):
        no_number = self.no_number
        for ts, data in queryset:
            if 'CommunicationEventProbe' not in data:
                continue
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.CommunicationEventProbe':
                    duration = probe.get('DURATION', 0)
                    yield (time(probe['COMM_TIMESTAMP']/1000.),
                           probe['COMMUNICATION_DIRECTION'],
                           probe['COMMUNICATION_TYPE'],
                           '' if no_number else safe_hash(probe['NORMALIZED_HASH']),
                           duration,
                    )
class PRCommunicationEventProbeNoNumber(PRCommunicationEventProbe):
    no_number = True




class _PRGeneric(_Converter):
    """Generic simple probe

    This is an abstract base class for converting any probe into one row.

    Required attribute: 'field', which is tuples of (field_name,
    PROBE_FIELD).  The first is the output field name, the second is
    what is found in the probe object.  If length second is missing,
    use the first for both.
    """
    device_class = 'PurpleRobot'
    @classmethod
    def convert(self, queryset, time=lambda x:x):
        """Iterate through all data, extract the probes, take the probes we
        want, then yield timestamp+the requested fields.
        """
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == self.probe_name:
                    yield (time(probe['TIMESTAMP']), ) + \
                         tuple(probe[x[-1]] for x in self.fields)
class _PRGenericArray(_Converter):
    """Generic simple probe

    This is an abstract base class for converting any probe into one row.

    Required attribute: 'field', which is tuples of (field_name,
    PROBE_FIELD).  The first is the output field name, the second is
    what is found in the probe object.  If length second is missing,
    use the first for both.
    """
    device_class = 'PurpleRobot'
    @classmethod
    def header2(cls):
        """Return header, either dynamic or static."""
        if hasattr(cls, 'header') and cls.header:
            return cls.header
        return ['time', 'probe_time'] + [x[0].lower() for x in cls.fields] + [x[0].lower() for x in cls.fields_array]
    @classmethod
    def convert(self, queryset, time=lambda x:x):
        """Iterate through all data, extract the probes, take the probes we
        want, then yield timestamp+the requested fields.
        """
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['PROBE'] == self.probe_name:
                    row_common = tuple(probe[f[-1]] for f in self.fields)
                    for row in zip(probe[self.ts_field], *(probe[f[-1]] for f in self.fields_array )):
                        ts_event = row[0]
                        yield (time(ts_event),
                               time(probe['TIMESTAMP'])) \
                              + row_common \
                              + row[1:]


class PRAccelerometerBasicStatistics(_PRGeneric):
    probe_name = 'edu.northwestern.cbits.purple_robot_manager.probes.features.AccelerometerBasicStatisticsFeature'
    desc = "Purple Robot features.AccelerometerBasicStatisticsFeature"
    fields = [
        ('X_MIN', ),
        ('X_MEAN', ),
        ('X_MAX', ),
        ('X_STD_DEV', ),
        ('X_RMS', ),
        ('Y_MIN', ),
        ('Y_MEAN', ),
        ('Y_MAX', ),
        ('Y_STD_DEV', ),
        ('Y_RMS', ),
        ('Z_MIN', ),
        ('Z_MEAN', ),
        ('Z_MAX', ),
        ('Z_STD_DEV', ),
        ('Z_RMS', ),
        ('DURATION', ),
        ('BUFFER_SIZE', ),
        ('FREQUENCY', ),
        ]
class PRAccelerometerFrequency(_PRGeneric):
    probe_name = 'edu.northwestern.cbits.purple_robot_manager.probes.features.AccelerometerFrequencyFeature'
    desc = "Purple Robot features.AccelerometerFrequencyFeature"
    fields = [
        ('WINDOW_TIMESTAMP', ),
        ('POWER_X', ),
        ('FREQ_X', ),
        ('POWER_Y', ),
        ('FREQ_Y', ),
        ('POWER_Z', ),
        ('FREQ_Z', ),
        ]
class PRApplicationLaunches(_PRGeneric):
    probe_name = 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.ApplicationLaunchProbe'
    desc = "ApplicationLaunchProbe, when software is started"
    fields = [
        ('CURRENT_APP_PKG', ),
        ('CURRENT_APP_NAME', ),
        # These can always be found by looking at previous row, and
        # are missing in the first row.
        #('PREVIOUS_APP_PKG', ),
        #('PREVIOUS_APP_NAME', ),
        #('PREVIOUS_TIMESTAMP', ),
        ]
class PRAudioFeatures(_PRGeneric):
    probe_name = 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.AudioFeaturesProbe'
    desc = "Audio Features Probe - some signal information on audio"
    fields = [
        ('FREQUENCY', ),
        ('NORMALIZED_AVG_MAGNITUDE', ),
        ('POWER', ),
        ('SAMPLE_BUFFER_SIZE', ),
        ('SAMPLE_RATE', ),
        ('SAMPLES_RECORDED', ),
        ]
class PRCallState(_PRGeneric):
    probe_name = 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.CallStateProbe'
    desc = "Call state (idle/active)"
    fields = [
        ('CALL_STATE', ),
        ]
class PRTouchEvents(_PRGeneric):
    probe_name = 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.TouchEventsProbe'
    desc = "Touch events, number of"
    fields = [
        ('TOUCH_COUNT', ),
        ('LAST_TOUCH_DELAY', ),
        ]
class PRProximity(_PRGenericArray):
    probe_name = 'edu.northwestern.cbits.purple_robot_manager.probes.builtin.ProximityProbe'
    desc = "Proximity probe"
    ts_field = 'EVENT_TIMESTAMP'
    fields = [ ]
    fields_array = [('ACCURACY',),
                    ('DISTANCE',), ]


class PRDataSize(_Converter):
    device_class = 'PurpleRobot'
    per_page = None
    header = ['probe', 'count', 'bytes', 'human_bytes', 'bytes/day']
    desc = "Total bytes taken by each separate probe (warning: takes a long time to compute)"
    days_ago = None
    @classmethod
    def query(cls, queryset):
        """"Limit to the number of days ago, if cls.days_ago is given."""
        if not cls.days_ago:
            return queryset
        from django.utils import timezone
        now = timezone.now()
        return queryset.filter(ts__gt=now-timedelta(days=cls.days_ago))
    def convert(self, queryset, time=lambda x:x):
        if self.days_ago is not None:
            start_time = mod_time.time() - self.days_ago * (24*3600)
            total_days = self.days_ago
        else:
            start_time = 0
            total_days = None
        sizes = collections.defaultdict(int)
        counts = collections.defaultdict(int)
        for ts, data in queryset:
            data = loads(data)
            for probe in data:
                if probe['TIMESTAMP'] < start_time:
                    # TODO: some probes may have wrong timestamps
                    # (like StepCounterProbe) which makes this
                    # comparison wrong.
                    continue
                if total_days is None:
                    # Figure out the total days.  If we are in django,
                    # this is an aware datetime.  Otherwise, it is
                    # _probably_ a naive one, which we assume to be
                    # UTC.  This hackish stuff also allows us to not
                    # depend on django.  TODO: improve this.
                    try:
                        total_days = (datetime.utcfromtimestamp(mod_time.time())-ts).total_seconds() / (3600*24)
                    except TypeError:
                        from django.utils import timezone
                        now = timezone.now()
                        total_days = (now-ts).total_seconds() / (3600*24)
                # Actual body:
                sizes[probe['PROBE']] += len(dumps(probe))
                counts[probe['PROBE']] += 1
        for probe, size in sorted(iteritems(sizes), key=lambda x: x[1], reverse=True):
            yield (probe,
                   counts[probe],
                   size,
                   human_bytes(size),
                   human_bytes(size/float(total_days)))
        yield ('total',
               sum(itervalues(counts)),
               sum(itervalues(sizes)),
               human_bytes(sum(itervalues(sizes))),
               human_bytes(sum(itervalues(sizes))/float(total_days)))
class PRDataSize1Day(PRDataSize):
    desc = "Like PRDataSize, but limited to 1 day.  Use this for most testing."
    days_ago = 1
class PRDataSize1Week(PRDataSize):
    desc = "Like PRDataSize, but limited to 7 days.  Also more efficient."
    days_ago = 7
class PRDataSize1Hour(PRDataSize):
    desc = "Like PRDataSize, but limited to 7 days.  Also more efficient."
    days_ago = 1/24.

class PRMissingData(_Converter):
    """Report time periods of greater than 3600s when no data was recorded.

    This uses the PRTimestamps converter to the timestamps of actual
    data collection, not just when data was uploaded which is expected
    to be intermitent.  This is used for testing Purple Robot
    functioning.
    """
    device_class = 'PurpleRobot'
    per_page = None
    header = ['gap_start', 'gap_end', 'gap_s', 'previous_duration_s']
    desc = "Report gaps of greater than 3600s in last 28 days of Purple Robot data."
    days_ago = 28
    min_gap = 3600
    @classmethod
    def query(cls, queryset):
        """Do necessary filtering on the django QuerySet.

        In this case, restrict to the last 14 days."""
        #now = datetime.utcnow() This method depends on django, but
        # that is OK since it used Queryset semantics, which itself
        # depend on django.  This method only makes sent to call in
        # the server itself.
        from django.utils import timezone
        now = timezone.now()
        return queryset.filter(ts__gt=now-timedelta(days=cls.days_ago))
    def __init__(self, *args, **kwargs):
        super(PRMissingData, self).__init__(*args, **kwargs)
        self.ts_list = [ ]
    def convert(self, rows, time=lambda x:x):
        ts_list = self.ts_list
        # Get list of all actual data timestamps (using PRTimestamps converter).
        #
        # Run through all data.  By the way that "extend" works, if
        # there is an error in decoding, the previously appended items
        # will still be tehre.  So, when we restart (from the .run()
        # method that restarts on exceptions), we continue appending
        # to the same list, which is good.
        self.ts_list.extend(x[0] for x in PRTimestamps(rows).run())
        # Avoid all timestamps less than 1e8s (1973).  This avoids
        # times converted from things that weren't unixtimes.
        ts_list_sorted = sorted(t for t in ts_list if t > 100000000)
        ts_list_sorted.append(mod_time.time())
        ts_list_sorted = iter(ts_list_sorted)
        # Simple core: go through, convert all data, any gaps that are
        # greater than self.min_gap seconds, yield that info.
        t_before_gap = next(ts_list_sorted)
        t_active_start = t_before_gap
        for t_next in ts_list_sorted:
            if t_next > t_before_gap + self.min_gap:
                yield (time(t_before_gap),
                       time(t_next),
                       t_next-t_before_gap,
                       t_before_gap-t_active_start if t_active_start else '',
                )
                t_active_start = t_next
            t_before_gap = t_next
        yield (time(t_before_gap),
               time(t_next),
               t_next-t_before_gap,
               t_before_gap-t_active_start if t_active_start else '',
        )
        del self.ts_list
        del ts_list
class PRMissingData7Days(PRMissingData):
    days_ago = 7
    desc = "Report gaps of greater than 3600s in last 7 days of Purple Robot data."



class IosLocation(_Converter):
    header = ['time', 'lat', 'lon', 'alt', 'speed']
    desc = "Location data"
    per_page = 1
    device_class = 'Ios'
    def convert(self, queryset, time=lambda x:x):
        for ts, data in queryset:
            data = loads(data)
            for row in data:
                try:
                    yield (time(row['timestamp']),
                       float(row['lat']),
                       float(row['lon']),
                       float(row['alt']),
                       float(row['speed']),
                       )
                except:
                    pass





if __name__ == "__main__":
    import argparse
    description = """\
    Command line utility for converting raw data into other forms.

    This converts raw data using the converters defined in this file.
    It is a simple command line version of views_data.py:device_data.
    In the future, the common ground of these two functions should be
    merged.

    So far, the input format must be 'json-lines', that is, one JSON
    object on each line.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help="Input filename")
    parser.add_argument('converter', help="Output filename")
    parser.add_argument('-f', '--format', help="Output format [csv,json,py]",
                        default='csv')
    parser.add_argument('-o', '--output', help="Output filename",
                        default=None)
    parser.add_argument('--handle-errors', help="Catch errors and continue",
                        action='store_true', default=False)
    parser.add_argument('--suppress-errors', help="If there were errorrs, do not print "
                                        "anything about them.  Has no effect unless "
                                        "--handle-errors is given.",
                        action='store_true', default=False)
    args = parser.parse_args()

    converter = globals()[args.converter]

    # Open the input file.  We expect it to have one JSON object per
    # line (as separated by \n).  Then, we make an iterator that JSON
    # decodes each line, and give this iterater to the converter.  The
    # converter returns another iterator over the reprocessed data.
    f = open(args.input)
    row_iter = (loads(line) for line in f )
    # Reprocess the row to convert the unixtime to UTC datetime
    row_iter = ((datetime.utcfromtimestamp(ts), data) for (ts, data) in row_iter)
    # First method is new conversion that handles errors
    # semi-intelligently.
    if args.handle_errors:
        converter = converter(row_iter)
        table = converter.run()
    # Second does not handle errors, if an error happens exception is
    # propagated.
    else:
        table = converter().convert(row_iter)  # iterate through lines
    # Output filename
    if args.output is not None:
        f_output = open(args.output, 'w')
    else:
        f_output = sys.stdout

    # Write as python objects (repr)
    if args.format == 'py':
        for row in table:
            print(repr(row), file=f_output)

    # Write as CSV
    elif args.format == 'csv':
        # We have to be a bit convoluted to support both python2 and
        # python3 here.  Maybe there is a better way to do this...
        csv_writer = csv.writer(f_output)
        csv_writer.writerow([x.encode('utf-8') for x in converter.header2()])
        for row in table:
            #csv_writer.writerow(row)
            csv_writer.writerow([x.encode('utf-8') if isinstance(x, string_types) else x
                                 for x in row])

    # Write as JSON
    elif args.format == 'json':
        print('[', file=f_output)
        table = iter(table)
        print(dumps(next(table)), end='', file=f_output)
        for row in table:
            print(',', file=f_output) # makes newline
            print(dumps(row), end='', file=f_output)
        print('\n]', file=f_output)

    else:
        print("Unknown output format: %s"%args.format)
        exit(1)

    # If there were any errors, make a warning about them.
    if args.handle_errors and not args.suppress_errors:
        if converter.errors:
            print("")
            print("The following errors were found:")
            for error in converter.errors:
                print(error)
