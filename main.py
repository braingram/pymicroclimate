#6K

import struct

import microbit


def i2c_read(addr, reg, nbytes=1):
    microbit.i2c.write(addr, reg, True)
    return microbit.i2c.read(addr, nbytes)


class TimedSensor:
    def __init__(self, interval):
        self.dt = interval
        self.lt = microbit.running_time()

    def update(self, t):
        if t - self.lt >= interval:
            self.report(t)
            self.lt = t

    def report(self, t):
        pass


class MBTemp(TimedSensor):
    def report(self, t):
        print("mbt,%i,%0.2f" % (t, microbit.temperature()))


class WindSpeed(TimedSensor):
    def __init__(self, interval, pin):
        super().__init__(interval)
        self.state = 1
        self.count = 0
        self.pin = pin
        self.pin.set_pull(pin.PULL_UP)
        self.last_report = microbit.running_time()

    def update(self, t):
        if self.state:  # pin was high
            if self.pin.read_digital() == 0:
                # pin went low
                self.count += 1
                self.state = 0
        else:  # pin was low
            if self.pin.read_digital():
                # pin went high
                self.state = 1
        super().update(t)

    def report(self, t):
        dt = t - self.last_report
        # 1 low per seoncd = 2.4 km/h
        ws = 2.4 * self.count / dt
        print('ws,%i,%0.4f' % (t, ws))
        self.last_report = t
        self.count = 0


adc_to_dir = [
    (372, '112.5'),
    (390, '67.5'),
    (399, '90'),
    (430, '157.5'),
    (483, '135'),
    (534, '202.5'),
    (569, '180'),
    (661, '22.5'),
    (700, '45'),
    (792, '247.5'),
    (811, '225'),
    (855, '337.5'),
    (902, '0'),
    (925, '292.5'),
    (956, '315'),
    (985, '270'),
]


class WindDir(TimedSensor):
    def report(self, t):
        v = microbit.pin1.read_analog()
        # lookup closest wind direction in adc_to_dir
        lcv, lwd = None, None
        for cv, wd in adc_to_dir:
            if cv > v:
                if lcv is None:
                    wd = wd
                    break
                else:  # v is between lcv and cv
                    if cv - v > v - lcv:
                        wd = lwd
                        break
                    else:
                        # wd = wd
                        break
            lcv, lwd = cv, wd
        print('wd,%i,%s' % (t, wd))


class Rain(WindSpeed):
    def report(self, t):
        print('r,%i,%0.4f' % (t, 0.2794 * self.count))


class VEML6030(TimedSensor):
    def __init__(self, interval):
        super().__init__(interval)
        # reg, data_lsb, data_msb

        # 50 ms integration time, 1/8 gain, (~60k lux max) 0.9216 lux/unit
        #microbit.i2c.write(0x48, b'')
        # for lux > 1000 need correction factor (chart looks more like 10000)
        # y = 6.0135E-13x4 - 9.3924E-09x3 + 8.1488E-05x2 + 1.0023E+00x

        # PSM = 3 (slowest integration time, lowest power consumption)
        # PSM_EN = 1 (enable power savings mode)
        # reg: 0x03 0b111 0b0
        microbit.i2c.write(0x48, b'\x03\x07\x00')

        # ALS_SD = 0 (power on) (then wait 2.5 ms)
        # ALS_IT = 8 (set integration time)
        # ALS_PERSIST = 
        # ALS_GAIN = 2 (set gain (do this after power on?))
        # reg: 0x00, 0b00000001, 0b00010010
        microbit.i2c.write(0x48, b'\x00\x00\x18')

        # for reading
        # ALS_SD = 0 (trigger sample)
        # how to know when done? (ALS_SD == 1)
        #self.reading = False

    #def update(self, t):
    #    super().update(t)
    #    if self.reading:  # check if sampling is done
    #        if i2c_read(0x48, b'\x00', 2)[0] & 0b1:  # sample ready
    #            self.report(t)

    def report(self, t):
        v = struct.unpack('<H', i2c_read(0x48, b'\x04', 2))[0]
        # TODO compensate for non-linearity
        print("l,%i,%0.4f" % (t, v * 0.9216))
        #if self.reading:
        #    v = struct.unpack('<H', i2c_read(0x48, b'\x04', 2))[0]
        #    # TODO compensate for non-linearity
        #    print("l,%i,%0.4f" % (t, v * 0.9216))
        #    self.reading = False
        #else:
        #    # request reading
        #    #microbit.i2c.write(0x48, b'\x00\x01\x18')
        #    microbit.i2c.write(0x48, b'\x00\x00\x18')
        #    self.reading = True


interval = 1000
#i2c_sensor_addrs = {
#    #0x48: VEML6030,
#    #0x76: MS8607,
#    #0x77: BME280,
#}

microbit.i2c.init()
sensors = (
    MBTemp(interval),
    #Accel(interval),
    WindSpeed(interval, microbit.pin8),
    WindDir(interval),
    Rain(interval, microbit.pin2),  # 192 bytes
    VEML6030(interval),
)

# scan i2c bus, add only available sensors
#for addr in microbit.i2c.scan():
#    if addr in i2c_sensor_addrs:
#        sensors.append(sensor_addrs[addr](interval))

while True:
    t_ms = microbit.running_time()
    for s in sensors:
        s.update(t_ms)
