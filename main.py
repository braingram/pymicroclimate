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


class BME280(TimedSensor):
    def __init__(self, interval):
        super().__init__(interval)

        # no filter, as default

        # no humidity oversampling
        microbit.i2c.write(0x77, b'\xF2\x00')  # no humidity oversampling

        # no temp/pres oversampling, forced mode
        microbit.i2c.write(0x77, b'\xF4\x01')

        # read in calibration/compensation values
        t1 = struct.unpack('<H', i2c_read(0x77, 0x88, 2))[0]
        t2 = struct.unpack('<h', i2c_read(0x77, 0x8A, 2))[0]
        t3 = struct.unpack('<h', i2c_read(0x77, 0x8C, 2))[0]

        def comp_temp(self, v):
            """
            BME280_S32_t BME280_compensate_T_int32(BME280_S32_t adc_T)
            {
            BME280_S32_t var1, var2, T;
            var1 = ((((adc_T>>3) – ((BME280_S32_t)dig_T1<<1))) * ((BME280_S32_t)dig_T2)) >> 11;
            var2 = (((((adc_T>>4) – ((BME280_S32_t)dig_T1)) * ((adc_T>>4) – ((BME280_S32_t)dig_T1)))
            >> 12) *
            ((BME280_S32_t)dig_T3)) >> 14;
            t_fine = var1 + var2;
            T = (t_fine * 5 + 128) >> 8;
            return T;
            }
            """
            v1 = (((v >> 3) - (t1 << 1)) * t2) >> 11
            v2 = (((((v >> 4) - t1) * ((v >> 4) - t1)) >> 12) * t3) >> 14
            self._t_fine = v1 + v2
            return ((self.t_fine * 5 + 128) >> 8) / 100.0

        self._comp_temp = comp_temp

        p1 = struct.unpack('<H', i2c_read(0x77, 0x8E, 2))[0]
        p2 = struct.unpack('<h', i2c_read(0x77, 0x90, 2))[0]
        p3 = struct.unpack('<h', i2c_read(0x77, 0x92, 2))[0]
        p4 = struct.unpack('<h', i2c_read(0x77, 0x94, 2))[0]
        p5 = struct.unpack('<h', i2c_read(0x77, 0x96, 2))[0]
        p6 = struct.unpack('<h', i2c_read(0x77, 0x98, 2))[0]
        p7 = struct.unpack('<h', i2c_read(0x77, 0x9A, 2))[0]
        p8 = struct.unpack('<h', i2c_read(0x77, 0x9C, 2))[0]
        p9 = struct.unpack('<h', i2c_read(0x77, 0x9E, 2))[0]

        def comp_pres(self, v):
            """
            BME280_U32_t BME280_compensate_P_int64(BME280_S32_t adc_P)
            {
            BME280_S64_t var1, var2, p;
            var1 = ((BME280_S64_t)t_fine) – 128000;
            var2 = var1 * var1 * (BME280_S64_t)dig_P6;
            var2 = var2 + ((var1*(BME280_S64_t)dig_P5)<<17);
            var2 = var2 + (((BME280_S64_t)dig_P4)<<35);
            var1 = ((var1 * var1 * (BME280_S64_t)dig_P3)>>8) + ((var1 * (BME280_S64_t)dig_P2)<<12);
            var1 = (((((BME280_S64_t)1)<<47)+var1))*((BME280_S64_t)dig_P1)>>33;
            if (var1 == 0)
            {
            return 0; // avoid exception caused by division by zero
            }
            p = 1048576-adc_P;
            p = (((p<<31)-var2)*3125)/var1;
            var1 = (((BME280_S64_t)dig_P9) * (p>>13) * (p>>13)) >> 25;
            var2 = (((BME280_S64_t)dig_P8) * p) >> 19;
            p = ((p + var1 + var2) >> 8) + (((BME280_S64_t)dig_P7)<<4);
            return (BME280_U32_t)p;
            }
            """
            v1 = self._t_fine - 128000
            v2 = (
                v1 * v1 * p6
                + ((v1 * p5) << 17)
                + (p4 << 35))
            v1 = ((v1 * v1 * p3) >> 8) + ((v1 * p2) << 12)
            v1 = (((a << 47) + v1) * p1) >> 33
            if v1 == 0:
                return 0
            p = 1048576 - v
            p = (((p << 31) - v2) * 3125) / v1
            v1 = (p9 * (p >> 13) * (p >> 13)) >> 25
            v2 = (p8 * p) >> 19
            p = ((p + v1 + v2) >> 8) + (p7 << 4)
            return p / 256.

        self._comp_pres = comp_pres

        h1 = i2c_read(0x77, 0xA1)[0]
        h2 = struct.unpack('<h', i2c_read(0x77, 0xE1, 2))[0]
        h3 = i2c_read(0x77, 0xE3)[0]
        bs = i2c_read(0x77, 0xE4, 3)
        h4 = (bs[0] << 4) | (bs[1] & 0xF)
        h5 = (bs[1] >> 4) | (bs[2] << 4)

        def comp_humidity(self, v):
            """
            BME280_U32_t bme280_compensate_H_int32(BME280_S32_t adc_H)
            {
            BME280_S32_t v_x1_u32r;
            v_x1_u32r = (t_fine – ((BME280_S32_t)76800));
            v_x1_u32r = (((((adc_H << 14) – (((BME280_S32_t)dig_H4) << 20) – (((BME280_S32_t)dig_H5) *
            v_x1_u32r)) + ((BME280_S32_t)16384)) >> 15) * (((((((v_x1_u32r *
            ((BME280_S32_t)dig_H6)) >> 10) * (((v_x1_u32r * ((BME280_S32_t)dig_H3)) >> 11) +
            ((BME280_S32_t)32768))) >> 10) + ((BME280_S32_t)2097152)) * ((BME280_S32_t)dig_H2) +
            8192) >> 14));
            v_x1_u32r = (v_x1_u32r – (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) *
            ((BME280_S32_t)dig_H1)) >> 4));
            v_x1_u32r = (v_x1_u32r < 0 ? 0 : v_x1_u32r);
            v_x1_u32r = (v_x1_u32r > 419430400 ? 419430400 : v_x1_u32r);
            return (BME280_U32_t)(v_x1_u32r>>12);
            }
            """
            v1 = self._t_fine - 76800
            v1 = (
                ((((v << 14) - (h4 << 20) - (h5 * v1)) + 16384) >> 15) *
                (((((((v1 * h6) >> 10) * (((v1 * h3) >> 11) + 32768)) >> 10) + 2097152) * h2 + 8192) >> 14)
            )
            v1 = (v1 - (((((v1 >> 15) * (v1 >> 15)) >> 7) * h1) >> 4))
            if v1 < 0:
                v1 = 0
            v_x1_u32r = (v_x1_u32r > 419430400 ? 419430400 : v_x1_u32r);
            if v1 > 419430400:
                v1 = 419430400
            return (v1 >> 12) / 1024.

        self._comp_humidity = comp_humidity

        # modes
        # 0: waiting for trigger
        # 1: triggered
        self.reading = False

    def update(self, t):
        super(BME280, self).update(self, t)
        if self.reading:  # check if sampling is done
            status = i2c_read(0x77, 0xF3)[0]
            if (status ^ 0b1000) & 0b1000:
                # sample is ready, report
                self.report(t)

    def parse_temperature(self, bs):
        return self._comp_temp((bs[3] << 12) | (bs[4] << 4) | (bs[5] >> 4))

    def parse_pressure(self, bs):
        return self._comp_pres((bs[0] << 12) | (bs[1] << 4) | (bs[2] >> 4))

    def parse_humidity(self, bs):
        return self._comp_humidity((bs[6] << 8) | bs[7])

    def report(self, t):
        if self.reading:
            # read bytes
            bs = i2c_read(0x77, 0xF7, 8)

            # convert
            print("wbt,%i,%0.2f" % (t, self.parse_temperature(bs)))
            print("wbp,%i,%0.2f" % (t, self.parse_pressure(bs)))
            print("wbh,%i,%0.2f" % (t, self.parse_humidity(bs)))

            self.reading = False
        else:
            # request reading
            # no temp/pres oversampling, forced mode
            microbit.i2c.write(0x77, b'\xF4\x01')
            self.reading = True


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
        # ALS_GAIN = 2 (set gain (do this after power on?))
        # reg: 0x00, 0b00000001, 0b00010010
        microbit.i2c.write(0x48, b'\x00\x01\x18')

        # for reading
        # ALS_SD = 0 (trigger sample)
        # how to know when done? (ALS_SD == 1)
        self.reading = False

    def update(self, t):
        super(BME280, self).update(self, t)
        if self.reading:  # check if sampling is done
            if i2c_read(0x48, 0x00, 2)[0] & 0b1:  # sample ready
                self.report(t)

    def report(self, t):
        if self.reading:
            v = struct.unpack('>h', i2c_read(0x48, 0x04, 2))[0]
            # TODO compensate for non-linearity
            print("l,%i,%0.4f" % (t, v * 0.9216))

            self.reading = False
        else:
            # request reading
            microbit.i2c.write(0x48, b'\x00\x01\x18')
            self.reading = True


class MS8607(TimedSensor):
    # TODO
    pass


class Accel(TimedSensor):
    def __init__(self, interval):
        super().__init__(interval)
        # set data rate, enable xyz
        microbit.i2c.write(0x19, b'\x20\x17')
        # int1 latching int2 latching
        microbit.i2c.write(0x19, b'\x24\x0A')
        # bdu (block data update) to true
        microbit.i2c.write(0x19, b'\x23\x80')

    def report(self, t):
        # read x,y,z
        x = (
            (i2c_read(0x19, b'\x28')[0] >> 4) +
            (i2c_read(0x19, b'\x29')[0] << 4))
        y = (
            (i2c_read(0x19, b'\x2A')[0] >> 4) +
            (i2c_read(0x19, b'\x2B')[0] << 4))
        z = (
            (i2c_read(0x19, b'\x2C')[0] >> 4) +
            (i2c_read(0x19, b'\x2D')[0] << 4))
        print("ax,%i,%i" % (t, x))
        print("ay,%i,%i" % (t, y))
        print("az,%i,%i" % (t, z))


class WindSpeed(TimedSensor):
    def __init__(self, interval, pin):
        super().__init__(interval)
        self.state = 1
        self.count = 0
        self.pin = pin
        # self.pin.set_pull?
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
    (270, '112.5'),
    (294, '67.5'),
    (305, '90'),
    (347, '157.5'),
    (414, '135'),
    (479, '202.5'),
    (522, '180'),
    (631, '22.5'),
    (677, '45'),
    (780, '247.5'),
    (801, '225'),
    (849, '337.5'),
    (899, '0'),
    (922, '292.5'),
    (955, '315'),
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
        print('wd,%i,%0.1f' % (t, wd))


class Rain(WindSpeed):
    def report(self, t):
        print('r,%i,%0.4f' % (t, 0.2794 * self.count))


interval = 1000
i2c_sensor_addrs = {
    #0x48: VEML6030,
    #0x76: MS8607,
    0x77: BME280,
}

microbit.i2c.init()
sensors = [
    MBTemp(interval),
    #Accel(interval),
    WindSpeed(interval, microbit.pin8),
    WindDir(interval),
    Rain(interval, microbit.pin2),
]

# scan i2c bus, add only available sensors
for addr in microbit.i2c.scan():
    if addr in i2c_sensor_addrs:
        sensors.append(sensor_addrs[addr](interval))

while True:
    t_ms = microbit.running_time()
    [s.update(t_ms) for s in sensors]
