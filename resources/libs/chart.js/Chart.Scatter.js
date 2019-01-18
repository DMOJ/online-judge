// From https://github.com/dima117/Chart.Scatter

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(['Chart'], factory);
    } else if (typeof exports === 'object') {
        // Node. Does not work with strict CommonJS, but
        // only CommonJS-like environments that support module.exports,
        // like Node.
        factory(require('Chart'));
    } else {
        // Browser globals (root is window)
        factory(root.Chart);
    }
}(this, function (chartjs) {
    "use strict";

    var helpers = chartjs.helpers,
        hlp = {
            formatDateValue: function (date, tFormat, dFormat, useUtc) {
                date = new Date(+date);

                var ms = useUtc ? date.getUTCMilliseconds() : date.getMilliseconds();

                if (ms) {
                    return ('000' + ms).slice(-3);
                }

                var hasTime = useUtc
                    ? date.getUTCHours() + date.getUTCMinutes() + date.getUTCSeconds()
                    : date.getHours() + date.getMinutes() + date.getSeconds();

                if (hasTime) {
                    return dateFormat(date, tFormat || "h:MM", useUtc);
                } else {
                    return dateFormat(date, dFormat || "mmm d", useUtc);
                }
            },

            getElementOrDefault: function (array, index, defaultValue) {
                return index >= 0 && index < array.length
                    ? array[index]
                    : defaultValue;
            },

            applyRange: function (value, min, max) {
                return value > max ? max
                    : value < min ? min
                    : value;
            },

            calculateFixedScaleRange: function (startValue, steps, stepWidth) {
                return {
                    steps: steps,
                    stepValue: stepWidth,
                    min: startValue,
                    max: startValue + (steps * stepWidth)
                };
            },

            ScatterPoint: chartjs.Point.extend({
                inRange: function (chartX, chartY) {
                    var hitDetectionRange = this.hitDetectionRadius + this.radius * this.size;
                    return ((Math.pow(chartX - this.x, 2) + Math.pow(chartY - this.y, 2)) < Math.pow(hitDetectionRange, 2));
                },

                draw: function () {
                    if (this.display && this.size > 0) {
                        var ctx = this.ctx;
                        ctx.beginPath();

                        ctx.arc(this.x, this.y, this.size * this.radius, 0, Math.PI * 2);
                        ctx.closePath();

                        ctx.strokeStyle = this.strokeColor;
                        ctx.lineWidth = this.strokeWidth;

                        ctx.fillStyle = this.fillColor;

                        ctx.fill();
                        ctx.stroke();
                    }
                }
            })
        };

    var dateFormat = function () {
        var token = /d{1,4}|m{1,4}|yy(?:yy)?|([HhMsTt])\1?|[LloSZ]|"[^"]*"|'[^']*'/g,
            timezone = /\b(?:[PMCEA][SDP]T|(?:Pacific|Mountain|Central|Eastern|Atlantic) (?:Standard|Daylight|Prevailing) Time|(?:GMT|UTC)(?:[-+]\d{4})?)\b/g,
            timezoneClip = /[^-+\dA-Z]/g,
            pad = function (val, len) {
                val = String(val);
                len = len || 2;
                while (val.length < len) val = "0" + val;
                return val;
            },
            masks = {
                "default": "ddd mmm dd yyyy HH:MM:ss"
            },
            i18n = {
                dayNames: [
                    "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat",
                    "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
                ],
                monthNames: [
                    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
                    "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"
                ]
            };


        // Regexes and supporting functions are cached through closure
        return function (date, mask, utc) {
            // You can't provide utc if you skip other args (use the "UTC:" mask prefix)
            if (arguments.length == 1 && Object.prototype.toString.call(date) == "[object String]" && !/\d/.test(date)) {
                mask = date;
                date = undefined;
            }

            // Passing date through Date applies Date.parse, if necessary
            date = date ? new Date(date) : new Date;
            if (isNaN(date)) throw SyntaxError("invalid date");

            mask = String(masks[mask] || mask || masks["default"]);

            // Allow setting the utc argument via the mask
            if (mask.slice(0, 4) == "UTC:") {
                mask = mask.slice(4);
                utc = true;
            }

            var _ = utc ? "getUTC" : "get",
                d = date[_ + "Date"](),
                D = date[_ + "Day"](),
                m = date[_ + "Month"](),
                y = date[_ + "FullYear"](),
                H = date[_ + "Hours"](),
                M = date[_ + "Minutes"](),
                s = date[_ + "Seconds"](),
                L = date[_ + "Milliseconds"](),
                o = utc ? 0 : date.getTimezoneOffset(),
                flags = {
                    d: d,
                    dd: pad(d),
                    ddd: i18n.dayNames[D],
                    dddd: i18n.dayNames[D + 7],
                    m: m + 1,
                    mm: pad(m + 1),
                    mmm: i18n.monthNames[m],
                    mmmm: i18n.monthNames[m + 12],
                    yy: String(y).slice(2),
                    yyyy: y,
                    h: H % 12 || 12,
                    hh: pad(H % 12 || 12),
                    H: H,
                    HH: pad(H),
                    M: M,
                    MM: pad(M),
                    s: s,
                    ss: pad(s),
                    l: pad(L, 3),
                    L: pad(L > 99 ? Math.round(L / 10) : L),
                    t: H < 12 ? "a" : "p",
                    tt: H < 12 ? "am" : "pm",
                    T: H < 12 ? "A" : "P",
                    TT: H < 12 ? "AM" : "PM",
                    Z: utc ? "UTC" : (String(date).match(timezone) || [""]).pop().replace(timezoneClip, ""),
                    o: (o > 0 ? "-" : "+") + pad(Math.floor(Math.abs(o) / 60) * 100 + Math.abs(o) % 60, 4),
                    S: ["th", "st", "nd", "rd"][d % 10 > 3 ? 0 : (d % 100 - d % 10 != 10) * d % 10]
                };

            return mask.replace(token, function ($0) {
                return $0 in flags ? flags[$0] : $0.slice(1, $0.length - 1);
            });
        };
    }();

    var defaultConfig = {
        // INHERIT
        // showScale: true,							// Boolean - If we should show the scale at all
        // scaleLineColor: "rgba(0,0,0,.1)",		// String - Colour of the scale line
        // scaleLineWidth: 1,						// Number - Pixel width of the scale line
        // scaleShowLabels: true,					// Boolean - Whether to show labels on the scale
        // scaleLabel: "<%=value%>",				// Interpolated JS string - can access value
        scaleArgLabel: "<%=value%>",				// Interpolated JS string - can access value
        scaleSizeLabel: "<%=value%>",				// Interpolated JS string - can access value

        emptyDataMessage: "chart has no data",		// String - Message for empty data

        // SCALE
        scaleShowGridLines: true,				//Boolean - Whether grid lines are shown across the chart
        scaleGridLineWidth: 1,					//Number - Width of the grid lines
        scaleGridLineColor: "rgba(0,0,0,.05)",	//String - Colour of the grid lines
        scaleShowHorizontalLines: true,			//Boolean - Whether to show horizontal lines (except X axis)
        scaleShowVerticalLines: true,			//Boolean - Whether to show vertical lines (except Y axis)

        // DATE SCALE
        scaleType: "number",
        useUtc: true,
        scaleDateFormat: "mmm d",
        scaleTimeFormat: "h:MM",
        scaleDateTimeFormat: "mmm d, yyyy, hh:MM",

        // LINES
        datasetStroke: true,				// Boolean - Whether to show a stroke for datasets
        datasetStrokeWidth: 2,				// Number - Pixel width of dataset stroke
        datasetStrokeColor: '#007ACC',		// String - Color of dataset stroke
        datasetPointStrokeColor: 'white',	// String - Color of dataset stroke

        bezierCurve: true,				// Boolean - Whether the line is curved between points
        bezierCurveTension: 0.4,		// Number - Tension of the bezier curve between points


        // POINTS
        pointDot: true,					// Boolean - Whether to show a dot for each point
        pointDotStrokeWidth: 1,			// Number - Pixel width of point dot stroke
        pointDotRadius: 4,				// Number - Radius of each point dot in pixels
        pointHitDetectionRadius: 4,		// Number - amount extra to add to the radius to cater for hit detection outside the drawn point


        multiTooltipTemplate: "<%=argLabel%>; <%=valueLabel%>",
        tooltipTemplate: "<%if (datasetLabel){%><%=datasetLabel%>: <%}%><%=argLabel%>; <%=valueLabel%>",
        legendTemplate: "<ul class=\"<%=name.toLowerCase()%>-legend\"><%for(var i=0;i<datasets.length;i++){%><li><span class=\"<%=name.toLowerCase()%>-legend-marker\" style=\"background-color:<%=datasets[i].strokeColor%>\"></span><%=datasets[i].label%></li><%}%></ul>"
    };

    chartjs.ScatterNumberScale = chartjs.Element.extend({
        initialize: function () {
            // this.dataRange - минимальные и максимальные значения данных

            // инициализируем настройки
            // рассчитываем вспомогательные параметры

            this.font = helpers.fontString(this.fontSize, this.fontStyle, this.fontFamily);
            this.padding = this.fontSize / 2;
        },

        setDataRange: function (dataRange) {
            this.dataRange = dataRange;
        },

        api: {
            calculateControlPoints: function (prev, current, next, range, tension) {
                var tensionBefore = !!prev ? tension : 0;
                var tensionAfter = !!next ? tension : 0;

                var innerCurrent = current;
                var innerPrev = prev ? prev : current;
                var innerNext = next ? next : current;

                var a = {xx: innerCurrent.arg - innerPrev.arg, yy: innerCurrent.value - innerPrev.value}
                var b = {xx: innerNext.arg - innerPrev.arg, yy: innerNext.value - innerPrev.value}

                var mul = a.xx * b.xx + a.yy * b.yy;
                var mod = Math.sqrt(b.xx * b.xx + b.yy * b.yy);

                var k = Math.min(Math.max(mul / (mod * mod), 0.3), 0.7);

                var result = {
                    before: {
                        x: innerCurrent.arg - b.xx * k * tensionBefore,
                        y: innerCurrent.value - b.yy * k * tensionBefore
                    },
                    after: {
                        x: innerCurrent.arg + b.xx * (1 - k) * tensionAfter,
                        y: innerCurrent.value + b.yy * (1 - k) * tensionAfter
                    }
                };

                // Cap inner bezier handles to the upper/lower scale bounds
                result.before.y = hlp.applyRange(result.before.y, range.ymin, range.ymax);
                result.after.y = hlp.applyRange(result.after.y, range.ymin, range.ymax);

                return result;
            },

            generateLabels: function (templateString, numberOfSteps, graphMin, stepValue) {
                var labelsArray = new Array(numberOfSteps + 1),
                    stepDecimalPlaces = helpers.getDecimalPlaces(stepValue);

                if (templateString) {
                    helpers.each(labelsArray, function (val, index) {
                        labelsArray[index] = helpers.template(templateString, {value: (graphMin + (stepValue * (index))).toFixed(stepDecimalPlaces)});

                    });
                }
                return labelsArray;
            }
        },

        calculateYscaleRange: function () {
            if (this.scaleOverride) {
                this.yScaleRange = hlp.calculateFixedScaleRange(
                    this.scaleStartValue,
                    this.scaleSteps,
                    this.scaleStepWidth);
            } else {
                this.yScaleRange = helpers.calculateScaleRange(
                    [this.dataRange.ymin, this.dataRange.ymax],
                    this.chart.height,
                    this.fontSize,
                    this.beginAtZero,	// beginAtZero,
                    this.integersOnly); // integersOnly
            }
        },

        calculateXscaleRange: function () {
            if (this.xScaleOverride) {
                this.xScaleRange = hlp.calculateFixedScaleRange(
                    this.xScaleStartValue,
                    this.xScaleSteps,
                    this.xScaleStepWidth);
            } else {
                this.xScaleRange = helpers.calculateScaleRange(
                    [this.dataRange.xmin, this.dataRange.xmax],
                    this.chart.width,
                    this.fontSize,
                    false,	// beginAtZero,
                    true); // integersOnly
            }
        },

        generateYLabels: function () {
            this.yLabels = this.api.generateLabels(
                this.labelTemplate,
                this.yScaleRange.steps,
                this.yScaleRange.min,
                this.yScaleRange.stepValue);
        },

        generateXLabels: function () {
            this.xLabels = this.api.generateLabels(
                this.argLabelTemplate,
                this.xScaleRange.steps,
                this.xScaleRange.min,
                this.xScaleRange.stepValue);
        },

        argToString: function (arg) {
            return +arg + "";
        },

        fit: function () {
            // labels & padding
            this.calculateYscaleRange();
            this.calculateXscaleRange();
            this.generateYLabels();
            this.generateXLabels();

            var xLabelMaxWidth = helpers.longestText(this.chart.ctx, this.font, this.xLabels);
            var yLabelMaxWidth = helpers.longestText(this.chart.ctx, this.font, this.yLabels);

            this.xPadding = this.display && this.showLabels
                ? yLabelMaxWidth + this.padding * 2
                : this.padding;

            var xStepWidth = Math.floor((this.chart.width - this.xPadding) / this.xScaleRange.steps);
            var xLabelHeight = this.fontSize * 1.5;
            this.xLabelRotation = xLabelMaxWidth > xStepWidth;

            this.xPaddingRight = this.display && this.showLabels && !this.xLabelRotation
                ? xLabelMaxWidth / 2
                : this.padding;

            this.yPadding = this.display && this.showLabels
                ? (this.xLabelRotation ? xLabelMaxWidth : xLabelHeight) + this.padding * 2
                : this.padding;
        },

        updateBezierControlPoints: function (dataSetPoints, ease, tension) {
            for (var i = 0; i < dataSetPoints.length; i++) {
                var current = hlp.getElementOrDefault(dataSetPoints, i);
                var prev = hlp.getElementOrDefault(dataSetPoints, i - 1);
                var next = hlp.getElementOrDefault(dataSetPoints, i + 1);

                var obj = this.api.calculateControlPoints(prev, current, next, this.dataRange, tension);

                current.controlPoints = {
                    x1: this.calculateX(obj.before.x),
                    y1: this.calculateY(obj.before.y, ease),

                    x2: this.calculateX(obj.after.x),
                    y2: this.calculateY(obj.after.y, ease)
                };
            }
        },

        updatePoints: function (dataSetPoints, ease) {
            for (var i = 0; i < dataSetPoints.length; i++) {
                var current = dataSetPoints[i];

                current.x = this.calculateX(current.arg);
                current.y = this.calculateY(current.value, ease);
            }
        },

        calculateX: function (x) {
            return this.xPadding + ((x - this.xScaleRange.min) * (this.chart.width - this.xPadding - this.xPaddingRight) / (this.xScaleRange.max - this.xScaleRange.min));
        },
        calculateY: function (y, ease) {
            return this.chart.height - this.yPadding - ((y - this.yScaleRange.min) * (this.chart.height - this.yPadding - this.padding) / (this.yScaleRange.max - this.yScaleRange.min)) * (ease || 1);
        },

        draw: function () {
            var ctx = this.chart.ctx, value, index;

            if (this.display) {
                var xpos1 = this.calculateX(this.xScaleRange.min);
                var xpos2 = this.chart.width;
                var ypos1 = this.calculateY(this.yScaleRange.min);
                var ypos2 = 0;

                // y axis
                for (index = 0, value = this.yScaleRange.min;
                     index <= this.yScaleRange.steps;
                     index++, value += this.yScaleRange.stepValue) {
                    var ypos = this.calculateY(value);

                    if (this.showLabels || this.showHorizontalLines) {
                        // line color
                        ctx.lineWidth = index == 0 ? this.lineWidth : this.gridLineWidth;
                        ctx.strokeStyle = index == 0 ? this.lineColor : this.gridLineColor;

                        ctx.beginPath();
                        ctx.moveTo(xpos1 - this.padding, ypos);
                        ctx.lineTo(this.showHorizontalLines || index == 0 ? xpos2 : xpos1, ypos);
                        ctx.stroke();
                    }

                    // labels
                    if (this.showLabels) {
                        ctx.lineWidth = this.lineWidth;
                        ctx.strokeStyle = this.lineColor;

                        // text
                        ctx.textAlign = "right";
                        ctx.textBaseline = "middle";
                        ctx.font = this.font;
                        ctx.fillStyle = this.textColor;
                        ctx.fillText(this.yLabels[index], xpos1 - this.padding * 1.4, ypos);
                    }
                }

                // x axis
                for (index = 0, value = this.xScaleRange.min;
                     index <= this.xScaleRange.steps;
                     index++, value += this.xScaleRange.stepValue) {
                    var xpos = this.calculateX(value);

                    if (this.showLabels || this.showVerticalLines) {
                        // line color
                        ctx.lineWidth = index == 0 ? this.lineWidth : this.gridLineWidth;
                        ctx.strokeStyle = index == 0 ? this.lineColor : this.gridLineColor;

                        ctx.beginPath();
                        ctx.moveTo(xpos, ypos1 + this.padding);
                        ctx.lineTo(xpos, this.showVerticalLines || index == 0 ? ypos2 : ypos1);
                        ctx.stroke();
                    }

                    // labels
                    if (this.showLabels) {
                        ctx.lineWidth = this.lineWidth;
                        ctx.strokeStyle = this.lineColor;

                        // text
                        ctx.save();
                        ctx.translate(xpos, ypos1 + (this.padding * 1.4));
                        ctx.rotate(this.xLabelRotation ? -Math.PI / 2 : 0);
                        ctx.textAlign = (this.xLabelRotation) ? "right" : "center";
                        ctx.textBaseline = (this.xLabelRotation) ? "middle" : "top";
                        ctx.font = this.font;
                        ctx.fillStyle = this.textColor;
                        ctx.fillText(this.xLabels[index], 0, 0);
                        ctx.restore();
                    }
                }
            }
        }
    });

    chartjs.ScatterDateScale = chartjs.ScatterNumberScale.extend({
        _calculateDateScaleRange: function (valueMin, valueMax, drawingSize, fontSize) {
            // todo: move to global object
            var units = [
                {u: 1, c: 1, t: 1, n: 'ms'},
                {u: 1, c: 2, t: 2, n: 'ms'},
                {u: 1, c: 5, t: 5, n: 'ms'},
                {u: 1, c: 10, t: 10, n: 'ms'},
                {u: 1, c: 20, t: 20, n: 'ms'},
                {u: 1, c: 50, t: 50, n: 'ms'},
                {u: 1, c: 100, t: 100, n: 'ms'},
                {u: 1, c: 200, t: 200, n: 'ms'},
                {u: 1, c: 500, t: 500, n: 'ms'},
                {u: 1000, c: 1, t: 1000, n: 's'},
                {u: 1000, c: 2, t: 2000, n: 's'},
                {u: 1000, c: 5, t: 5000, n: 's'},
                {u: 1000, c: 10, t: 10000, n: 's'},
                {u: 1000, c: 15, t: 15000, n: 's'},
                {u: 1000, c: 20, t: 20000, n: 's'},
                {u: 1000, c: 30, t: 30000, n: 's'},
                {u: 60000, c: 1, t: 60000, n: 'm'},
                {u: 60000, c: 2, t: 120000, n: 'm'},
                {u: 60000, c: 5, t: 300000, n: 'm'},
                {u: 60000, c: 10, t: 600000, n: 'm'},
                {u: 60000, c: 15, t: 900000, n: 'm'},
                {u: 60000, c: 20, t: 1200000, n: 'm'},
                {u: 60000, c: 30, t: 1800000, n: 'm'},
                {u: 3600000, c: 1, t: 3600000, n: 'h'},
                {u: 3600000, c: 2, t: 7200000, n: 'h'},
                {u: 3600000, c: 3, t: 10800000, n: 'h'},
                {u: 3600000, c: 4, t: 14400000, n: 'h'},
                {u: 3600000, c: 6, t: 21600000, n: 'h'},
                {u: 3600000, c: 8, t: 28800000, n: 'h'},
                {u: 3600000, c: 12, t: 43200000, n: 'h'},
                {u: 86400000, c: 1, t: 86400000, n: 'd'},
                {u: 86400000, c: 2, t: 172800000, n: 'd'},
                {u: 86400000, c: 4, t: 345600000, n: 'd'},
                {u: 86400000, c: 5, t: 432000000, n: 'd'},
                {u: 604800000, c: 1, t: 604800000, n: 'w'}];

            var maxSteps = drawingSize / (fontSize * 3.3);

            // fix https://github.com/dima117/Chart.Scatter/issues/31
            valueMax === valueMin && (valueMax++);

            var valueRange = +valueMax - valueMin,
                offset = this.useUtc ? 0 : new Date().getTimezoneOffset() * 60000,
                min = +valueMin - offset,
                max = +valueMax - offset;

            var xp = 0, f = [2, 3, 5, 7, 10];

            while (valueRange / units[xp].t > maxSteps) {
                xp++;

                if (xp == units.length) {
                    var last = units[units.length - 1];
                    for (var fp = 0; fp < f.length; fp++) {
                        units.push({
                            u: last.u,
                            c: last.c * f[fp],
                            t: last.c * f[fp] * last.u,
                            n: last.n
                        });
                    }
                }
            }

            var stepValue = units[xp].t,
                start = Math.floor(min / stepValue) * stepValue,
                stepCount = Math.ceil((max - start) / stepValue),
                end = start + stepValue * stepCount;

            return {
                min: start + offset,
                max: end + offset,
                steps: stepCount,
                stepValue: stepValue
            };
        },

        calculateXscaleRange: function () {
            if (this.xScaleOverride) {
                this.xScaleRange = hlp.calculateFixedScaleRange(
                    this.xScaleStartValue,
                    this.xScaleSteps,
                    this.xScaleStepWidth);
            } else {
                this.xScaleRange = this._calculateDateScaleRange(
                    this.dataRange.xmin,
                    this.dataRange.xmax,
                    this.chart.width,
                    this.fontSize
                );
            }
        },

        argToString: function (arg) {
            return dateFormat(+arg, this.dateTimeFormat, this.useUtc);
        },

        generateXLabels: function () {
            var graphMin = this.xScaleRange.min,
                stepValue = this.xScaleRange.stepValue,
                labelsArray = new Array(this.xScaleRange.steps + 1);

            helpers.each(labelsArray, function (val, index) {
                var value = graphMin + stepValue * index;

                labelsArray[index] = hlp.formatDateValue(value, this.timeFormat, this.dateFormat, this.useUtc);
            }, this);

            this.xLabels = labelsArray;
        }
    });

    chartjs.ScatterDataSet = (function () {
        var datasetCtr = function (datasetOptions, chartOptions, chart, scale) {
            this.chart = chart;
            this.scale = scale;

            this.label = datasetOptions.label || null;
            this.strokeColor = datasetOptions.strokeColor || chartOptions.datasetStrokeColor;
            this.pointColor = datasetOptions.pointColor || datasetOptions.strokeColor || chartOptions.datasetStrokeColor;
            this.pointStrokeColor = datasetOptions.pointStrokeColor || chartOptions.datasetPointStrokeColor;

            this.pointDot = chartOptions.pointDot;
            this.pointDotRadius = chartOptions.pointDotRadius;
            this.pointHitDetectionRadius = chartOptions.pointHitDetectionRadius;
            this.pointDotStrokeWidth = chartOptions.pointDotStrokeWidth;

            this.scaleArgLabel = chartOptions.scaleArgLabel;
            this.scaleLabel = chartOptions.scaleLabel;
            this.scaleSizeLabel = chartOptions.scaleSizeLabel;

            this.points = [];
        };

        datasetCtr.prototype.addPoint = function (x, y, r) {
            // default size
            r = arguments.length < 3 ? 1 : r;

            var point = this._createNewPoint();
            this._setPointData(point, x, y, r);
            this.points.push(point);
        };

        datasetCtr.prototype.setPointData = function (index, x, y, r) {
            // default size
            r = arguments.length < 4 ? 1 : r;

            var point = hlp.getElementOrDefault(this.points, index);

            if (point) {
                this._setPointData(point, x, y, r);
            }
        };

        datasetCtr.prototype.removePoint = function (index) {
            if (index >= 0 && index < this.points.length) {
                this.points.splice(index, 1);
            }
        };

        datasetCtr.prototype._createNewPoint = function () {
            return new hlp.ScatterPoint({
                ctx: this.chart.ctx,
                datasetLabel: this.label,

                // point
                display: this.pointDot,
                radius: this.pointDotRadius,
                hitDetectionRadius: this.pointHitDetectionRadius,
                strokeWidth: this.pointDotStrokeWidth,

                // colors
                strokeColor: this.pointStrokeColor,
                highlightStroke: this.pointColor,
                fillColor: this.pointColor,
                highlightFill: this.pointStrokeColor
            });
        };

        datasetCtr.prototype._setPointData = function (point, x, y, r) {
            var formattedArg = this.scale.argToString(+x),
                formattedValue = +y + "",
                formattedSize = +r + "";

            point.arg = +x || 0;
            point.value = +y || 0;
            point.size = +r || 0;  // for use in templates

            point.argLabel = helpers.template(this.scaleArgLabel, {value: formattedArg}),
                point.valueLabel = helpers.template(this.scaleLabel, {value: formattedValue});
            point.sizeLabel = helpers.template(this.scaleSizeLabel, {value: formattedSize});
        };

        return datasetCtr;
    })();

    chartjs.Type.extend({
        name: "Scatter",

        defaults: defaultConfig,

        initialize: function (datasets) {
            this.datasets = [];
            this.scale = this._initScale();

            // Compatibility layer
            if (datasets.datasets) {
                datasets = datasets.datasets;
            }

            //Iterate through each of the datasets, and build this into a property of the chart
            helpers.each(datasets, function (dataset) {
                var datasetObject = new chartjs.ScatterDataSet(dataset, this.options, this.chart, this.scale);

                this.datasets.push(datasetObject);

                helpers.each(dataset.data, function (dataPoint) {
                    datasetObject.addPoint(dataPoint.x, dataPoint.y, dataPoint.r || 1);
                });

            }, this);

            //Set up tooltip events on the chart
            if (this.options.showTooltips) {
                helpers.bindEvents(this, this.options.tooltipEvents, function (evt) {
                    var activePoints = (evt.type !== 'mouseout') ? this.getPointsAtEvent(evt) : [];

                    this._forEachPoint(function (point) {
                        point.restore(['fillColor', 'strokeColor']);
                    });

                    helpers.each(activePoints, function (activePoint) {
                        activePoint.fillColor = activePoint.highlightFill;
                        activePoint.strokeColor = activePoint.highlightStroke;
                    });

                    this.showTooltip(activePoints);
                });
            }

            var dataRange = this._calculateRange();
            this.scale.setDataRange(dataRange);

            this.update();
        },

        _initScale: function () {
            var scaleOptions = {
                chart: this.chart,

                textColor: this.options.scaleFontColor,
                fontSize: this.options.scaleFontSize,
                fontStyle: this.options.scaleFontStyle,
                fontFamily: this.options.scaleFontFamily,

                labelTemplate: this.options.scaleLabel,
                argLabelTemplate: this.options.scaleArgLabel,
                showLabels: this.options.scaleShowLabels,
                beginAtZero: this.options.scaleBeginAtZero,
                integersOnly: this.options.scaleIntegersOnly,

                gridLineWidth: (this.options.scaleShowGridLines) ? this.options.scaleGridLineWidth : 0,
                gridLineColor: (this.options.scaleShowGridLines) ? this.options.scaleGridLineColor : "rgba(0,0,0,0)",
                showHorizontalLines: this.options.scaleShowHorizontalLines,
                showVerticalLines: this.options.scaleShowVerticalLines,
                lineWidth: this.options.scaleLineWidth,
                lineColor: this.options.scaleLineColor,
                display: this.options.showScale,

                // y range
                xScaleOverride: this.options.xScaleOverride,
                xScaleSteps: this.options.xScaleSteps,
                xScaleStepWidth: this.options.xScaleStepWidth,
                xScaleStartValue: this.options.xScaleStartValue,

                // y range
                scaleOverride: this.options.scaleOverride,
                scaleSteps: this.options.scaleSteps,
                scaleStepWidth: this.options.scaleStepWidth,
                scaleStartValue: this.options.scaleStartValue,

                // dates
                useUtc: this.options.useUtc,
                dateFormat: this.options.scaleDateFormat,
                timeFormat: this.options.scaleTimeFormat,
                dateTimeFormat: this.options.scaleDateTimeFormat
            };

            return this.options.scaleType === "date"
                ? new chartjs.ScatterDateScale(scaleOptions)
                : new chartjs.ScatterNumberScale(scaleOptions);
        },

        // helpers
        getPointsAtEvent: function (e) {
            var pointsArray = [],
                eventPosition = helpers.getRelativePosition(e);
            helpers.each(this.datasets, function (dataset) {
                helpers.each(dataset.points, function (point) {
                    if (point.inRange(eventPosition.x, eventPosition.y)) pointsArray.push(point);
                });
            }, this);
            return pointsArray;
        },

        showTooltip: function (elements) {
            this.draw();

            if (elements.length > 0) {
                var firstElement = elements[0];
                var tooltipPosition = firstElement.tooltipPosition();

                if (elements.length == 1) {
                    new chartjs.Tooltip({
                        x: Math.round(tooltipPosition.x),
                        y: Math.round(tooltipPosition.y),
                        xPadding: this.options.tooltipXPadding,
                        yPadding: this.options.tooltipYPadding,
                        fillColor: this.options.tooltipFillColor,
                        textColor: this.options.tooltipFontColor,
                        fontFamily: this.options.tooltipFontFamily,
                        fontStyle: this.options.tooltipFontStyle,
                        fontSize: this.options.tooltipFontSize,
                        caretHeight: this.options.tooltipCaretSize,
                        cornerRadius: this.options.tooltipCornerRadius,
                        text: helpers.template(this.options.tooltipTemplate, firstElement),
                        chart: this.chart,
                        custom: this.options.customTooltips
                    }).draw();
                } else {
                    var tooltipLabels = [],
                        tooltipColors = [];

                    helpers.each(elements, function (point) {
                        tooltipLabels.push(helpers.template(this.options.multiTooltipTemplate, point));

                        tooltipColors.push({
                            fill: point._saved.fillColor || point.fillColor,
                            stroke: point._saved.strokeColor || point.strokeColor
                        });

                    }, this);

                    new chartjs.MultiTooltip({
                        x: Math.round(tooltipPosition.x),
                        y: Math.round(tooltipPosition.y),
                        xPadding: this.options.tooltipXPadding,
                        yPadding: this.options.tooltipYPadding,
                        xOffset: this.options.tooltipXOffset,
                        fillColor: this.options.tooltipFillColor,
                        textColor: this.options.tooltipFontColor,
                        fontFamily: this.options.tooltipFontFamily,
                        fontStyle: this.options.tooltipFontStyle,
                        fontSize: this.options.tooltipFontSize,
                        titleTextColor: this.options.tooltipTitleFontColor,
                        titleFontFamily: this.options.tooltipTitleFontFamily,
                        titleFontStyle: this.options.tooltipTitleFontStyle,
                        titleFontSize: this.options.tooltipTitleFontSize,
                        cornerRadius: this.options.tooltipCornerRadius,
                        labels: tooltipLabels,
                        legendColors: tooltipColors,
                        legendColorBackground: this.options.multiTooltipKeyBackground,
                        title: '',
                        chart: this.chart,
                        ctx: this.chart.ctx,
                        custom: this.options.customTooltips
                    }).draw();
                }
            }

            return this;
        },

        _forEachPoint: function (callback) {
            helpers.each(this.datasets, function (dataset) {
                helpers.each(dataset.points, callback, this);
            }, this);
        },

        _forEachDataset: function (callback) {
            helpers.each(this.datasets, callback, this);
        },

        _hasData: function () {
            var hasData = false;

            this._forEachDataset(function (dataset) {
                hasData |= !!dataset.points.length;
            });

            return hasData;
        },

        _calculateRange: function () {
            var xmin = undefined,
                xmax = undefined,
                ymin = undefined,
                ymax = undefined;

            this._forEachPoint(function (point) {
                // min x
                if (xmin === undefined || point.arg < xmin) {
                    xmin = point.arg;
                }

                // max x
                if (xmax === undefined || point.arg > xmax) {
                    xmax = point.arg;
                }

                // min y
                if (ymin === undefined || point.value < ymin) {
                    ymin = point.value;
                }

                // max y
                if (ymax === undefined || point.value > ymax) {
                    ymax = point.value;
                }
            });

            return {
                xmin: xmin,
                xmax: xmax,
                ymin: ymin,
                ymax: ymax
            }
        },

        _drawMessage: function (message) {
            var ctx = this.chart.ctx,
                width = this.chart.width,
                height = this.chart.height,

                fontSize = this.options.scaleFontSize,
                fontStyle = this.options.scaleFontStyle,
                fontFamily = this.options.scaleFontFamily,
                font = helpers.fontString(fontSize, fontStyle, fontFamily);

            // text
            ctx.save();
            ctx.translate(width / 2, height / 2);
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.font = font;
            ctx.fillStyle = this.options.scaleFontColor;
            ctx.fillText(message, 0, 0);
            ctx.restore();
        },

        _drawLine: function (dataset) {
            var ctx = this.chart.ctx,
                prev = undefined;

            ctx.lineJoin = "round";
            ctx.lineWidth = this.options.datasetStrokeWidth;
            ctx.strokeStyle = dataset.strokeColor || this.options.datasetStrokeColor;

            ctx.beginPath();

            helpers.each(dataset.points, function (point, index) {
                if (index === 0) {
                    ctx.moveTo(point.x, point.y);
                }
                else {
                    if (this.options.bezierCurve) {
                        ctx.bezierCurveTo(
                            prev.controlPoints.x2,
                            prev.controlPoints.y2,
                            point.controlPoints.x1,
                            point.controlPoints.y1,
                            point.x, point.y);
                    }
                    else {
                        ctx.lineTo(point.x, point.y);
                    }
                }

                prev = point;

            }, this);

            ctx.stroke();

            // debug
            //if (this.options.bezierCurve) {
            //	ctx.lineWidth = 0.3;

            //	helpers.each(dataset.points, function(point) {
            //		ctx.beginPath();
            //		ctx.moveTo(point.controlPoints.x1, point.controlPoints.y1);
            //		ctx.lineTo(point.x, point.y);
            //		ctx.lineTo(point.controlPoints.x2, point.controlPoints.y2);
            //		ctx.stroke();
            //	});
            //}
        },

        update: function () {
            var dataRange = this._calculateRange();
            this.scale.setDataRange(dataRange);

            this.render();
        },

        draw: function (ease) {
            if (this._hasData()) {
                // update view params
                this.scale.fit();

                this._forEachDataset(function (dataset) {
                    this.scale.updatePoints(dataset.points, ease);

                    if (this.options.bezierCurve) {
                        this.scale.updateBezierControlPoints(dataset.points, ease, this.options.bezierCurveTension);
                    }
                });

                // draw
                this.clear();
                this.scale.draw();

                // draw lines
                if (this.options.datasetStroke) {
                    helpers.each(this.datasets, this._drawLine, this);
                }

                // draw points
                if (this.options.pointDot) {
                    this._forEachPoint(function (point) {
                        point.draw();
                    });
                }
            } else {
                this.clear();
                this._drawMessage(this.options.emptyDataMessage);
            }
        }
    });
}));
