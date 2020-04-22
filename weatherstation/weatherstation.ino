#include <elapsedMillis.h>
#include <Wire.h>

// TODO serial logger
// TODO soil moistrue meter?

// interal temperature/humidity/pressure sensor
#define BME280

// light sensor
#define VEML6030

// weather (rain and wind) sensors
#define WEATHER

// one-wire temperature sensor
#define DS18B20

#ifdef BME280
// requires installing BMx280MI library
#include <BMx280I2C.h>
BMx280I2C bme280(0x76);
bool bme280_waiting = false;
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
  private:
    int pin;
    int count;
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
bool dts_waiting = false;
#endif


// -------------------------------------------------------


elapsedMillis report_timer;
//#define REPORT_INTERVAL 1000
#define REPORT_INTERVAL 60000
float wspd_scale = 2.4 / (REPORT_INTERVAL / 1000.);

void setup (){
  Serial.begin(9600);
  Serial.println("Weather station booting...");
  Wire.begin();
#ifdef BME280
  Serial.println("Adding BME280...");
  bme280.begin();
  Serial.println("  resetting...");
  bme280.resetToDefaults();
  Serial.println("  set sampling...");
  bme280.writeOversamplingPressure(BMx280MI::OSRS_P_x01);
  bme280.writeOversamplingTemperature(BMx280MI::OSRS_T_x01);
  bme280.writeOversamplingHumidity(BMx280MI::OSRS_H_x01);
  Serial.println("  set filter...");
  bme280.writeFilterSetting(BMx280MI::FILTER_OFF);
#endif
#ifdef VEML6030
  Serial.println("Adding VEML6030...");
  light.begin();
  light.setGain(0.125);
  light.setIntegTime(50); 
#endif
#ifdef WEATHER
  Serial.println("Adding wind and rain sensors...");
#endif
#ifdef DS18B20
  dts.begin();
  DeviceAddress da;
  dts.getAddress(da, 0);
  dts.setResolution(da, DS18B20RES);
  dts.setWaitForConversion(false);
#endif
}

void loop() {
  rain.update();
  wspd.update();
  if (report_timer >= REPORT_INTERVAL) {
    report_timer = 0;
    Serial.print("time,");
    Serial.println(millis());
#ifdef BME280
    bme280.measure();  // if false, measure couldn't start
    bme280_waiting = true;
#endif
#ifdef VEML6030
    Serial.print("light,");
    Serial.println(light.readLight(), 4);
#endif
#ifdef WEATHER
    Serial.print("wind_dir,");
    Serial.println(wdir_val_to_dir(analogRead(WDIRPIN)), 1);
    Serial.print("wind_speed,");
    Serial.println(wspd.get_and_reset_count() * wspd_scale, 4);
    Serial.print("rain,");
    Serial.println(rain.get_and_reset_count() * 0.2794, 4);
#endif
#ifdef DS18B20
    dts.requestTemperatures();
    dts_waiting = true;
    dts_timer = 0;
#endif
  };
#ifdef BME280
  if (bme280_waiting) {
    if (bme280.hasValue()) {   // if true, measurement is ready
      Serial.print("wb_temp,");
      Serial.println(bme280.getTemperature(), 4);
      Serial.print("wb_pressure,");
      Serial.println(bme280.getPressure(), 4);
      Serial.print("wb_humidity,");
      Serial.println(bme280.getHumidity(), 2);
      bme280_waiting = false;
    };
  };
#endif
#ifdef DS18B20
  if (dts_waiting) {
    if (dts_timer > DS18B20CONVT) {
      dts_waiting = false;
      Serial.print("ext_temp,");
      Serial.println(dts.getTempCByIndex(0));
    };
  };
#endif
}
