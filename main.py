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


interval = 1000
i2c_sensor_addrs = {
    #0x48: VEML6030,
    #0x76: MS8607,
    #0x77: BME280,
}

microbit.i2c.init()
sensors = [
    MBTemp(interval),
    #Accel(interval),
    WindSpeed(interval, microbit.pin8),
    WindDir(interval),
    #Rain(interval, microbit.pin2),
]

# scan i2c bus, add only available sensors
for addr in microbit.i2c.scan():
    if addr in i2c_sensor_addrs:
        sensors.append(sensor_addrs[addr](interval))

while True:
    t_ms = microbit.running_time()
    [s.update(t_ms) for s in sensors]
