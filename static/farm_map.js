// farm_map.js — Drag-and-drop trial positioning on farm images

(function () {
    var wrapper = document.getElementById('map-wrapper');
    var farmImage = document.getElementById('farm-image');
    var farmSelect = document.getElementById('farm-select');
    var blocks = [];

    // Navigate to new farm when selector changes
    farmSelect.addEventListener('change', function () {
        window.location.href = '/farm_map?farm=' + encodeURIComponent(this.value);
    });

    // Create draggable trial blocks once the image loads
    function createBlocks() {
        // Remove any existing blocks
        blocks.forEach(function (b) { if (b.el.parentNode) b.el.parentNode.removeChild(b.el); });
        blocks = [];

        TRIALS_DATA.forEach(function (trial) {
            var el = document.createElement('div');
            el.className = 'trial-block';
            el.innerHTML =
                '<div class="tb-name">' + escapeHtml(trial.name) + '</div>' +
                '<div class="tb-detail">' + escapeHtml(trial.crop_category) + ' · ' + trial.year + '</div>' +
                '<div class="tb-detail">' + trial.plot_count + ' plot(s)</div>';
            el.dataset.trialId = trial.id;

            wrapper.appendChild(el);
            positionBlock(el, trial.map_x, trial.map_y);

            blocks.push({ el: el, trial: trial });
            makeDraggable(el, trial);
        });
    }

    function positionBlock(el, pctX, pctY) {
        // Position the block so its center is at (pctX%, pctY%) of the image
        var imgRect = farmImage.getBoundingClientRect();
        var wrapRect = wrapper.getBoundingClientRect();
        var imgOffsetX = imgRect.left - wrapRect.left;
        var imgOffsetY = imgRect.top - wrapRect.top;
        var imgW = imgRect.width;
        var imgH = imgRect.height;

        var px = imgOffsetX + (pctX / 100) * imgW;
        var py = imgOffsetY + (pctY / 100) * imgH;

        el.style.left = (px - el.offsetWidth / 2) + 'px';
        el.style.top = (py - el.offsetHeight / 2) + 'px';
    }

    function makeDraggable(el, trial) {
        var startX, startY, origLeft, origTop;
        var dragging = false;

        function onPointerDown(e) {
            e.preventDefault();
            dragging = true;
            startX = e.clientX;
            startY = e.clientY;
            origLeft = parseInt(el.style.left, 10) || 0;
            origTop = parseInt(el.style.top, 10) || 0;
            el.style.zIndex = 100;
            document.addEventListener('pointermove', onPointerMove);
            document.addEventListener('pointerup', onPointerUp);
        }

        function onPointerMove(e) {
            if (!dragging) return;
            var dx = e.clientX - startX;
            var dy = e.clientY - startY;
            el.style.left = (origLeft + dx) + 'px';
            el.style.top = (origTop + dy) + 'px';
        }

        function onPointerUp(e) {
            if (!dragging) return;
            dragging = false;
            el.style.zIndex = 10;
            document.removeEventListener('pointermove', onPointerMove);
            document.removeEventListener('pointerup', onPointerUp);

            // Calculate new percentage position based on center of block relative to image
            var imgRect = farmImage.getBoundingClientRect();
            var wrapRect = wrapper.getBoundingClientRect();
            var imgOffsetX = imgRect.left - wrapRect.left;
            var imgOffsetY = imgRect.top - wrapRect.top;
            var imgW = imgRect.width;
            var imgH = imgRect.height;

            var blockCenterX = parseInt(el.style.left, 10) + el.offsetWidth / 2;
            var blockCenterY = parseInt(el.style.top, 10) + el.offsetHeight / 2;

            var pctX = ((blockCenterX - imgOffsetX) / imgW) * 100;
            var pctY = ((blockCenterY - imgOffsetY) / imgH) * 100;

            // Clamp to 0-100
            pctX = Math.max(0, Math.min(100, pctX));
            pctY = Math.max(0, Math.min(100, pctY));

            trial.map_x = pctX;
            trial.map_y = pctY;

            // Save to server
            fetch('/trials/' + trial.id + '/update_position', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ map_x: pctX, map_y: pctY })
            }).catch(function (err) {
                console.error('Failed to save position:', err);
            });
        }

        el.addEventListener('pointerdown', onPointerDown);
    }

    // Reposition blocks when the window resizes
    window.addEventListener('resize', function () {
        blocks.forEach(function (b) {
            positionBlock(b.el, b.trial.map_x, b.trial.map_y);
        });
    });

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    // Wait for the farm image to load before placing blocks
    if (farmImage.complete) {
        createBlocks();
    } else {
        farmImage.addEventListener('load', createBlocks);
    }
})();
