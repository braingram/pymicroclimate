#include <elapsedMillis.h>
#include <Wire.h>

// TODO serial logger

//#define DEBUG

// interal temperature/humidity/pressure sensor
#define BME280

// light sensor
#define VEML6030

// weather (rain and wind) sensors
#define WEATHER

// one-wire temperature sensor
#define DS18B20

// use bluetooth serial
#define BLE


/* ------------------------------- */

#ifdef DEBUG
#define DBG(txt) Serial.println(txt);
#else
#define DBG(txt);
#endif

#ifdef BME280
// requires installing BMx280MI library
#include <BMx280I2C.h>
BMx280I2C bme280(0x76);
#define BME280_POLL_MASK 0x01
#endif

#ifdef VEML6030
// requires installing SparkFun Ambient Light Sensor Arduino Library
#include "SparkFun_VEML6030_Ambient_Light_Sensor.h"
SparkFun_Ambient_Light light(0x48);
#endif

#ifdef WEATHER
#define WDIRPIN 1
#define WSPDPIN 8
#define RAINPIN 2
int wdir_vals[] = {
  381,  395, 415, 457,  509,  552,  615,  681, 746, 802,  833,  879,  914, 941,  971,  1024};
int wdir_dirs[] = {
  1125, 675, 900, 1575, 1350, 2025, 1800, 225, 450, 2475, 2250, 3375, 0,   2925, 3150, 2700};
int n_wdir = sizeof(wdir_vals) / sizeof(int);

float wdir_val_to_dir(int val) {
  for (int i=0; i<n_wdir; i++) {
    if (wdir_vals[i] > val) {
      return ((float)wdir_dirs[i]) / 10.;
    };
  };
  return ((float)wdir_dirs[n_wdir-1]) / 10.;
};


class PinCounter {
  public:
    PinCounter(int pin_number);
    void update();
    int get_and_reset_count();
    volatile int count;
  private:
    int pin;
    int state;
};

PinCounter::PinCounter(int pin_number) {
  pinMode(pin_number, INPUT_PULLUP);
  pin = pin_number;
  count = 0;
  state = true;
};

void PinCounter::update() {
   if (state) {
    if (!digitalRead(pin)) {
      state = false;
      count += 1;
    };
  } else {
    if (digitalRead(pin)) {
      state = true;
    };
  };
};

int PinCounter::get_and_reset_count() {
  int c = count;
  count = 0;
  return c;
};

PinCounter wspd(WSPDPIN);
PinCounter rain(RAINPIN);


void wspd_isr() {
  wspd.count += 1;
};

void rain_isr() {
  rain.count += 1;
};

#endif

#ifdef DS18B20
// requires installing OneWire and DallasTemperature
#include <OneWire.h>
#include <DallasTemperature.h>
#define DS18B20PIN 12
// conversion time is set by resolution, make sure they are correct
#define DS18B20RES 12
#define DS18B20CONVT 750
OneWire oneWire(DS18B20PIN);
DallasTemperature dts(&oneWire);
elapsedMillis dts_timer;
#define DS18B20_POLL_MASK 0x02
#endif

#ifdef BLE
#include <Adafruit_Microbit.h>
Adafruit_Microbit microbit;
#endif

// -------------------------------------------------------


elapsedMillis poll_timer;
#define POLL_INTERVAL 2000
byte poll_state = 0;
unsigned long record_count = 0;
#define REPORT_AFTER_N_DATA 5

elapsedMillis header_timer;
#define HEADER_INTERVAL 60000

#ifdef WEATHER
float wspd_scale = 2.4 / (POLL_INTERVAL / 1000.);
#endif


void setup (){
  Serial.begin(115200);
  Serial.println("#Weather station booting...");
  Wire.begin();
#ifdef BME280
  Serial.print("#Adding BME280...");
  bme280.begin();
  bme280.resetToDefaults();
  bme280.writeOversamplingPressure(BMx280MI::OSRS_P_x01);
  bme280.writeOversamplingTemperature(BMx280MI::OSRS_T_x01);
  bme280.writeOversamplingHumidity(BMx280MI::OSRS_H_x01);
  bme280.writeFilterSetting(BMx280MI::FILTER_OFF);
  Serial.println("ok!");
#endif
#ifdef VEML6030
  Serial.print("#Adding VEML6030...");
  light.begin();
  light.setGain(0.125);
  light.setIntegTime(50); 
  Serial.println("ok!");
#endif
#ifdef WEATHER
  Serial.println("#Adding wind and rain sensors...ok!");
  attachInterrupt(digitalPinToInterrupt(RAINPIN), rain_isr, FALLING);
  attachInterrupt(digitalPinToInterrupt(WSPDPIN), wspd_isr, FALLING);
#endif
#ifdef DS18B20
  Serial.print("#Adding external temperature sensor...");
  dts.begin();
  DeviceAddress da;
  dts.getAddress(da, 0);
  dts.setResolution(da, DS18B20RES);
  dts.setWaitForConversion(false);
  Serial.println("ok!");
#endif
#ifdef BLE
  Serial.print("#Adding BTLESerial...");
  microbit.BTLESerial.begin();
  microbit.BTLESerial.setLocalName("microbit");
  microbit.begin();
  Serial.println("ok!");
#endif
  Serial.println("#=== Setup done ===");
}


class Record {
  public:
    Record(unsigned long t);
    void clear();
    void accumulate(Record other);
    void finalize();
    void report(Stream &io);

    unsigned long time;
    int n;
#ifdef BME280
    double wb_temp;
    double wb_pressure;
    double wb_humidity;
#endif 
#ifdef VEML6030
    double light;
#endif
#ifdef WEATHER
    double rain;
    double wspd;
    double wdir;
    double wdir_x;
    double wdir_y;
#endif
#ifdef DS18B20
    double ext_temp;
#endif
};


Record::Record(unsigned long t) {
  clear();
  time = t;
};


void Record::clear() {
  n = 0;
#ifdef BME280
  wb_temp = 0;
  wb_pressure = 0;
  wb_humidity = 0;
#endif
#ifdef VEML6030
  light = 0;
#endif
#ifdef WEATHER
  rain = 0;
  wspd = 0;
  wdir = 0;
  wdir_x = 0;
  wdir_y = 0;
#endif
#ifdef DS18B20
  ext_temp = 0;
#endif
};


void Record::accumulate(Record other) {
  time = other.time;
#ifdef BME280
  wb_temp += other.wb_temp;
  wb_pressure += other.wb_pressure;
  wb_humidity += other.wb_humidity;
#endif
#ifdef VEML6030
  light += other.light;
#endif
#ifdef WEATHER
  rain += other.rain;
  wspd += other.wspd;
  float ra = other.wdir / 180. * PI;
  // TODO weight by wind speed?
  wdir_x += cos(ra);
  wdir_y += sin(ra);
#endif
#ifdef DS18B20
  ext_temp += other.ext_temp;
#endif
  n += other.n;
};

void Record::finalize() {
  if (n < 2) return;
#ifdef BME280
  wb_temp /= n;
  wb_pressure /= n;
  wb_humidity /= n;
#endif
#ifdef VEML6030
  light /= n;
#endif
#ifdef WEATHER
  // rain accumulates
  wspd /= n;
  // average accounting for rollover
  wdir = atan2(wdir_y / n, wdir_x / n) / PI * 180.;
  if (wdir < 0) wdir += 360;
#endif
#ifdef DS18B20
  ext_temp /= n;
#endif
};


void Record::report(Stream &io) {
  io.print(time); io.print(",");
#ifdef VEML6030
  io.print(light, 4); io.print(",");
#endif
#ifdef WEATHER
  io.print(wdir, 4); io.print(",");
  io.print(wspd, 4); io.print(",");
  io.print(rain, 4); io.print(",");
#endif
#ifdef BME280
  io.print(wb_temp, 4); io.print(",");
  io.print(wb_pressure, 4); io.print(",");
  io.print(wb_humidity, 4); io.print(",");
#endif
#ifdef DS18B20
  io.print(ext_temp, 4); io.print(",");
#endif
  io.println(record_count);
};


void print_header(Stream &io) {
  io.print("#Time,");
#ifdef VEML6030
  io.print("Light,");
#endif
#ifdef WEATHER
  io.print("WindDir,");
  io.print("WindSpd,");
  io.print("Rain,");
#endif
#ifdef BME280
  io.print("WBTemp,");
  io.print("WBPres,");
  io.print("WBHum,");
#endif
#ifdef DS18B20
  io.print("ExtTemp,");
#endif
  io.println("SampleIndex");
};


Record avg(millis());
Record datum(millis());


void loop() {
#ifdef BLE
  microbit.BTLESerial.poll();
#endif
  bool trigger_header = false;
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'h') {
      trigger_header = true;
    };
    // TODO other serial commands?
  };
  if (trigger_header || (header_timer >= HEADER_INTERVAL)) {
    print_header(Serial);
#ifdef BLE
    print_header(microbit.BTLESerial);
#endif
    header_timer = 0;
  };
  if (poll_timer >= POLL_INTERVAL) {
    DBG("Polling")
    poll_timer = 0;
    // clear current data record (datum)
    datum.clear();

    // start filling and wait for all data
    datum.time = millis();
    poll_state = 0;
#ifdef BME280
    poll_state |= BME280_POLL_MASK;
    bme280.measure();
#endif
#ifdef VEML6030
    datum.light = light.readLight();
#endif
#ifdef WEATHER
    datum.wdir = wdir_val_to_dir(analogRead(WDIRPIN));
    datum.wspd = wspd.get_and_reset_count() * wspd_scale;
    datum.rain = rain.get_and_reset_count() * 0.2794;
#endif
#ifdef DS18B20
    poll_state |= DS18B20_POLL_MASK;
    dts.requestTemperatures();
    dts_timer = 0;
#endif
    DBG(poll_state)
  };
  if (poll_state != 0) {
    // check if sensors are done polling
#ifdef BME280
    if (poll_state & BME280_POLL_MASK) {
      if (bme280.hasValue()) {   // if true, measurement is ready
        DBG("Reading BME280")
        DBG(poll_state)
        datum.wb_temp = bme280.getTemperature();
        datum.wb_pressure = bme280.getPressure();
        datum.wb_humidity = bme280.getHumidity();
        poll_state ^= BME280_POLL_MASK;
        DBG(poll_state)
      };
    };
#endif
#ifdef DS18B20
    if (poll_state & DS18B20_POLL_MASK) {
      if (dts_timer > DS18B20CONVT) {
        DBG("Reading DS18B20")
        DBG(poll_state)
        datum.ext_temp = dts.getTempCByIndex(0);
        poll_state ^= DS18B20_POLL_MASK;
        DBG(poll_state)
      };
    };
#endif
    // if all done, add datum to avg
    if (poll_state == 0) {
      DBG("Polling done")
      datum.time = millis();
      datum.n = 1;
      record_count += 1;
      avg.accumulate(datum);
#ifdef BLE
      DBG("BLE report")
      datum.report(microbit.BTLESerial);
      DBG("BLE report done")
#endif
    };
  };
  if (avg.n >= REPORT_AFTER_N_DATA) {
    // generate serial report
    DBG("finalize")
    avg.finalize();
    DBG("Serial report")
    avg.report(Serial);
    DBG("clear")
    avg.clear();
  };
}
