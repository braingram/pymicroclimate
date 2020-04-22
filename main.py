import struct

import microbit


adc_to_dir = [(372, '112.5'),(390, '67.5'),(399, '90'),(430, '157.5'),(483, '135'),(534, '202.5'),(569, '180'),(661, '22.5'),(700, '45'),(792, '247.5'),(811, '225'),(855, '337.5'),(902, '0'),(925, '292.5'),(956, '315'),(985, '270'),]


def winddir():
    v = microbit.pin1.read_analog()
    # lookup closest wind direction in adc_to_dir
    lcv, lwd = None, None
    for cv, wd in adc_to_dir:
        if cv > v:
            if lcv is None:
                return wd
            else:  # v is between lcv and cv
                if cv - v > v - lcv:
                    return lwd
                else:
                    return wd
        lcv, lwd = cv, wd
    return lwd


class PinCounter:
    def __init__(self, pin):
        self.count = 0
        self.state = 1
        pin.set_pull(pin.PULL_UP)
        self.pin = pin

    def update(self):
        if self.state:
            if self.pin.read_digital() == 0:
                self.state = 0
                self.count += 1
        else:
            if self.pin.read_digital() == 1:
                self.state = 1

    def get_count(self):
        c = self.count
        self.count = 0
        return c


def i2c_read(addr, reg, nbytes=1):
    microbit.i2c.write(addr, reg, True)
    return microbit.i2c.read(addr, nbytes)


class BME280():
    def __init__(self, interval):

        # no filter, as default

        # no humidity oversampling
        microbit.i2c.write(0x76, b'\xF2\x00')  # no humidity oversampling

        # no temp/pres oversampling, forced mode
        microbit.i2c.write(0x76, b'\xF4\x01')

        # modes
        # 0: waiting for trigger
        # 1: triggered
        self.reading = False

    def update(self, t):
        super().update(t)
        if self.reading:  # check if sampling is done
            status = i2c_read(0x76, b'\xF3')[0]
            if (status ^ 0b1000) & 0b1000:
                # sample is ready, report
                self.report(t)

    def parse_temperature(self, bs):
        return ((bs[3] << 12) | (bs[4] << 4) | (bs[5] >> 4))

    def parse_pressure(self, bs):
        return ((bs[0] << 12) | (bs[1] << 4) | (bs[2] >> 4))

    def parse_humidity(self, bs):
        return ((bs[6] << 8) | bs[7])

    def report(self, t):
        if self.reading:
            # read bytes
            bs = i2c_read(0x76, b'\xF7', 8)

            # convert
            print("wbt,%i,%0.2f" % (t, self.parse_temperature(bs)))
            print("wbp,%i,%0.2f" % (t, self.parse_pressure(bs)))
            print("wbh,%i,%0.2f" % (t, self.parse_humidity(bs)))

            self.reading = False
        else:
            # request reading
            # no temp/pres oversampling, forced mode
            microbit.i2c.write(0x76, b'\xF4\x01')
            self.reading = True



interval = 1000

microbit.i2c.init()

microbit.i2c.write(0x48, b'\x03\x07\x00')  # VEML6030
microbit.i2c.write(0x48, b'\x00\x00\x18')
#microbit.i2c.write(0x76, b'\xF2\x00')  # BME280
#microbit.i2c.write(0x76, b'\xF2\x01')
# MS8607
windspeed = PinCounter(microbit.pin8)
wind_speed_scale = 2.4 / (interval / 1000.)
rain = PinCounter(microbit.pin2)


def report():
    print("mbtemp,%0.2f" % microbit.temperature())
    print("windspeed,%0.4f" % (windspeed.get_count() * wind_speed_scale))
    print("winddir,%s" % winddir())
    print("rain,%0.4f" % (rain.get_count() * 0.2794))
    # TODO verify scalar
    print("light,%0.4f" % (struct.unpack('<H', i2c_read(0x48, b'\x04', 2))[0] * 0.9216))
    #microbit.i2c.write(0x76, b'\xF4\x01')
    #while (i2c_read(0x76, b'\xF3')[0] ^ 0b1000) & 0b1000 == 0:  # takes 3-4 ms
    #    pass
    #bs = i2c_read(0x76, b'\xF7', 8)
    ## TODO needs compensation from calibration values
    #print("wbt,%0.2f" % ((bs[3] << 12) | (bs[4] << 4) | (bs[5] >> 4)))
    #print("wbp,%0.2f" % ((bs[0] << 12) | (bs[1] << 4) | (bs[2] >> 4)))
    #print("wbh,%0.2f" % ((bs[6] << 8) | bs[7]))



def update():
    windspeed.update()
    rain.update()


t0 = microbit.running_time()
while True:
    t = microbit.running_time()
    if (t - t0) >= interval:
        print("time,%i" % t)
        report()
        t0 = t
    else:
        update()
