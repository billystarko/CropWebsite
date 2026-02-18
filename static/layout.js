// layout.js — Google Maps overlay for trial plot layout

var map;
var infoWindow;
var layoutData = null;

function initMap() {
    // Default center (will be overridden by data)
    map = new google.maps.Map(document.getElementById('map'), {
        zoom: 18,
        center: { lat: 35.7796, lng: -78.6382 },
        mapTypeId: 'satellite',
    });
    infoWindow = new google.maps.InfoWindow();

    // Fetch layout data
    fetch(LAYOUT_DATA_URL)
        .then(function(res) { return res.json(); })
        .then(function(data) {
            layoutData = data;
            drawBlocks(data);
        })
        .catch(function(err) {
            console.error('Failed to load layout data:', err);
            document.getElementById('map').textContent = 'Failed to load layout data.';
        });
}

function drawBlocks(data) {
    var blocks = data.blocks;
    var treatmentColors = data.treatment_colors;
    var bounds = new google.maps.LatLngBounds();
    var legendEl = document.getElementById('legend');
    var legendHtml = '';

    // If coloring by trait, find value range for gradient
    var allMeasurements = [];
    if (SELECTED_TRAIT_ID) {
        blocks.forEach(function(block) {
            block.plots.forEach(function(p) {
                if (p.measurement !== null && p.measurement !== undefined) {
                    var v = parseFloat(p.measurement);
                    if (!isNaN(v)) allMeasurements.push(v);
                }
            });
        });
    }
    var minMeas = allMeasurements.length ? Math.min.apply(null, allMeasurements) : 0;
    var maxMeas = allMeasurements.length ? Math.max.apply(null, allMeasurements) : 1;
    if (minMeas === maxMeas) maxMeas = minMeas + 1;

    blocks.forEach(function(block) {
        if (block.rows === 0 || block.cols === 0) return;

        // Compute corners of each plot cell
        var plots = block.plots;
        plots.forEach(function(p) {
            var corners = computePlotCorners(
                block.center_lat, block.center_lng,
                block.width_m, block.height_m,
                block.rotation_deg,
                block.rows, block.cols,
                p.row, p.col
            );

            var fillColor;
            var fillOpacity = 0.5;

            if (SELECTED_TRAIT_ID && p.measurement !== null && p.measurement !== undefined) {
                var v = parseFloat(p.measurement);
                if (!isNaN(v)) {
                    var ratio = (v - minMeas) / (maxMeas - minMeas);
                    fillColor = valueToColor(ratio);
                    fillOpacity = 0.7;
                } else {
                    fillColor = '#999';
                    fillOpacity = 0.3;
                }
            } else if (SELECTED_TRAIT_ID) {
                fillColor = '#999';
                fillOpacity = 0.3;
            } else {
                fillColor = treatmentColors[p.treatment_id] || '#999';
            }

            var polygon = new google.maps.Polygon({
                paths: corners,
                strokeColor: '#333',
                strokeOpacity: 0.8,
                strokeWeight: 1,
                fillColor: fillColor,
                fillOpacity: fillOpacity,
            });
            polygon.setMap(map);

            corners.forEach(function(c) { bounds.extend(c); });

            // Click handler
            (function(plot, poly) {
                google.maps.event.addListener(poly, 'click', function(e) {
                    var content = '<div style="font-size:13px;line-height:1.4">' +
                        '<strong>' + plot.plot_code + '</strong><br>' +
                        'Treatment: ' + plot.treatment_name + '<br>' +
                        'Row: ' + (plot.row + 1) + ', Col: ' + (plot.col + 1);
                    if (plot.measurement !== null && plot.measurement !== undefined) {
                        content += '<br>Value: ' + plot.measurement;
                    }
                    content += '</div>';
                    infoWindow.setContent(content);
                    infoWindow.setPosition(e.latLng);
                    infoWindow.open(map);
                });
            })(p, polygon);
        });
    });

    // Fit map to bounds
    if (!bounds.isEmpty()) {
        map.fitBounds(bounds);
    }

    // Build legend
    if (SELECTED_TRAIT_ID && allMeasurements.length) {
        legendHtml += '<p><em>Color by trait value</em></p>';
        legendHtml += '<div class="legend-item"><div class="legend-swatch" style="background:' + valueToColor(0) + '"></div> ' + minMeas.toFixed(1) + ' (low)</div>';
        legendHtml += '<div class="legend-item"><div class="legend-swatch" style="background:' + valueToColor(0.5) + '"></div> ' + ((minMeas + maxMeas) / 2).toFixed(1) + ' (mid)</div>';
        legendHtml += '<div class="legend-item"><div class="legend-swatch" style="background:' + valueToColor(1) + '"></div> ' + maxMeas.toFixed(1) + ' (high)</div>';
        legendHtml += '<div class="legend-item"><div class="legend-swatch" style="background:#999"></div> No data</div>';
    } else {
        // Treatment colors legend
        var seenTreatments = {};
        blocks.forEach(function(block) {
            block.plots.forEach(function(p) {
                if (!seenTreatments[p.treatment_id]) {
                    seenTreatments[p.treatment_id] = p.treatment_name;
                }
            });
        });
        for (var tId in seenTreatments) {
            var color = treatmentColors[tId] || '#999';
            legendHtml += '<div class="legend-item"><div class="legend-swatch" style="background:' + color + '"></div> ' + seenTreatments[tId] + '</div>';
        }
    }
    legendEl.innerHTML = legendHtml;
}

/**
 * Compute the 4 lat/lng corners of a single plot cell within a rotated block.
 */
function computePlotCorners(centerLat, centerLng, widthM, heightM, rotDeg, totalRows, totalCols, row, col) {
    // Each plot cell size in meters
    var cellW = widthM / totalCols;
    var cellH = heightM / totalRows;

    // Position of cell center relative to block center (in meters)
    // Origin at block center; x = east, y = north
    var x0 = -widthM / 2 + col * cellW;
    var y0 = heightM / 2 - row * cellH; // rows go top-to-bottom

    // 4 corners of this cell (before rotation), relative to block center
    var corners = [
        { x: x0,         y: y0 },          // top-left
        { x: x0 + cellW, y: y0 },          // top-right
        { x: x0 + cellW, y: y0 - cellH },  // bottom-right
        { x: x0,         y: y0 - cellH },  // bottom-left
    ];

    var radians = rotDeg * Math.PI / 180;
    var cosR = Math.cos(radians);
    var sinR = Math.sin(radians);

    // Convert meters offset to lat/lng (approximate)
    var metersPerDegreeLat = 111320;
    var metersPerDegreeLng = 111320 * Math.cos(centerLat * Math.PI / 180);

    return corners.map(function(c) {
        // Rotate
        var rx = c.x * cosR - c.y * sinR;
        var ry = c.x * sinR + c.y * cosR;
        return {
            lat: centerLat + ry / metersPerDegreeLat,
            lng: centerLng + rx / metersPerDegreeLng,
        };
    });
}

/**
 * Map a 0–1 ratio to a color (blue → green → red gradient).
 */
function valueToColor(ratio) {
    // Clamp
    ratio = Math.max(0, Math.min(1, ratio));
    var r, g, b;
    if (ratio < 0.5) {
        // blue to green
        var t = ratio * 2;
        r = 0;
        g = Math.round(200 * t);
        b = Math.round(200 * (1 - t));
    } else {
        // green to red
        var t = (ratio - 0.5) * 2;
        r = Math.round(220 * t);
        g = Math.round(200 * (1 - t));
        b = 0;
    }
    return 'rgb(' + r + ',' + g + ',' + b + ')';
}
