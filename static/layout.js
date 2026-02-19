// layout.js — Canvas-based plot layout visualization (no external APIs)

(function() {
    var canvas = document.getElementById('layout-canvas');
    var ctx = canvas.getContext('2d');
    var tooltip = document.getElementById('tooltip');
    var legendEl = document.getElementById('legend');
    var layoutData = null;
    var plotRects = []; // {x, y, w, h, plot} for hit-testing

    // Resize canvas to fill container
    function resizeCanvas() {
        var wrap = canvas.parentElement;
        canvas.width = wrap.clientWidth;
        canvas.height = wrap.clientHeight || 500;
    }

    function init() {
        resizeCanvas();
        ctx.fillStyle = '#e8e8e8';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#888';
        ctx.textAlign = 'center';
        ctx.font = '14px sans-serif';
        ctx.fillText('Loading layout...', canvas.width / 2, canvas.height / 2);

        fetch(LAYOUT_DATA_URL)
            .then(function(res) { return res.json(); })
            .then(function(data) {
                layoutData = data;
                drawLayout(data);
            })
            .catch(function(err) {
                console.error('Failed to load layout data:', err);
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = '#c00';
                ctx.fillText('Failed to load layout data.', canvas.width / 2, canvas.height / 2);
            });
    }

    function drawLayout(data) {
        resizeCanvas();
        plotRects = [];
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#e8e8e8';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        var blocks = data.blocks;
        var treatmentColors = data.treatment_colors;

        if (!blocks || blocks.length === 0) {
            ctx.fillStyle = '#888';
            ctx.textAlign = 'center';
            ctx.font = '14px sans-serif';
            ctx.fillText('No blocks to display.', canvas.width / 2, canvas.height / 2);
            return;
        }

        // Gather measurement stats for trait coloring
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

        // Layout: stack blocks vertically with padding
        var padding = 20;
        var blockGap = 30;
        var labelHeight = 24;
        var currentY = padding;

        // Calculate total height needed, then scale if necessary
        var totalNeeded = padding;
        blocks.forEach(function(block) {
            if (block.rows === 0 || block.cols === 0) return;
            totalNeeded += labelHeight + blockGap;
            var cellH = Math.max(30, Math.min(50, (canvas.height - padding * 2) / (blocks.length * Math.max.apply(null, blocks.map(function(b){ return b.rows || 1; })))));
            totalNeeded += block.rows * cellH;
        });

        // Determine a good cell size
        var maxRows = Math.max.apply(null, blocks.map(function(b){ return b.rows || 1; }));
        var maxCols = Math.max.apply(null, blocks.map(function(b){ return b.cols || 1; }));
        var availWidth = canvas.width - padding * 2;
        var availHeightPerBlock = (canvas.height - padding * 2 - (blocks.length - 1) * blockGap - blocks.length * labelHeight) / blocks.length;

        blocks.forEach(function(block) {
            if (block.rows === 0 || block.cols === 0) return;

            var cellW = Math.min(80, availWidth / block.cols);
            var cellH = Math.min(50, Math.max(25, availHeightPerBlock / block.rows));
            var blockWidth = cellW * block.cols;
            var startX = padding + (availWidth - blockWidth) / 2;

            // Block label
            ctx.fillStyle = '#333';
            ctx.textAlign = 'center';
            ctx.font = 'bold 13px sans-serif';
            ctx.fillText('Block: ' + (block.block_name || block.block_id), startX + blockWidth / 2, currentY + 14);
            currentY += labelHeight;

            // Draw each plot cell
            block.plots.forEach(function(p) {
                var x = startX + p.col * cellW;
                var y = currentY + p.row * cellH;

                var fillColor;
                var fillOpacity = 1;

                if (SELECTED_TRAIT_ID && p.measurement !== null && p.measurement !== undefined) {
                    var v = parseFloat(p.measurement);
                    if (!isNaN(v)) {
                        var ratio = (v - minMeas) / (maxMeas - minMeas);
                        fillColor = valueToColor(ratio);
                    } else {
                        fillColor = '#ccc';
                    }
                } else if (SELECTED_TRAIT_ID) {
                    fillColor = '#ccc';
                } else {
                    fillColor = treatmentColors[p.treatment_id] || '#ccc';
                }

                // Fill cell
                ctx.fillStyle = fillColor;
                ctx.fillRect(x + 1, y + 1, cellW - 2, cellH - 2);

                // Border
                ctx.strokeStyle = '#555';
                ctx.lineWidth = 1;
                ctx.strokeRect(x + 1, y + 1, cellW - 2, cellH - 2);

                // Plot code label (if cells are big enough)
                if (cellW > 35 && cellH > 20) {
                    ctx.fillStyle = '#000';
                    ctx.textAlign = 'center';
                    ctx.font = '10px sans-serif';
                    ctx.fillText(p.plot_code || '', x + cellW / 2, y + cellH / 2 + 3);
                }

                // Store rect for hit-testing
                plotRects.push({ x: x + 1, y: y + 1, w: cellW - 2, h: cellH - 2, plot: p });
            });

            currentY += block.rows * cellH + blockGap;
        });

        // Build legend
        buildLegend(blocks, treatmentColors, allMeasurements, minMeas, maxMeas);
    }

    function buildLegend(blocks, treatmentColors, allMeasurements, minMeas, maxMeas) {
        var html = '';
        if (SELECTED_TRAIT_ID && allMeasurements.length) {
            html += '<p><em>Color by trait value</em></p>';
            html += '<div class="legend-item"><div class="legend-swatch" style="background:' + valueToColor(0) + '"></div> ' + minMeas.toFixed(1) + ' (low)</div>';
            html += '<div class="legend-item"><div class="legend-swatch" style="background:' + valueToColor(0.5) + '"></div> ' + ((minMeas + maxMeas) / 2).toFixed(1) + ' (mid)</div>';
            html += '<div class="legend-item"><div class="legend-swatch" style="background:' + valueToColor(1) + '"></div> ' + maxMeas.toFixed(1) + ' (high)</div>';
            html += '<div class="legend-item"><div class="legend-swatch" style="background:#ccc"></div> No data</div>';
        } else {
            var seenTreatments = {};
            blocks.forEach(function(block) {
                block.plots.forEach(function(p) {
                    if (!seenTreatments[p.treatment_id]) {
                        seenTreatments[p.treatment_id] = p.treatment_name;
                    }
                });
            });
            for (var tId in seenTreatments) {
                var color = treatmentColors[tId] || '#ccc';
                html += '<div class="legend-item"><div class="legend-swatch" style="background:' + color + '"></div> ' + seenTreatments[tId] + '</div>';
            }
        }
        legendEl.innerHTML = html;
    }

    // Tooltip on hover
    canvas.addEventListener('mousemove', function(e) {
        var rect = canvas.getBoundingClientRect();
        var mx = e.clientX - rect.left;
        var my = e.clientY - rect.top;

        var hit = null;
        for (var i = 0; i < plotRects.length; i++) {
            var r = plotRects[i];
            if (mx >= r.x && mx <= r.x + r.w && my >= r.y && my <= r.y + r.h) {
                hit = r;
                break;
            }
        }

        if (hit) {
            var p = hit.plot;
            var html = '<strong>' + (p.plot_code || '') + '</strong><br>' +
                'Treatment: ' + (p.treatment_name || '—') + '<br>' +
                'Row: ' + (p.row + 1) + ', Col: ' + (p.col + 1);
            if (p.measurement !== null && p.measurement !== undefined) {
                html += '<br>Value: ' + p.measurement;
            }
            tooltip.innerHTML = html;
            tooltip.style.display = 'block';
            tooltip.style.left = (mx + 12) + 'px';
            tooltip.style.top = (my + 12) + 'px';
            canvas.style.cursor = 'pointer';
        } else {
            tooltip.style.display = 'none';
            canvas.style.cursor = 'default';
        }
    });

    canvas.addEventListener('mouseleave', function() {
        tooltip.style.display = 'none';
    });

    // Redraw on resize
    window.addEventListener('resize', function() {
        if (layoutData) {
            drawLayout(layoutData);
        }
    });

    /**
     * Map a 0-1 ratio to a color (blue -> green -> red gradient).
     */
    function valueToColor(ratio) {
        ratio = Math.max(0, Math.min(1, ratio));
        var r, g, b;
        if (ratio < 0.5) {
            var t = ratio * 2;
            r = 0;
            g = Math.round(200 * t);
            b = Math.round(200 * (1 - t));
        } else {
            var t2 = (ratio - 0.5) * 2;
            r = Math.round(220 * t2);
            g = Math.round(200 * (1 - t2));
            b = 0;
        }
        return 'rgb(' + r + ',' + g + ',' + b + ')';
    }

    // Start
    init();
})();
