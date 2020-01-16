const locale = {
    en: {
      tempHi: "Temperature",
      tempLo: "Temperature night",
      precip: "Precipitations",
      uPress: "hPa",
      uSpeed: "m/s",
      uPrecip: "mm"
    },
    hr: {
      tempHi: "Temperatura",
      tempLo: "Najniža temperatura",
      precip: "Padaline",
      uPress: "hPa",
      uSpeed: "m/s",
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
            align-items: right;
            justify-content: space-between;
            font-size: 24px;
            font-weight: 350;
          }
          .main ha-icon {
            --iron-icon-height: 74px;
            --iron-icon-width: 74px;
            margin-right: 20px;
          }
          .main div {
            cursor: pointer;
            margin-top: -11px;
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
            --iron-icon-height: 28px;
            --iron-icon-width: 28px;
            margin-right: 1px;
          }
          .forecast_text {
            display: flex;
            align-items: left;
            justify-content: space-between;
            margin: 10px 0px 10px 0px;
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
            <div class="forecast_text"><div class="label">Today:</div><div class="text">[[weatherObj.attributes.forecast_today]]</div></div>
            <ha-chart-base data="[[ChartData]]"></ha-chart-base>
            <div class="conditions">
              <template is="dom-repeat" items="[[forecast]]">
                <div>
                  <ha-icon style="background-image: url(https://meteo.hr/assets/images/icons/[[item.weather_symbol]].svg)"></ha-icon>
                </div>
              </template>
            </div>
            <div class="forecast_text"><div class="label">Tommorow:</div><div class="text">[[weatherObj.attributes.forecast_tommorow]]</div></div>
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
      if (locale[this.lang] === undefined)
        return locale.en[str];
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
      const chartOptions = {
        type: 'bar',
        data: {
          labels: dateTime,
          datasets: [
            {
              label: this.ll('tempHi'),
              type: 'line',
              data: tempHigh,
              yAxisID: 'TempAxis',
              borderWidth: 2.0,
              lineTension: 0.4,
              pointRadius: 0.0,
              pointHitRadius: 5.0,
              fill: false,
            },
            {
              label: this.ll('tempLo'),
              type: 'line',
              data: tempLow,
              yAxisID: 'TempAxis',
              borderWidth: 2.0,
              lineTension: 0.4,
              pointRadius: 0.0,
              pointHitRadius: 5.0,
              fill: false,
            },
            {
              label: this.ll('precip'),
              type: 'bar',
              data: precip,
              yAxisID: 'PrecipAxis',
            },
          ]
        },
        options: {
          animation: {
            duration: 300,
            easing: 'linear',
            onComplete: function () {
              var chartInstance = this.chart,
                ctx = chartInstance.ctx;
              ctx.fillStyle = textColor;
              var fontSize = 10;
              var fontStyle = 'normal';
              var fontFamily = 'Roboto';
              ctx.font = Chart.helpers.fontString(fontSize, fontStyle, fontFamily);
              ctx.textAlign = 'center';
              ctx.textBaseline = 'bottom';
              var meta = chartInstance.controller.getDatasetMeta(2);
              meta.data.forEach(function (bar, index) {
                var data = (Math.round((chartInstance.data.datasets[2].data[index]) * 10) / 10).toFixed(1);
                ctx.fillText(data, bar._model.x, bar._model.y - 5);
              });
            },
          },
          legend: {
            display: false,
          },
          scales: {
            xAxes: [{
              type: 'time',
              maxBarThickness: 15,
              display: false,
              ticks: {
                display: false,
              },
              gridLines: {
                display: false,
              },
            },
            {
              id: 'DateAxis',
              position: 'top',
              gridLines: {
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
                  var data = new Date(value).toLocaleDateString(locale,
                    { weekday: 'short' });
                  var time = new Date(value).toLocaleTimeString(locale,
                    { weekday: 'short', hour: 'numeric', hour12:false });
                  if (mode == 'hourly') {
                    return time || "h";
                  }
                  return data;
                },
              },
            }],
            yAxes: [{
              id: 'TempAxis',
              position: 'left',
              gridLines: {
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
                scaleInstance.width = 28;
              },
            },
            {
              id: 'PrecipAxis',
              position: 'right',
              gridLines: {
                display: false,
                drawBorder: false,
                color: dividerColor,
              },
              ticks: {
                display: false,
                min: 0,
                suggestedMax: 20,
                fontColor: textColor,
              },
              afterFit: function(scaleInstance) {
                scaleInstance.width = 15;
              },
            }],
          },
          tooltips: {
            mode: 'index',
            callbacks: {
              title: function (items, data) {
                const item = items[0];
                const date = data.labels[item.index];
                return new Date(date).toLocaleDateString(locale, {
                  month: 'long',
                  day: 'numeric',
                  weekday: 'long',
                  hour: 'numeric',
                  minute: 'numeric',
                  hour12: false,
                });
              },
              label: function(tooltipItems, data) {
                var label = data.datasets[tooltipItems.datasetIndex].label || '';
                if (data.datasets[2].label == label) {
                  return label + ': ' + (tooltipItems.yLabel ?
                    (tooltipItems.yLabel + ' ' + precipUnit) : ('0 ' + precipUnit));
                }
                return label + ': ' + tooltipItems.yLabel + ' ' + tempUnit;
              },
            },
          },
        },
      };
      this.ChartData = chartOptions;
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