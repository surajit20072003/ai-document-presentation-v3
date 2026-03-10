# Player V3 — Three Surgical Fixes
**Apply all three to `player/player_v3.html`**

---

## FIX 1 — Avatar squeezed (size collapse)

**Root cause:** `#av-overlay` has no explicit height. When `<video>` was shrunk to 1×1px, the container collapsed, making `aspect-ratio:9/16` on the canvas render at near-zero size.

**Find this CSS block (~line 663):**
```css
#av-overlay {
    position: fixed;
    bottom: 68px;
    right: 16px;
    z-index: 50;
    width: 100px;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0, 0, 0, .5);
    border: 1px solid rgba(255, 255, 255, .1);
    transition: all .3s;
    cursor: pointer;
    display: none
}
```

**Replace with:**
```css
#av-overlay {
    position: fixed;
    bottom: 68px;
    right: 16px;
    z-index: 50;
    width: 120px;
    height: 213px; /* explicit height = width * 16/9 — prevents collapse */
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0, 0, 0, .5);
    border: 1px solid rgba(255, 255, 255, .1);
    transition: all .3s;
    cursor: pointer;
    display: none
}

#av-overlay:hover {
    width: 150px;
    height: 267px; /* keep ratio on hover */
}
```

**Also update the canvas element (~line 972):**

Find:
```html
<canvas id="av-canvas" style="aspect-ratio:9/16;width:100%;display:block;"></canvas>
```
Replace with:
```html
<canvas id="av-canvas" style="width:100%;height:100%;display:block;position:absolute;top:0;left:0;"></canvas>
```

**And fix `initAvatarWebGL()` to use explicit container size (~line 1062):**

Find:
```javascript
var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true });
renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
```
Replace with:
```javascript
var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true });
var overlay = document.getElementById('av-overlay');
renderer.setSize(overlay.clientWidth, overlay.clientHeight, false);
```

And update the resize listener at the bottom of `initAvatarWebGL()`:
```javascript
window.addEventListener('resize', function () {
    var overlay = document.getElementById('av-overlay');
    renderer.setSize(overlay.clientWidth, overlay.clientHeight, false);
});
```

---

## FIX 2 — Green screen not removed (wrong key color / threshold)

**Root cause:** Hardcoded `0x00ff00` may not match the actual green in the avatar video. Also `similarity: 0.28` is too strict. Need auto-sampling from first video frame + looser threshold.

**Find the `initAvatarWebGL()` function. Replace the uniform setup block:**

Find:
```javascript
var material = new THREE.ShaderMaterial({
    uniforms: {
        map: { value: texture },
        keyColor: { value: new THREE.Color(0x00ff00) },
        similarity: { value: 0.28 },
        smoothness: { value: 0.12 }
    },
```

Replace with:
```javascript
// Sample actual green from top-left corner of first video frame
var keyColor = new THREE.Color(0x00b140); // fallback: common avatar green
try {
    var sampleCanvas = document.createElement('canvas');
    sampleCanvas.width = 16; sampleCanvas.height = 16;
    var sctx = sampleCanvas.getContext('2d');
    sctx.drawImage(video, 0, 0, 16, 16);
    var px = sctx.getImageData(2, 2, 1, 1).data; // sample top-left corner
    if (px[1] > px[0] && px[1] > px[2]) {        // confirm it's greenish
        keyColor.setRGB(px[0]/255, px[1]/255, px[2]/255);
    }
} catch(e) { /* cross-origin fallback — use default */ }

var material = new THREE.ShaderMaterial({
    uniforms: {
        map: { value: texture },
        keyColor: { value: keyColor },
        similarity: { value: 0.35 },   // looser — catches green spill
        smoothness: { value: 0.15 }    // soft edge
    },
```

**Also wrap the sampling in a `loadeddata` event** so video has a frame before sampling.

Find the line where `initAvatarWebGL()` is called (~line 1137):
```javascript
if (typeof THREE !== 'undefined') {
    initAvatarWebGL();
}
```

Replace with:
```javascript
if (typeof THREE !== 'undefined') {
    var avVidEl = document.getElementById('av-vid');
    if (avVidEl.readyState >= 2) {
        initAvatarWebGL();
    } else {
        avVidEl.addEventListener('loadeddata', function() {
            initAvatarWebGL();
        }, { once: true });
    }
}
```

---

## FIX 3 — Recap subtitles still showing (second injection site overwriting the fix)

**Root cause:** The `isRecap` check exists in the Three.js beat loop but the **video beat loop** at ~line 1625 also injects subtitle text. The recap section uses the video renderer, so the video loop fires and overwrites the hide.

The fix is one additional guard: **hide subtitle overlay permanently when section type is recap**, at section load time, so no downstream loop can re-show it.

**Find `loadSection()` — the block that hides subtitles at section start (~line 1293):**
```javascript
// Hide subtitles by default on new section load
var subtitleEl = document.getElementById('subtitle-overlay');
if (subtitleEl) subtitleEl.style.display = 'none';
```

**Replace with:**
```javascript
// Hide subtitles on new section load
var subtitleEl = document.getElementById('subtitle-overlay');
if (subtitleEl) {
    subtitleEl.style.display = 'none';
    // For recap: set a data attribute so ALL downstream loops respect the hide
    if (secType === 'recap') {
        subtitleEl.setAttribute('data-force-hide', 'true');
    } else {
        subtitleEl.removeAttribute('data-force-hide');
    }
}
```

**Then find BOTH places that set `subtitleEl.style.display = 'block'` (~lines 1492 and 1632):**

Change each from:
```javascript
if (subtitleEl) subtitleEl.style.display = 'block';
```
To:
```javascript
if (subtitleEl && subtitleEl.getAttribute('data-force-hide') !== 'true') {
    subtitleEl.style.display = 'block';
}
```

That's it. The `data-force-hide` attribute acts as a section-level lock — no loop can re-show subtitles once recap sets it.

---

## Summary — 3 files touched, all in `player_v3.html`

| Fix | Lines changed | Risk |
|---|---|---|
| FIX 1: Avatar size | CSS block + canvas element + 2 JS lines | Low |
| FIX 2: Green screen | Uniform setup + call site guard | Low |
| FIX 3: Recap subtitles | 1 set + 2 show guards | Very low |