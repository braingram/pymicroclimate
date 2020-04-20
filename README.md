Using micropython
Transferred using [MicroFS](https://microfs.readthedocs.io/en/latest/)


Sensors
------

Microbit Sensors:
- Temperature: microbit.temperature()  # C
- Radio: (for talking to other micirobits)

Weatherbit Sensors:
- Temp/Humidity/Pressure, BME280: i2c, 0x77
- Wind (WDIR:P1, WSPEED:P8)
- Rain (P2)
- Serial logger (TX:P15, RX:P14)
- Temp, DS18B20: (P12, P13)

Extra Sensors:
- Temp/Humidity/Pressure, MS8607: i2c, 0x76 & 0x40
- Light Sensor, VEML6030: i2c, 0x48


Weatherbit Temp/Humidity/Pressure: BME280
------
i2c, 0x77
Recommended weather monitoring:
    Forced mode, 1 sample/minute
    1x oversampling, no filter
Set config:
    0xF5 0bXXX000X0
Set ctrl_hum 16x oversampling:
    0xF2 0bXXXXX000

For each sample

Set ctrl_meas 16x temp/press oversampling, normal mode:
    0xF4 0b00000010
Wait for status done
    0xF3 0bXXXX1XX0  # measuring
    0xF3 0bXXXX0XX0  # done measuring


Wind
------
Speed: P8 GPIO
1 low(? needs pullup?) per second = 2.4 km/h

Direction: P1 (ADC)
Angle = Resistance (see datasheet)
Has 4.7k pullup (to 3.3v) and 2k in series (1k to pin, 1k to ground)


Rain
------
GPIO: P2
every low (needs internal pullup?) = 0.2794 mm of rain


Weatherbit Temp: DS18B20
------
(P12, P13)?


HW hookup
------

i2c pullups:
- microbit: 4.7k
- MS8607: 2.2k
- VEML6030: 4.7k
- total: 1.13k, through 3.3V yields 3 mA
