"""Sensor for the DHMZ."""
from datetime import timedelta, datetime
import gzip
import json
import logging
import os
from urllib.request import urlopen, URLError, HTTPError
from lxml import etree
import voluptuous as vol

from homeassistant.components.weather import (
    ATTR_WEATHER_HUMIDITY,
    ATTR_WEATHER_PRESSURE,
    ATTR_WEATHER_WIND_SPEED,
    ATTR_WEATHER_TEMPERATURE,
    ATTR_WEATHER_WIND_BEARING,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_CONDITION,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_MONITORED_CONDITIONS,
    __version__,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

ATTR_STATION = "station"
ATTR_REGION = "region"
ATTR_FORECAST_TEXT = "forecast_text"
ATTR_UPDATED = "updated"

CONF_STATION_NAME = "station_name"
CONF_FORECAST_REGION_NAME = "forecast_region_name"
CONF_FORECAST_TEXT = "forecast_text"
CONF_FORECAST_STATION_NAME = "forecast_station_name"

DEFAULT_NAME = "dhmz"

CURRENT_SITUATION_API_URL = "https://vrijeme.hr/hrvatska_n.xml"
PRECIPITATION_API_URL = "https://vrijeme.hr/oborina.xml"
FORECAST_TODAY_API_URL = "https://prognoza.hr/prognoza_danas.xml"
FORECAST_TOMMOROW_API_URL = "https://prognoza.hr/prognoza_sutra.xml"
FORECAST_3DAYS_API_URL = "https://prognoza.hr/tri/3d_graf_i_simboli.xml"
FORECAST_7DAYS_API_URL = "https://prognoza.hr/sedam/hrvatska/7d_meteogrami.xml"

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=15)

SENSOR_TYPES = {
    # from "hrvatska_n.xml"
    ATTR_WEATHER_PRESSURE: ("Pressure", "hPa", "Stat hPa", float, "Tlak", ["pressure_tendency"], "mdi:thermometer-lines"),
    "pressure_tendency": ("Pressure Tendency", "hPa", "Delta hPa", float, "TlakTend", [], "mdi:thermometer-plus"),
    ATTR_WEATHER_HUMIDITY: ("Humidity", "%", "RF %", int, "Vlaga", [], "mdi:water-percent"),
    ATTR_WEATHER_WIND_SPEED: ("Wind Speed", "m/s", "WS m/s", float, "VjetarBrzina", [], "mdi:weather-windy"),
    ATTR_WEATHER_WIND_BEARING: ("Wind Bearing", "°", "WD °", int, "VjetarSmjer", [], "mdi:compass"),
    ATTR_WEATHER_TEMPERATURE: ("Temperature", "°C", "T °C", float, "Temp", [], "mdi:thermometer"),
	"condition": ("Condition", None, "Type", str, "Vrijeme", ["weather_symbol"], ""),
	"weather_symbol": ("Weather Symbol", None, "Symbol", int, "VrijemeZnak", [], ""),
    "station_name": ("Station Name", None, "Station", str, "GradIme", [], "mdi:map-marker"),
    "lon": ("Longitude", "°", "Long °", float, "Lon", [], "mdi:longitude"),
    "lat": ("Latitude", "°", "Latt °", float, "Lat", [], "mdi:latitude"),
    "update_timestamp": ("Update Timestamp", None, "Update", str, "Timestamp", [], "mdi:update"),
    # from "oborine.xml"
    "precipitation": ("Precipitation", "mm", "mm/24h", float, "kolicina", ["precipitation_update_timestamp"], "mdi:weather-pouring"),
    "precipitation_update_timestamp": ("Precipitation Update Timestamp", None, "Update", str, "kolicina_timestamp", [], "mdi:update"),
    # forecast texts
    "forecast_text_today": ("Today forecast", "", "", str, "PrognozaDanas", [], "mdi:calendar-today"),
    "forecast_text_tommorow": ("Today forecast", "", "", str, "PrognozaSutra", [], "mdi:calendar-blank"),
}

FORECAST_DAILY_TYPES = {
    ATTR_FORECAST_TIME: ("datetime"),
    ATTR_FORECAST_CONDITION: ("vrijeme"),
    ATTR_FORECAST_TEMP: ("Tmx"),
    ATTR_FORECAST_TEMP_LOW: ("Tmn"),
    "wind": ("wind"),
    ATTR_FORECAST_TEXT: ("text"),
}

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_MONITORED_CONDITIONS, default=[ATTR_WEATHER_TEMPERATURE]): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        ),        
        vol.Required(CONF_STATION_NAME): cv.string,
        vol.Required(CONF_FORECAST_REGION_NAME): cv.string,
        vol.Required(CONF_FORECAST_TEXT): cv.string,
        vol.Required(CONF_FORECAST_STATION_NAME): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the DHMZ sensor platform."""
    name = config.get(CONF_NAME)
    station_name = config.get(CONF_STATION_NAME)
    forecast_region_name = config.get(CONF_FORECAST_REGION_NAME)
    forecast_text = config.get(CONF_FORECAST_TEXT)
    forecast_station_name = config.get(CONF_FORECAST_STATION_NAME)

    # if station_name not in dhmz_stations(hass.config.config_dir):
    #     _LOGGER.error(
    #         "Configured DHMZ %s (%s) is not a known station",
    #         CONF_STATION_NAME,
    #         station_name,
    #     )
    #     return False
    
	# if forecast_region_name not in dhmz_regions(hass.config.config_dir):
    #     _LOGGER.error(
    #         "Configured DHMZ %s (%s) is not a known region",
    #         CONF_FORECAST_REGION_NAME,
    #         forecast_region_name,
    #     )
    #     return False

    probe = DhmzData(station_name=station_name, forecast_region_name=forecast_region_name, forecast_text=forecast_text, forecast_station_name=forecast_station_name)
    try:
        probe.update()
    except (ValueError, TypeError) as err:
        _LOGGER.error("Received error from DHMZ: %s", err)
        return False

    add_entities(
        [
            DhmzSensor(probe, variable, name)
            for variable in config[CONF_MONITORED_CONDITIONS]
        ],
        True,
    )


class DhmzSensor(Entity):
    """Implementation of a DHMZ sensor."""

    def __init__(self, probe, variable, name):
        """Initialize the sensor."""
        self.probe = probe
        self.client_name = name
        self.variable = variable
        _LOGGER.debug("Initializing: %s", variable)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.client_name} {self.variable}"

    @property
    def icon(self):
        """Return the name of the sensor."""
        return SENSOR_TYPES[self.variable][6]

    @property
    def state(self):
        """Return the state of the sensor."""
        if (self.variable == "forecast_text_today") or (self.variable == "forecast_text_tommorow"):
            return self.probe.get_data(SENSOR_TYPES[self.variable][4])[:255]
        else:
            return self.probe.get_data(SENSOR_TYPES[self.variable][4])

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return SENSOR_TYPES[self.variable][1]

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        ret = {
            ATTR_STATION: self.probe.get_data(SENSOR_TYPES["station_name"][4]),
        }
        if self.variable == "precipitation":
            ret[ATTR_UPDATED] = self.probe.last_update_precipitation
        else:
            ret[ATTR_UPDATED] = self.probe.last_update
        if self.variable == ATTR_WEATHER_PRESSURE:
            ret["pressure_tendency"] = self.probe.get_data(SENSOR_TYPES["pressure_tendency"][4]) + " hPa"
        return(ret)

    @property
    def entity_picture(self):
        """Weather symbol if type is condition."""
        if self.variable != "condition":
            return None
        return (
            "https://meteo.hr/assets/images/icons/{0}.svg".format(self.probe.get_data(SENSOR_TYPES["weather_symbol"][4]))
        )

    def update(self):
        """Delegate update to probe."""
        self.probe.update()

class DhmzData:
    """The class for handling the data retrieval."""

    _station_name = ""
    _forecast_region_name = ""
    _forecast_text = ""
    _forecast_station_name = ""
    _data = {}
    _forecast_daily = []
    _forecast_hourly = []

    def __init__(self, station_name, forecast_region_name, forecast_text, forecast_station_name):
        """Initialize the probe."""
        self._station_name = station_name
        self._forecast_region_name = forecast_region_name
        self._forecast_text = forecast_text
        self._forecast_station_name = forecast_station_name
        self._data = {}
        self._forecast_daily = []
        self._forecast_hourly = []
        _LOGGER.debug("Initialized sensor data: %s, %s, %s, %s", station_name, forecast_region_name, forecast_text, forecast_station_name)

    @property
    def last_update(self):
        """Return the timestamp of the most recent data."""
        date_time = self._data.get("Timestamp")
        if date_time is not None:
            return datetime.strptime(date_time, "%d.%m.%Y %H:%M:%S")

    @property
    def last_update_precipitation(self):
        """Return the timestamp of the most recent precipitation data."""
        date_time = self._data.get("kolicina_timestamp")
        if date_time is not None:
            return datetime.strptime(date_time, "%d.%m.%Y. %H:%M:%S")

    def current_situation(self):
        """Fetch and parse the latest XML data."""
        try:
            _LOGGER.debug("Refreshing current_situation - hrvatska_n.xml")
            elems = []
            # get current weather "hrvatska_n.xml"
            tree = etree.parse(urlopen(CURRENT_SITUATION_API_URL))
            elems = tree.xpath("//Hrvatska/Grad[GradIme='" + self._station_name + "']/Podatci/*")
            elem_lat = tree.xpath("//Hrvatska/Grad[GradIme='" + self._station_name + "']/Lat")
            elem_lon = tree.xpath("//Hrvatska/Grad[GradIme='" + self._station_name + "']/Lon")
            elem_gradime = tree.xpath("//Hrvatska/Grad[GradIme='" + self._station_name + "']/GradIme")
            elems.extend(elem_lat)
            elems.extend(elem_lon)
            elems.extend(elem_gradime)
            vardt = etree.Element("Timestamp")
            vardt.text = tree.xpath("//Hrvatska/DatumTermin/Datum/text()")[0] + " " + tree.xpath("//Hrvatska/DatumTermin/Termin/text()")[0] + ":00:00"
            elems.extend([vardt])

            _LOGGER.debug("Refreshing current_situation - oborine.xml")
            # get percipitation "oborine.xml"
            tree = etree.parse(urlopen(PRECIPITATION_API_URL))
            elem_kisa = tree.xpath("//dnevna_oborina/grad[ime='" + self._station_name + "']/kolicina")
            if elem_kisa: 
                elems.extend(elem_kisa)
                vardt_kisa = etree.Element("kolicina_timestamp")
                vardt_kisa.text = tree.xpath("//dnevna_oborina/datumtermin/datum/text()")[0] + " " + tree.xpath("//dnevna_oborina/datumtermin/termin/text()")[0] + ":00:00"
                elems.extend([vardt_kisa])

            #return data back
            return elems

        except HTTPError as err:
            _LOGGER.error("HTTP error: %s", err.reason )
        except URLError as err:
            _LOGGER.error("URL error: %s", err.reason )
        except etree.ParseError as err:
            _LOGGER.error("LXML PARSE error: %s at position: %s", err.message, err.position )
        except etree.ParserError as err:
            _LOGGER.error("LXML PARSER error: %s", err.message )

    def forecast_daily(self):
        """Fetch and parse the latest daily forecast XML data."""
        try:
            _LOGGER.debug("Refreshing forecast_daily - prognoza_danas.xml")
            ret = []
            elems = {}
            # get "prognoza_danas.xml"
            tree = etree.parse(urlopen(FORECAST_TODAY_API_URL))
            val_condition = tree.xpath("//VW/section/station[@name='" + self._forecast_region_name + "']/param[@name='vrijeme']/@value")[0]
            val_temp_min = tree.xpath("//VW/section/station[@name='" + self._forecast_region_name + "']/param[@name='Tmn']/@value")[0]
            val_temp_max = tree.xpath("//VW/section/station[@name='" + self._forecast_region_name + "']/param[@name='Tmx']/@value")[0]
            val_wind = tree.xpath("//VW/section/station[@name='" + self._forecast_region_name + "']/param[@name='wind']/@value")[0]
            val_text = tree.xpath("//VW/section/param[@name='" + self._forecast_text + "']/@value")[0]
            val_datetime = tree.xpath("//VW/metadata/datatime/text()")[0] + " 00:00:00"
            elems["vrijeme"] = val_condition
            elems["Tmx"] = val_temp_max
            elems["Tmn"] = val_temp_min
            elems["wind"] = val_wind
            elems["text"] = val_text
            elems["datetime"] = datetime.strptime(val_datetime, "%d%m%y %H:%M:%S")
            ret.append(elems)

            _LOGGER.debug("Refreshing forecast_daily - prognoza_sutra.xml")
            elems_tm = {}
            # get "prognoza_sutra.xml"
            tree = etree.parse(urlopen(FORECAST_TOMMOROW_API_URL))
            val_condition = tree.xpath("//VW/section/station[@name='" + self._forecast_region_name + "']/param[@name='vrijeme']/@value")[0]
            val_temp_min = tree.xpath("//VW/section/station[@name='" + self._forecast_region_name + "']/param[@name='Tmn']/@value")[0]
            val_temp_max = tree.xpath("//VW/section/station[@name='" + self._forecast_region_name + "']/param[@name='Tmx']/@value")[0]
            val_wind = tree.xpath("//VW/section/station[@name='" + self._forecast_region_name + "']/param[@name='wind']/@value")[0]
            val_text = tree.xpath("//VW/section/param[@name='" + self._forecast_text + "']/@value")[0]
            val_datetime = tree.xpath("//VW/metadata/datatime/text()")[0] + " 00:00:00"
            elems_tm["vrijeme"] = val_condition
            elems_tm["Tmx"] = val_temp_max
            elems_tm["Tmn"] = val_temp_min
            elems_tm["wind"] = val_wind
            elems_tm["text"] = val_text
            elems_tm["datetime"] = (datetime.strptime(val_datetime, "%d%m%y %H:%M:%S") + timedelta(days=1))
            ret.append(elems_tm)
            
            # return data back
            return ret

        except HTTPError as err:
            _LOGGER.error("HTTP error: %s", err.reason )
        except URLError as err:
            _LOGGER.error("URL error: %s", err.reason )
        except etree.ParseError as err:
            _LOGGER.error("LXML PARSE error: %s at position: %s", err.message, err.position )
        except etree.ParserError as err:
            _LOGGER.error("LXML PARSER error: %s", err.message )

    def forecast_hourly(self):
        """Fetch and parse the latest daily forecast XML data."""
        try:
            ret = []
            _LOGGER.debug("Refreshing forecast_hourly - 7d_meteogrami.xml")
            # get forecast weather "7d_meteogrami.xml"
            tree = etree.parse(urlopen(FORECAST_7DAYS_API_URL))
            node_days = tree.xpath("//sedmodnevna_aliec/grad[@lokacija='" + self._forecast_station_name + "']/*")
            for node in node_days:
                elems = {}
                elems["vrijeme"] = node.xpath("simbol/text()")[0]
                elems["Tmx"] = node.xpath("t_2m/text()")[0]
                elems["wind"] = node.xpath("vjetar/text()")[0]
                elems["percipitation"] = node.xpath("oborina/text()")[0]
                elems["datetime"] = datetime.strptime(node.get("datum") + " " + node.get("sat"), "%d.%m.%Y. %H")
                ret.append(elems)

            # return data back
            return ret

        except HTTPError as err:
            _LOGGER.error("HTTP error: %s", err.reason )
        except URLError as err:
            _LOGGER.error("URL error: %s", err.reason )
        except etree.ParseError as err:
            _LOGGER.error("LXML PARSE error: %s at position: %s", err.message, err.position )
        except etree.ParserError as err:
            _LOGGER.error("LXML PARSER error: %s", err.message )

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from DHMZ."""
        if self.last_update and (
            self.last_update + timedelta(hours=1)
            > datetime.now()
        ):
            _LOGGER.debug("Skipping sensor data update, last_update was: %s", self.last_update)
            return  # Not time to update yet; data is only hourly

        _LOGGER.debug("Doing sensor data update, last_update was: %s", self.last_update)
        for dataline in self.current_situation():
            self._data[dataline.tag] = dataline.text.strip()

        self._forecast_daily = self.forecast_daily()
        if self._forecast_daily:
            self._data["PrognozaDanas"] = self._forecast_daily[0]["text"]
            self._data["PrognozaSutra"] = self._forecast_daily[1]["text"]

        self._forecast_hourly = self.forecast_hourly()

        _LOGGER.debug("Sensor, current data: %s", self._data)
        # _LOGGER.debug("DHMZ Sensor, current forecast daily: %s", self._forecast_daily)
        # _LOGGER.debug("DHMZ Sensor, current forecast hourly: %s", self._forecast_hourly)

        _LOGGER.debug("Updating - finished.")

    def get_data(self, variable):
        """Get the data."""
        return self._data.get(variable)

    def get_forecast_daily(self):
        """Get the data."""
        return self._forecast_daily

    def get_forecast_hourly(self):
        """Get the data."""
        return self._forecast_hourly

def get_dhmz_stations():
    """Return {CONF_STATION: (lat, lon)} for all stations, for auto-config."""

    stations={}
    tree = etree.parse(urlopen(CURRENT_SITUATION_API_URL))
    elems = tree.xpath("//Hrvatska/Grad")
    for elem in elems:
        ime = elem.xpath("GradIme")[0]
        lon = elem.xpath("Lon")[0]
        lat = elem.xpath("Lat")[0]
        stations[ime.text] = (float(lat.text), float(lon.text))

    return stations


def dhmz_stations(cache_dir):
    """Return {CONF_STATION: (lat, lon)} for all stations, for auto-config.

    Results from internet requests are cached as compressed json, making
    subsequent calls very much faster.
    """
    cache_file = os.path.join(cache_dir, ".zamg-stations.json.gz")
    if not os.path.isfile(cache_file):
        stations = get_dhmz_stations()
        with gzip.open(cache_file, "wt") as cache:
            json.dump(stations, cache, sort_keys=True)
        return stations
    with gzip.open(cache_file, "rt") as cache:
        return {k: tuple(v) for k, v in json.load(cache).items()}
