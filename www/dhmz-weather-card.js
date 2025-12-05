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

import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@2.0.1/lit-element.js?module";

class DhmzWeatherCard extends LitElement {

  constructor() {
    super();
    this.mode = 'daily';
    this.chart = null;
    this.chartInitialized = false;
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
    if ( this.title == "undefined" ) {
      this.title = "";
    }
  }

  set hass(hass) {
    this._hass = hass;
    this.lang = this._hass.selectedLanguage || this._hass.language;
    this.weatherObj = this.config.weather in hass.states ? hass.states[this.config.weather] : null;
    this.sunObj = 'sun.sun' in hass.states ? hass.states['sun.sun'] : null;
    this.tempObj = this.config.temp in hass.states ? hass.states[this.config.temp] : null;
    
    if (this.weatherObj && this.weatherObj.attributes && this.weatherObj.attributes.forecast_list) {
      var tmp_forecast = this.weatherObj.attributes.forecast_list.slice(0,29);
      this.forecast = [];
      for (var i = 0; i < tmp_forecast.length; i+=2) {
        this.forecast.push(tmp_forecast[i]);
      }
      this.windBearing = this.weatherObj.attributes.wind_bearing;
      this.requestUpdate();
    }
  }

  get hass() {
    return this._hass;
  }

  async firstUpdated() {
    if (!this.chartInitialized) {
      await this.loadChartLibrary();
      this.chartInitialized = true;
      this.updateChart();
    }
  }

  updated(changedProperties) {
    if (this.chartInitialized && changedProperties.has('weatherObj') && this.weatherObj) {
      setTimeout(() => this.updateChart(), 50);
    }
  }

  async loadChartLibrary() {
    if (window.Chart) return;
    
    return new Promise((resolve) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js';
      script.onload = () => {
        const adapter = document.createElement('script');
        adapter.src = 'https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@2.0.0/dist/chartjs-adapter-date-fns.bundle.min.js';
        adapter.onload = () => resolve();
        adapter.onerror = () => resolve();
        document.head.appendChild(adapter);
      };
      script.onerror = () => resolve();
      document.head.appendChild(script);
    });
  }

  updateChart() {
    if (!this.shadowRoot || !window.Chart || !this.weatherObj) return;
    
    const canvas = this.shadowRoot.querySelector('#weather-chart');
    if (!canvas) return;

    const data = this.weatherObj.attributes.forecast_list?.slice(0, 29);
    if (!data || data.length === 0) return;

    const ctx = canvas.getContext('2d');
    
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }

    const style = getComputedStyle(document.body);
    const textColor = style.getPropertyValue('--primary-text-color') || '#212121';
    const dividerColor = style.getPropertyValue('--divider-color') || 'rgba(0,0,0,0.12)';

    const labels = data.map(d => new Date(d.datetime));
    const tempHigh = data.map(d => d.temperature);
    const tempLow = data.map(d => d.templow);
    const precip = data.map(d => d.precipitation || 0);
    const mode = this.mode;
    const locale = this.lang;
    const tempUnit = this._hass.config.unit_system.temperature;
    const precipUnit = this._hass.config.unit_system.length === 'km' ? 'mm' : 'in';

    // Create gradients
    const gradientHigh = ctx.createLinearGradient(0, 0, 0, 150);
    gradientHigh.addColorStop(0, 'rgba(255, 99, 132, 0.3)');
    gradientHigh.addColorStop(1, 'rgba(255, 99, 132, 0.0)');

    const gradientLow = ctx.createLinearGradient(0, 0, 0, 150);
    gradientLow.addColorStop(0, 'rgba(75, 192, 192, 0.3)');
    gradientLow.addColorStop(1, 'rgba(75, 192, 192, 0.0)');

    this.chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: this.ll('tempHi'),
            type: 'line',
            data: tempHigh,
            borderColor: "#ff6384",
            backgroundColor: gradientHigh,
            borderWidth: 2.5,
            tension: 0.4,
            pointRadius: 2,
            pointBackgroundColor: "#ff6384",
            pointBorderColor: "#fff",
            pointBorderWidth: 2,
            pointHoverRadius: 5,
            pointHoverBackgroundColor: "#ff6384",
            pointHoverBorderColor: "#fff",
            pointHoverBorderWidth: 2,
            fill: false,
            yAxisID: 'yTempAxis'
          },
          {
            label: this.ll('tempLo'),
            type: 'line',
            data: tempLow,
            borderColor: "#4bc0c0",
            backgroundColor: gradientLow,
            borderWidth: 2.5,
            tension: 0.4,
            pointRadius: 3,
            pointBackgroundColor: "#4bc0c0",
            pointBorderColor: "#fff",
            pointBorderWidth: 2,
            pointHoverRadius: 5,
            pointHoverBackgroundColor: "#4bc0c0",
            pointHoverBorderColor: "#fff",
            pointHoverBorderWidth: 2,
            fill: true,
            yAxisID: 'yTempAxis'
          },
          {
            label: this.ll('precip'),
            type: 'bar',
            data: precip,
            backgroundColor: "rgba(54, 162, 235, 0.6)",
            borderColor: "#36a2eb",
            borderWidth: 0,
            borderRadius: 4,
            yAxisID: 'yPrecipAxis'
          }
        ]
      },
      options: {
        animation: false,
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#fff',
            bodyColor: '#fff',
            borderColor: dividerColor,
            borderWidth: 1,
            padding: 12,
            displayColors: true,
            usePointStyle: true,
            callbacks: {
              title: function(context) {
                const date = new Date(context[0].parsed.x);
                if (mode == 'hourly') {
                  return date.toLocaleTimeString(locale, { weekday: 'short', hour: 'numeric', hour12:false });
                }
                return date.toLocaleDateString(locale, { weekday: 'short', month: 'short', day: 'numeric' });
              },
              label: function(context) {
                let label = context.dataset.label || '';
                if (label) label += ': ';
                label += context.parsed.y;
                if (context.datasetIndex < 2) {
                  label += ' ' + tempUnit;
                } else {
                  label += ' ' + precipUnit;
                }
                return label;
              }
            }
          }
        },
        scales: {
          x: {
            type: 'time',
            position: 'top',
            time: {
              unit: mode === 'hourly' ? 'hour' : 'day',
              displayFormats: {
                hour: 'ccc HH:mm',
                day: 'ccc'
              }
            },
            grid: {
              display: true,
              drawBorder: false,
              color: dividerColor,
            },
            ticks: {
              display: true,
              autoSkip: true,
              color: textColor,
              maxRotation: 0,
            }
          },
          yTempAxis: {
            position: 'left',
            grid: {
              display: true,
              drawBorder: false,
              color: dividerColor,
              borderDash: [1,3],
            },
            ticks: {
              display: true,
              color: textColor,
            },
            afterFit: function(scaleInstance) {
              scaleInstance.width = 25;
            }
          },
          yPrecipAxis: {
            display: false,
            position: 'right',
            suggestedMax: 20,
            grid: {
              display: false,
              drawBorder: false,
            },
            ticks: {
              display: false,
              min: 0,
            },
            afterFit: function(scaleInstance) {
              scaleInstance.width = 15;
            }
          }
        }
      }
    });
  }

  static get styles() {
    return css`
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
          margin: 5px 0px 5px 0px;
        }
        .attributes div {
          text-align: left;
          font-size: 12px;
        }
        .chart-container {
          margin: 10px 0;
          height: 150px;
          width: 100%;
          position: relative;
        }
        #weather-chart {
          width: 100% !important;
          height: 100% !important;
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
    `;
  }

  render() {
    if (!this.weatherObj || !this.weatherObj.attributes) {
      return html`<ha-card header="${this.title}"><div class="card">Loading...</div></ha-card>`;
    }

    return html`
        <ha-card header="${this.title}">
          <div class="card">
            <div class="main">
              <ha-icon style="background-image: url(${this.weatherObj.attributes.entity_picture})"></ha-icon>
              <div @click=${this._weatherAttr}>${this.weatherObj.attributes.temperature}<sup>${this.getUnit('temperature')}</sup></div>
              <div class="condition">${this.weatherObj.attributes.condition}</div>
            </div>
            <div class="attributes" @click=${this._weatherAttr}>
              <div>
                <ha-icon icon="hass:water-percent"></ha-icon> ${this.weatherObj.attributes.humidity} %<br>
                <ha-icon icon="mdi:weather-pouring"></ha-icon> ${this.weatherObj.attributes.precipitation} ${this.ll('uPrecip')}
              </div>
              <div>
                <ha-icon icon="hass:gauge"></ha-icon> ${this.weatherObj.attributes.pressure} ${this.ll('uPress')} (${this.weatherObj.attributes.pressure_tendency})<br>
                ${ this.sunObj ?  
                  html `<ha-icon icon="mdi:weather-sunset-up"></ha-icon> ${this.computeTime(this.sunObj.attributes.next_rising)} - ${this.computeTime(this.sunObj.attributes.next_setting)}`
                  : html ``
                }
              </div>
              <div>
                <ha-icon icon="${this.getWindDirIcon(this.windBearing)}"></ha-icon> ${this.windBearing}<br>
                <ha-icon icon="hass:weather-windy"></ha-icon> ${this.weatherObj.attributes.wind_speed} ${this.ll('uSpeed')}
              </div>
            </div>
            ${ this.show_today_text ?
              html `<div class="forecast_text"><div class="label">Danas:</div></div>
              <div class="forecast_text"><div class="text">${this.weatherObj.attributes.forecast_today}</div></div>`
              : html ``
            }
            <div class="chart-container">
              <canvas id="weather-chart"></canvas>
            </div>
            <div class="conditions">
            ${this.forecast ? this.forecast.map(one_forecast => 
                html `<ha-icon class="conditions" style="background-image: url(https://meteo.hr/assets/images/icons/${one_forecast.weather_symbol}.svg)"></ha-icon>`
            ) : ''}
            </div>
            ${ this.show_tomorrow_text ?
              html `<div class="forecast_text"><div class="label">Sutra:</div></div>
              <div class="forecast_text"><div class="text">${this.weatherObj.attributes.forecast_tommorow}</div></div>`
              : html ``
            }
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
          hasChanged: function(newVal, oldVal) {
            return JSON.stringify(newVal) !== JSON.stringify(oldVal);
          }
        }
      };
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
