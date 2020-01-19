# DHMZ-home-assistant-custom-component
Home Assistant Custom Components for DHMZ weather service ("Državni hidrometeorološki zavod Republike Hrvatske" / "Croatian Meteorological and Hydrological Service")

The `dhmz` weather platform provide meteorological data for DHMZ service ("Državni hidrometeorološki zavod Republike Hrvatske / "Croatian Meteorological and Hydrological Service") - https://meteo.hr/ . Data from DHMZ is listed on https://meteo.hr/proizvodi.php?section=podaci&param=xml_korisnici and provided under Open Licence of Republic of Croatia - https://data.gov.hr/otvorena-dozvola and https://data.gov.hr/open-licence-republic-croatia .
Custom weather card is also included in the package, combining graphical forecast data in weather card.

The following device types and data are supported:

- [Weather](#weather) - Current conditions and forecasts
- [Sensor](#sensor) - Current conditions and alerts
- [Camera](#camera) - Radar imagery
- [Custom Weather Card](#custom-card) - Custom lovelace card with 5-days forecast and DHMZ specifics

## Installation

There are two options; manual or HACS installation:

*Manual installation*
- Copy `dhmz`  folder in `custom_components` from repository to your Home Assistant configuration `custom_components` folder. Don't copy any other YAML files from repository root not to overwrite your own configuration.
- Copy `dhmz-weather-card.js` from `www` repocitory folder to your Home Assistant configuration `www` folder

*HACS installation*

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

- Use HACS custom repository (not default) - (https://github.com/kpisacic/DHMZ-home-assistant-custom-component)
- Copy `dhmz-weather-card.js` from `www` repocitory folder to your Home Assistant configuration `www` folder

## Location Selection

Each platform does not choose automatically which weather station's data to use. Selection of different identifiers is under configuration section of this document. Current version does not validate nor enforces configuration choices, but this is down the development roadmap.

For each platform, the location to use is determined according to the following list:

  - [station_name](#station_name) -  name of the station for current data (mandatory)
  - [forecast_region_name](#forecast_region_name) - name of the daily forecast region (mandatory)
  - [forecast_text](#forecast_text) - name of daily forecast text (mandatory)
  - [forecast_station_name](#forecast_station_name) - name of 7 days hourly forecast station (mandatory)

## Weather

The `dhmz` weather platform populates a weather card with DHMZ current conditions and forecast data.
To add DHMZ weather to your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
weather:
  - platform: dhmz
    name: DHMZ Maksimir
    station_name: Zagreb-Maksimir
    forecast_region_name: Zagreb
    forecast_text: zg_text
    forecast_station_name: Zagreb_Maksimir
```

- The platform checks for new data every 20 minutes, and the source data is typically updated hourly within 10 minutes after the hour.
- If no name is given, the weather entity will be named `weather.dhmz`.

*Configuration*

- name:
  - description: Name to be used for the entity ID, e.g. `weather.<name>`.
  - required: false
  - type: string
- station_name:
  - description: The station code of a specific weather station to use - see (#station_name)
  - required: true
  - type: string
- forecast_region_name:
  - description: The forecase region_name - see (#forecast_region_name)
  - required: true
  - type: string
- forecast_text:
  - description: The forecast text identifier - see ##forecast_text
  - required: true
  - type: string
- forecast_station_name:
  - description: The forecast station name - see ##forecast_station_name
  - required: true
  - type: string

## Sensor

The `dhmz` sensor platform creates sensors based on DHMZ current conditions data and daily forecasts.

To add DHMZ weather to your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
sensor:
  - platform: dhmz
    name: DHMZ Sensor Maksimir
    station_name: Zagreb-Maksimir
    forecast_region_name: Zagreb
    forecast_text: zg_text
    forecast_station_name: Zagreb_Maksimir
    monitored_conditions:
      - temperature
      - pressure
      - pressure_tendency
      - humidity
      - wind_speed
      - wind_bearing
      - condition
      - precipitation
      - forecast_text_today
      - forecast_text_tommorow
```

- A sensor will be created for each of the following conditions, with a default name like `sensor.<name>_temperature`:     
    - `temperature` - The current temperature, in ºC.
    - `pressure` - The current air pressure, in kPa.
    - `pressure_tendency` - The current air pressure tendency, e.g. "+0.5" in last hour.
    - `humidity` - The current humidity, in %.
    - `condition` - A brief text statement of the current weather conditions, e.g. "Sunny".
    - `wind_speed` - The current sustained wind speed, in km/h.
    - `wind_bearing` - The current cardinal wind direction, e.g. "SSW".
    - `precipitation` - precipitation in last 24 hours, in mm.
    - `forecast_text_today` - A textual description of today's forecast
    - `forecast_text_tommorow` - A textual description of tommorow's forecast

*Configuration*
- name:
  - description: Name to be used for the entity ID, e.g. `sensor.<name>_temperature`.
  - required: false
  - type: string
- station_name:
  - description: The station code of a specific weather station to use - see (#station_name)
  - required: true
  - type: string
- forecast_region_name:
  - description: The forecase region_name - see (#forecast_region_name)
  - required: true
  - type: string
- forecast_text:
  - description: The forecast text identifier - see ##forecast_text
  - required: true
  - type: string
- forecast_station_name:
  - description: The forecast station name - see ##forecast_station_name
  - required: true
  - type: string
- monitored_conditions:
  - description: List of sensors to monitor, create in home assistant
  - required: true
  - type: list or
      - temperature
      - pressure
      - pressure_tendency
      - humidity
      - wind_speed
      - wind_bearing
      - condition
      - precipitation
      - forecast_text_today
      - forecast_text_tommorow

## Camera

The `dhmz` camera platform displays DHMZ [radar imagery].

To add DHMZ radar imagery to your installation, add the desired lines from the following example to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
camera:
  - platform: dhmz
    name: DHMZ Radar
```

- If no name is given, the camera entity will be named `camera.dhmz`.

## Custom card

To add custom card for DHMZ weather, add following to your lovelace configuration YAML file:

1. Under resources section add custom card definition 

```yaml
resources:
  - type: js
    url: /local/dhmz-weather-card.js
```

2. In views and cards section add following card

```yaml
    cards:
      - mode: hourly
        type: 'custom:dhmz-weather-card'
        weather: weather.dhmz_maksimir
```

With `weather` attribute you should state name of the entity configured in weather compontent.
For mode, please use `daily` or `hourly`, since `hourly` was mostly customized and tested and is preffered to be used.

*Configuration*

- name:
  - description: Name to be used for the entity ID, e.g. `camera.<name>`.
  - required: false
  - type: string


## station_name

    RC Bilogora
    Bjelovar
    Crikvenica
    Crni Lug-NP Risnjak
    Daruvar
    Delnice
    Dubrovnik
    Dubrovnik-aerodrom
    Gospić
    RC Gorice (kod Nove Gradiške)
    RC Gradište (kod Županje)
    Gruda
    Hvar
    Imotski
    Karlovac
    Knin
    Komiža
    Krapina
    Krk
    Križevci
    Kukuljanovo
    Kutjevo
    Lastovo
    Lipik
    Malinska
    Makarska
    Mali Lošinj
    NP Mljet
    RC Monte Kope
    Ogulin
    Opatija
    RC Osijek-Čepin
    Osijek-aerodrom
    Palagruža
    Parg-Čabar
    Pazin
    NP Plitvička jezera
    Ploče
    Poreč
    Porer - svjetionik
    Prevlaka
    Pula
    Pula-aerodrom
    RC Puntijarka
    Rab
    Rijeka
    Rijeka-aerodrom
    Sv. Ivan na pučini - svjetionik
    Senj
    Sinj
    Sisak
    Slavonski Brod
    Split-Marjan
    Split-aerodrom
    Šibenik
    Varaždin
    Veli Rat - svjetionik
    Vinkovci
    Zadar
    Zadar-aerodrom
    Zagreb-Grič
    Zagreb-Maksimir
    Zagreb-aerodrom
    Zavižan


## forecast_region_name

    sredisnja
    istocna
    gorska
    unutrasnjost Dalmacije
    sjeverni Jadran
    srednji Jadran
    juzni Jadran
    Zagreb

## forecast_text

    rh_text
    zg_text


## forecast_station_name

    Beli_Manastir
    Bilogora
    Bjelovar
    Cavtat
    Cakovec
    Zracna_luka_Dubrovni
    Daruvar
    Delnice
    Donji_Miholjac
    Dubrovnik
    Dakovo
    Fuzine
    Glina
    Gospic
    Gracac
    Gradiste
    Hreljin
    Hrvatska_Kostajnica
    Hvar
    Ilok
    Imotski
    Karlovac
    Knin
    Komiza
    Koprivnica
    Korcula
    Krapina
    Krizevci
    Krk
    Lastovo
    Mali_Losinj
    Makarska
    Maslenica
    Metkovic
    Korita-NP_Mljet
    Most_Krk
    Nasice
    Nin
    Nova_Gradiska
    Novska
    Ogulin
    Orebic
    Osijek
    Pag
    Palagruza
    cabar
    Pazin
    NP_Plitvicka_jezera
    Ploce
    Pokupsko
    Porec
    Pozega
    Pula
    Rab
    Rijeka
    Rovinj
    Rupa
    Senj
    Sinj
    Sisak
    Slatina
    Slavonski_Brod
    Slunj
    Split
    Sibenik
    Udbina
    Varazdin
    Vela_Luka
    Vinkovci
    Virovitica
    Vukovar
    Zadar
    Zagreb_Maksimir
    Zavizan
    Zracna_luka_Zadar
