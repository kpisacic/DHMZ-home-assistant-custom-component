"""Sensor for data from DHMZ."""
import logging
from operator import itemgetter
from datetime import timedelta, datetime
import voluptuous as vol

from homeassistant.components.weather import (
    ATTR_WEATHER_HUMIDITY,
    ATTR_WEATHER_PRESSURE,
    ATTR_WEATHER_TEMPERATURE,
    ATTR_WEATHER_WIND_BEARING,
    ATTR_WEATHER_WIND_SPEED,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_WIND_SPEED,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_PRECIPITATION,
    PLATFORM_SCHEMA,
    WeatherEntity,
    Forecast,
    WeatherEntityFeature
)
from homeassistant.const import CONF_NAME, UnitOfTemperature, UnitOfPressure, UnitOfSpeed, UnitOfPrecipitationDepth
from homeassistant.helpers import config_validation as cv

# Reuse data and API logic from the sensor implementation
from .sensor import (
    DEFAULT_NAME,
    CONF_STATION_NAME,
    CONF_FORECAST_REGION_NAME,
    CONF_FORECAST_TEXT,
    CONF_FORECAST_STATION_NAME,
    DhmzData,
    SENSOR_TYPES,
    ATTR_STATION,
    ATTR_UPDATED,
)

CONDITION_CLASSES = {
    "clear-night": ["1n"],
    "cloudy": ["5","6","5n","6n"],
    "fog": ["7","8","9","10","11","39","40","41","42","7n","8n","9n","10n","11n","39n","40n","41n","42n"],
    "hail": [],
    "lightning": ["15","25","29","15n","25n","29n"],
    "lightning-rainy": ["16","17","18","30","31","16n","17n","18n","30n","31n"],
    "partlycloudy": ["2","3","4","2n","3n","4n"],
    "pouring": ["14","28","32","14n","28n","32n"],
    "rainy": ["12","13","26","27","12n","13n","26n","27n"],
    "snowy": ["22","23","24","36","37","38","22n","23n","24n","36n","37n","38n"],
    "snowy-rainy": ["19","20","21","33","34","35","19n","20n","21n","33n","34n","35n"],
    "sunny": ["1"],
    "windy": [],
    "windy-variant": [],
    "exceptional": ["-"],
}

WIND_MAPPING = {
    0: ("-", 0),
    1: ("N", 10),
    2: ("NE", 10),
    3: ("E", 10),
    4: ("SE", 10),
    5: ("S", 10),
    6: ("SW", 10),
    7: ("W", 10),
    8: ("NW", 10),
    9: ("N", 25),
    10: ("NE", 25),
    11: ("E", 25),
    12: ("SE", 25),
    13: ("S", 25),
    14: ("SW", 25),
    15: ("W", 25),
    16: ("NW", 25),
    17: ("N", 50),
    18: ("NE", 50),
    19: ("E", 50),
    20: ("SE", 50),
    21: ("S", 50),
    22: ("SW", 50),
    23: ("W", 50),
    24: ("NW", 50),
}

WIND_SPEED_MAPPING = {
    0: 0,
    1: 10,
    2: 25,
    3: 50,
}

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_STATION_NAME): cv.string,
        vol.Required(CONF_FORECAST_REGION_NAME): cv.string,
        vol.Required(CONF_FORECAST_TEXT): cv.string,
        vol.Required(CONF_FORECAST_STATION_NAME): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

SCAN_INTERVAL = timedelta(minutes=10)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the DHMZ weather platform."""
    name = config.get(CONF_NAME)
    station_name = config.get(CONF_STATION_NAME)
    forecast_region_name = config.get(CONF_FORECAST_REGION_NAME)
    forecast_text = config.get(CONF_FORECAST_TEXT)
    forecast_station_name = config.get(CONF_FORECAST_STATION_NAME)

    _LOGGER.debug("Setup weather platform: %s, %s, %s, %s",  station_name, forecast_region_name, forecast_text, forecast_station_name )

    probe = DhmzData(station_name=station_name, forecast_region_name=forecast_region_name, forecast_text=forecast_text, forecast_station_name=forecast_station_name)
    try:
        probe.update()
    except (ValueError, TypeError) as err:
        _LOGGER.error("Received error from DHMZ: %s", err)
        return False

    add_entities([DhmzWeather(probe, name)], True)

class DhmzWeather(WeatherEntity):
    """Representation of a weather condition."""

    def __init__(self, dhmz_data, name):
        """Initialise the platform with a data instance and station name."""
        _LOGGER.debug("Initialized.")
        self.dhmz_data = dhmz_data
        self._name = name
        self._state = self.format_condition(self.dhmz_data.get_data(SENSOR_TYPES["weather_symbol"][4]))
        self._last_update = self.dhmz_data.last_update

    def update(self):
        """Update current conditions."""
        _LOGGER.debug("Update - called.")
        self.dhmz_data.update()
        if self._last_update != self.dhmz_data.last_update:
            _LOGGER.debug("Update - updated last date found.")
            self._last_update = self.dhmz_data.last_update
            self._state = self.format_condition(self.dhmz_data.get_data(SENSOR_TYPES["weather_symbol"][4]))
        else:
            _LOGGER.debug("Update - no update found.")

    @property
    def supported_features(self) -> WeatherEntityFeature:
        return WeatherEntityFeature.FORECAST_HOURLY
        
    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state
    
    @property
    def condition(self):
        """Return the current condition."""
        return self.format_condition(self.dhmz_data.get_data(SENSOR_TYPES["weather_symbol"][4]))

    @property
    def entity_picture(self):
        """Weather symbol if type is condition."""
        return (
            "https://meteo.hr/assets/images/icons/{0}.svg".format(self.dhmz_data.get_data(SENSOR_TYPES["weather_symbol"][4]))
        )

    @property
    def attribution(self):
        """Return the attribution."""
        return "Data provided by DHMZ"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        ret = {
            "condition": self.dhmz_data.get_data(SENSOR_TYPES["condition"][4]),
            "weather_symbol": self.dhmz_data.get_data(SENSOR_TYPES["weather_symbol"][4]),
            ATTR_STATION: self.dhmz_data.get_data(SENSOR_TYPES["station_name"][4]),
            ATTR_UPDATED: self.dhmz_data.last_update.isoformat(),
            "pressure_tendency": self.dhmz_data.get_data(SENSOR_TYPES["pressure_tendency"][4]),
            "precipitation": self.dhmz_data.get_data(SENSOR_TYPES["precipitation"][4]) if self.dhmz_data.get_data(SENSOR_TYPES["precipitation"][4]) else "0",
            "forecast_today": self.dhmz_data.get_data(SENSOR_TYPES["forecast_text_today"][4]),
            "forecast_tommorow": self.dhmz_data.get_data(SENSOR_TYPES["forecast_text_tommorow"][4]),
            "forecast_list": self._get_forecast(),
        }
        return(ret)

    @property
    def native_temperature(self):
        """Return the platform temperature."""
        try:
            s_val = self.dhmz_data.get_data(SENSOR_TYPES[ATTR_WEATHER_TEMPERATURE][4]) or ""
            f_ret = float(s_val)
        except ValueError:
            _LOGGER.warning("Temperature - value not float: %s", s_val )
            f_ret = 0
        return f_ret

    @property
    def native_temperature_unit(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def native_pressure(self):
        """Return the pressure."""
        try:
            s_val = self.dhmz_data.get_data(SENSOR_TYPES[ATTR_WEATHER_PRESSURE][4]) or ""
            f_ret = float(s_val)
        except ValueError:
            _LOGGER.warning("Pressure - value not float: %s", s_val )
            f_ret = 0
        return f_ret

    @property
    def native_pressure_unit(self):
        """Return the unit of measurement."""
        return UnitOfPressure.HPA

    @property
    def humidity(self):
        """Return the humidity."""
        try:
            s_val = self.dhmz_data.get_data(SENSOR_TYPES[ATTR_WEATHER_HUMIDITY][4]) or ""
            f_ret = float(s_val)
        except ValueError:
            _LOGGER.warning("Humidity - value not float: %s", s_val )
            f_ret = 0
        return f_ret

    @property
    def native_precipitation(self):
        """Return the precipitation."""
        try:
            s_val = self.dhmz_data.get_data(SENSOR_TYPES["precipitation"][4]) or "0"
            f_ret = float(s_val)
        except ValueError:
            _LOGGER.warning("Humidity - value not float: %s", s_val )
            f_ret = 0
        return f_ret

    @property
    def native_precipitation_unit(self):
        """Return the precipitation unit."""
        return UnitOfPrecipitationDepth.MILLIMETERS

    @property
    def native_wind_speed(self):
        """Return the wind speed."""
        try:
            s_val = self.dhmz_data.get_data(SENSOR_TYPES[ATTR_WEATHER_WIND_SPEED][4]) or ""
            f_ret = float(s_val)
        except ValueError:
            _LOGGER.warning("Wind speed - value not float: %s", s_val )
            f_ret = 0
        return f_ret

    @property
    def native_wind_speed_unit(self):
        """Return the unit of measurement."""
        return UnitOfSpeed.METERS_PER_SECOND

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        return self.dhmz_data.get_data(SENSOR_TYPES[ATTR_WEATHER_WIND_BEARING][4])

    @staticmethod
    def format_condition(weather_symbol):
        """Return condition from dict CONDITION_CLASSES."""
        try:
            s_ret = [ k for k, v in CONDITION_CLASSES.items() if weather_symbol in v][0]
            return s_ret
        except IndexError as err:
            _LOGGER.warning("Unknown DHMZ weather symbol: %s", weather_symbol )
            return "exceptional"

    def _get_forecast(self) -> list[Forecast]:
        ret = []
        for entry in self.dhmz_data.get_forecast_hourly():
            if entry.get("datetime") > datetime.now():
                try:
                    s_cond = [ k for k, v in CONDITION_CLASSES.items() if entry.get("vrijeme") in v ][0]
                except IndexError as err:
                    _LOGGER.warning("Unknown DHMZ weather symbol: %s", entry.get("vrijeme") )
                    s_cond = "exceptional"
                elem = {
                    ATTR_FORECAST_TIME: entry.get("datetime"),
                    ATTR_FORECAST_TEMP: float(entry.get("Tmx")),
                    ATTR_FORECAST_PRECIPITATION: float(entry.get("precipitation")),
                    ATTR_FORECAST_WIND_SPEED: WIND_SPEED_MAPPING[int(entry.get("wind")[-1:])],
                    ATTR_FORECAST_WIND_BEARING: entry.get("wind")[:-1],
                    ATTR_FORECAST_CONDITION: s_cond,
                    "weather_symbol": entry.get("vrijeme"),
                }
                ret.append(elem)
        if len(ret) == 0:
            retlist = None
        else:
            retlist = sorted(ret, key=itemgetter(ATTR_FORECAST_TIME)) 
        return retlist

    async def async_forecast_hourly(self) -> list[Forecast]:
        return self._get_forecast()

    @property
    def forecast(self):
        return self._get_forecast()
