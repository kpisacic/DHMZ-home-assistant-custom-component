const locale = {
    en: {
      tempHi: "Temperature",
      tempLo: "Temperature night",
      precip: "Precipitations",
      uPress: "hPa",
      uSpeed: "km/h",
      uPrecip: "mm"
    },
    hr: {
      tempHi: "Temperatura",
      tempLo: "Najniža temperatura",
      precip: "Padaline",
      uPress: "hPa",
      uSpeed: "km/h",
      uPrecip: "mm"
    }
  };
  
class DhmzWeatherCard extends Polymer.Element {
  
    static get template() {
      return Polymer.html`
        <style>
          ha-icon {
            color: var(--paper-item-icon-color);
          }
          .card {
            padding: 0 18px 18px 18px;
          }
          .main {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 60px;
            font-weight: 400;
          }
          .condition {
            display: flex;
            justify-content: space-between;
            font-size: 24px;
            font-weight: 350;
            padding-left: 10px;
          }
         .main ha-icon {
            height: 74px;
            width: 74px;
            --iron-icon-height: 74px;
            --iron-icon-width: 74px;
            margin-right: 20px;
            background-repeat: no-repeat;
            background-position: center center;
          }
          .main div {
            cursor: pointer;
          }
          .main sup {
            font-size: 32px;
          }
          .attributes {
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 10px 0px 10px 0px;
          }
          .attributes div {
            text-align: left;
          }
          .conditions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 0px 3px 0px 10px;
          }
          .conditions ha-icon {
            height: 20px;
            width: 20px;
            --iron-icon-height: 20px;
            --iron-icon-width: 20px;
            margin-right: 1px;
            margin-left: 0px;
            background-repeat: no-repeat;
            background-position: center bottom;
          }
          .forecast_text {
            display: flex;
            align-items: left;
            justify-content: space-between;
            margin: 5px 0px 5px 0px;
          }
          .forecast_text .label {
            display: flex;
            align-items: left;
            justify-content: space-between;
            font-weight: 450;
            margin: 0px 10px 0px 0px;
          }
          .forecast_text .text {
            display: flex;
            align-items: left;
            justify-content: space-between;
          }
        </style>
        <ha-card header="[[title]]">
          <div class="card">
            <div class="main">
              <ha-icon style="background-image: url([[weatherObj.attributes.entity_picture]])"></ha-icon>
                <template is="dom-if" if="[[tempObj]]">
                    <div on-click="_tempAttr">[[tempObj.state]]<sup>[[getUnit('temperature')]]</sup></div>
                </template>
                <template is="dom-if" if="[[!tempObj]]">
                    <div on-click="_weatherAttr">[[weatherObj.attributes.temperature]]<sup>[[getUnit('temperature')]]</sup></div>
                </template>
              <div class="condition">[[weatherObj.attributes.condition]]</div>
            </div>
            <div class="attributes" on-click="_weatherAttr">
              <div>
                <ha-icon icon="hass:water-percent"></ha-icon> [[weatherObj.attributes.humidity]] %<br>
                <ha-icon icon="hass:gauge"></ha-icon> [[weatherObj.attributes.pressure]] [[ll('uPress')]] ([[weatherObj.attributes.pressure_tendency]])
              </div>
              <div>
                <template is="dom-if" if="[[sunObj]]">
                  <ha-icon icon="mdi:weather-sunset-up"></ha-icon> [[computeTime(sunObj.attributes.next_rising)]]<br>
                  <ha-icon icon="mdi:weather-sunset-down"></ha-icon> [[computeTime(sunObj.attributes.next_setting)]]
                </template>
              </div>
              <div>
                <ha-icon icon="[[getWindDirIcon(windBearing)]]"></ha-icon> [[windBearing]]<br>
                <ha-icon icon="hass:weather-windy"></ha-icon> [[weatherObj.attributes.wind_speed]] [[ll('uSpeed')]]
              </div>
            </div>
            <template is="dom-if" if="[[show_today_text]]">
              <div class="forecast_text"><div class="label">Danas:</div></div>
              <div class="forecast_text"><div class="text">[[weatherObj.attributes.forecast_today]]</div></div>
            </template>
            <ha-chart-base hass="[[_hass]]" data="[[ChartData]]" options="[[ChartOptions]]" chartType="[[ChartType]]"></ha-chart-base>
            <div class="conditions">
              <template is="dom-repeat" items="[[forecast]]">
                <ha-icon class="conditions" style="background-image: url(https://meteo.hr/assets/images/icons/[[item.weather_symbol]].svg)"></ha-icon>
              </template>
            </div>
            <template is="dom-if" if="[[show_tomorrow_text]]">
              <div class="forecast_text"><div class="label">Sutra:</div></div>
              <div class="forecast_text"><div class="text">[[weatherObj.attributes.forecast_tommorow]]</div></div>
            </template>
          </div>
        </ha-card>
      `;
    }
  
    static get properties() {
      return {
        config: Object,
        sunObj: Object,
        tempObj: Object,
        mode: String,
        weatherObj: {
          type: Object,
          observer: 'dataChanged',
        },
      };
    }
  
    constructor() {
      super();
      this.mode = 'daily';
      this.weatherIcons = {
        'clear-night': 'hass:weather-night',
        'cloudy': 'hass:weather-cloudy',
        'fog': 'hass:weather-fog',
        'hail': 'hass:weather-hail',
        'lightning': 'hass:weather-lightning',
        'lightning-rainy': 'hass:weather-lightning-rainy',
        'partlycloudy': 'hass:weather-partly-cloudy',
        'pouring': 'hass:weather-pouring',
        'rainy': 'hass:weather-rainy',
        'snowy': 'hass:weather-snowy',
        'snowy-rainy': 'hass:weather-snowy-rainy',
        'sunny': 'hass:weather-sunny',
        'windy': 'hass:weather-windy',
        'windy-variant': 'hass:weather-windy-variant',
        'exceptional': 'mdi:exclamation'
      };
      this.cardinalDirectionsIcon = {
        'N': 'mdi:arrow-down', 'NE': 'mdi:arrow-bottom-left', 'E': 'mdi:arrow-left',
        'SE': 'mdi:arrow-top-left', 'S': 'mdi:arrow-up', 'SW': 'mdi:arrow-top-right',
        'W': 'mdi:arrow-right', 'NW': 'mdi:arrow-bottom-right', 'C': 'mdi:circle-outline'
      };
    }
  
    setConfig(config) {
      this.config = config;
      this.title = config.title;
      this.weatherObj = config.weather;
      this.tempObj = config.temp;
      this.mode = config.mode;
      if (!config.weather) {
        throw new Error('Please define "weather" entity in the card config');
      }
      if ( typeof(config.show_today_text) == "undefined") {
        this.show_today_text = true;
      }
      else {
        this.show_today_text = config.show_today_text;
      }
      if ( typeof(config.show_tomorrow_text) == "undefined") {
        this.show_tomorrow_text = true;
      }
      else {
        this.show_tomorrow_text = config.show_tomorrow_text;
      }
    }
  
    set hass(hass) {
      this._hass = hass;
      this.lang = this._hass.selectedLanguage || this._hass.language;
      this.weatherObj = this.config.weather in hass.states ? hass.states[this.config.weather] : null;
      this.sunObj = 'sun.sun' in hass.states ? hass.states['sun.sun'] : null;
      this.tempObj = this.config.temp in hass.states ? hass.states[this.config.temp] : null;
      var tmp_forecast = this.weatherObj.attributes.forecast.slice(0,29);
      this.forecast = [];
      for (var i = 0; i < tmp_forecast.length; i+=2) {
        this.forecast.push(tmp_forecast[i]);
      }
      this.windBearing = this.weatherObj.attributes.wind_bearing;
    }
  
    dataChanged() {
      this.drawChart();
    }
  
    roundNumber(number) {
      var rounded = Math.round(number);
      return rounded;
    }
  
    ll(str) {
      if (locale[this.lang] === undefined) {
        return locale.en[str];
      }
      return locale[this.lang][str];
    }
  
    computeTime(time) {
      const date = new Date(time);
      return date.toLocaleTimeString(this.lang,
        { hour:'2-digit', minute:'2-digit', hour12:false }
      );
    }
  
    getCardSize() {
      return 4;
    }
  
    getUnit(unit) {
      return this._hass.config.unit_system[unit] || '';
    }
  
    getWindDirIcon(direction) {
      return this.cardinalDirectionsIcon[direction];
    }
  
    drawChart() {
      var data = this.weatherObj.attributes.forecast.slice(0,29);
      var locale = this._hass.selectedLanguage || this._hass.language;
      var tempUnit = this._hass.config.unit_system.temperature;
      var lengthUnit = this._hass.config.unit_system.length;
      var precipUnit = lengthUnit === 'km' ? this.ll('uPrecip') : 'in';
      var mode = this.mode;
      var i;
      if (!this.weatherObj.attributes.forecast) {
        return [];
      }
      var dateTime = [];
      var tempHigh = [];
      var tempLow = [];
      var precip = [];
      for (i = 0; i < data.length; i++) {
        var d = data[i];
        dateTime.push(new Date(d.datetime));
        tempHigh.push(d.temperature);
        tempLow.push(d.templow);
        if ( d.precipitation == 0.0 ) {
          precip.push(null);
        }
        else {
          precip.push(d.precipitation);
        }
      }
      var style = getComputedStyle(document.body);
      var textColor = style.getPropertyValue('--primary-text-color');
      var dividerColor = style.getPropertyValue('--divider-color');
      const ChartType = 'bar';
      const chartData = {
        labels: dateTime,
        datasets: [
          {
            label: this.ll('tempHi'),
            type: 'line',
            data: tempHigh,
            xAxisID: "xAxes",
            yAxisID: 'yTempAxis',
            borderWidth: 2.0,
            lineTension: 0.4,
            pointRadius: 1.0,
            pointHitRadius: 5.0,
            borderColor: "#ff0029",
            backgroundColor: "#ff0029",
            fill: false,
            tooltip: {
              callbacks: {
                title: function(context) {
                  var label = context.dataset.label || '';
                  return label += ': ' + context.parsed.y + ' ' + tempUnit;
                },
                label: function(context) {
                  var label = context.dataset.label || '';
                  return label += ': ' + context.parsed.y + ' ' + tempUnit;
                }
              }
            }            
          },
          {
            label: this.ll('tempLo'),
            type: 'line',
            data: tempLow,
            xAxisID: "xAxes",
            yAxisID: 'yTempAxis',
            borderWidth: 2.0,
            lineTension: 0.4,
            pointRadius: 1.0,
            pointHitRadius: 5.0,
            borderColor: "#66a61e",
            backgroundColor: "#66a61e",
            fill: false,
            tooltip: {
              callbacks: {
                label: function(context) {
                  var label = context.dataset.label || '';
                  return label += ': ' + context.parsed.y + ' ' + tempUnit;
                }
              }
            }
          },
          {
            label: this.ll('precip'),
            type: 'bar',
            data: precip,
            barThickness: 8,
            maxBarThickness: 15,
            xAxisID: "xAxes",
            yAxisID: 'yPrecipAxis',
            borderColor: "#262889",
            backgroundColor: "#262889",
            tooltip: {
              callbacks: {
                label: function(context) {
                  var label = context.dataset.label || '';
                  return label += ': ' + context.parsed.y + ' ' + precipUnit;
                }
              }
            }            
          },
        ]
      };
      const chartOptions = {
        animation: false,
        legend: {
          display: false,
        },
        scales: {
          xAxes: {
            type: 'time',
            adapters: {
              date: {
                locale: this._hass.locale,
              },
            },
            display: false,
            ticks: {
              display: false,
            },
            grid: {
              display: false,
            },
          },
          xDateAxis: {
            type: 'time',
            position: 'top',
            adapters: {
              date: {
                locale: this._hass.locale,
              },
            },
            grid: {
              display: true,
              drawBorder: false,
              color: dividerColor,
            },
            ticks: {
              display: true,
              source: 'labels',
              autoSkip: true,
              fontColor: textColor,
              maxRotation: 0,
              callback: function(value, index, values) {
                var date = new Date(0);
                date.setUTCMilliseconds(values[index].value);
                if (mode == 'hourly') {
                  return date.toLocaleTimeString(locale, { weekday: 'short', hour: 'numeric', hour12:false });
                }
                return date.toLocaleDateString(locale, { weekday: 'short' });;
              },
            },
          },
          yTempAxis: {
            position: 'left',
            adapters: {
              date: {
                locale: this._hass.locale,
              },
            },
            grid: {
              display: true,
              drawBorder: false,
              color: dividerColor,
              borderDash: [1,3],
            },
            ticks: {
              display: true,
              fontColor: textColor,
            },
            afterFit: function(scaleInstance) {
              scaleInstance.width = 25;
            },
          },
          yPrecipAxis: {
            display: false,
            position: 'right',
            suggestedMax: 20,
            adapters: {
              date: {
                locale: this._hass.locale,
              },
            },
            grid: {
              display: false,
              drawBorder: false,
              color: dividerColor,
            },
            ticks: {
              display: false,
              min: 0,
              fontColor: textColor,
            },
            afterFit: function(scaleInstance) {
              scaleInstance.width = 15;
            },
          },
        },
      };
      this.ChartType = ChartType;
      this.ChartData = chartData;
      this.ChartOptions = chartOptions;
    }
  
    _fire(type, detail, options) {
      const node = this.shadowRoot;
      options = options || {};
      detail = (detail === null || detail === undefined) ? {} : detail;
      const e = new Event(type, {
        bubbles: options.bubbles === undefined ? true : options.bubbles,
        cancelable: Boolean(options.cancelable),
        composed: options.composed === undefined ? true : options.composed
      });
      e.detail = detail;
      node.dispatchEvent(e);
      return e;
    }
  
    _tempAttr() {
      this._fire('hass-more-info', { entityId: this.config.temp });
    }
  
    _weatherAttr() {
      this._fire('hass-more-info', { entityId: this.config.weather });
    }
}
  
customElements.define("dhmz-weather-card", DhmzWeatherCard);