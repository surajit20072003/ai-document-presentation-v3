/**
 * topic_reference_scene.js
 * ========================
 * THE API CONTRACT — every generated Three.js beat file must follow this exactly.
 *
 * CONTRACT SUMMARY:
 *   - Entry point: initScene(container, totalDuration, params)
 *   - Return:      { onResize, onPinchZoom, dispose, onPointerMove, onPointerDown, onPointerUp }
 *   - No imports. THREE loaded by player via CDN (r128).
 *   - Animation fills totalDuration seconds exactly, then FREEZES.
 *   - Text via canvas texture on PlaneGeometry ONLY.
 *   - All closures (fadeIn, animateDraw) created BEFORE animate(). Never inside.
 *   - scene.add() called at setup. Never inside animate().
 */

// ── HELPER FUNCTIONS (defined before initScene) ───────────────────────────────

function makeLabel(text, hexColor, fontSize) {
  fontSize = fontSize || 48;
  var cvs = document.createElement('canvas');
  cvs.width = 512; cvs.height = 128;
  var ctx = cvs.getContext('2d');
  ctx.clearRect(0, 0, 512, 128);
  ctx.font = 'bold ' + fontSize + 'px Caveat, cursive, sans-serif';
  ctx.fillStyle = '#' + hexColor.toString(16).padStart(6, '0');
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, 256, 64);
  var tex = new THREE.CanvasTexture(cvs);
  var mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false });
  var geo = new THREE.PlaneGeometry(3.0, 0.7);
  return new THREE.Mesh(geo, mat);
}

function makeLine(x1, y1, z1, x2, y2, z2, color, lw) {
  var geo = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(x1, y1, z1),
    new THREE.Vector3(x2, y2, z2)
  ]);
  var mat = new THREE.LineBasicMaterial({ color: color, linewidth: lw || 2 });
  return new THREE.Line(geo, mat);
}

// KEY RULE: returns a CLOSURE. Call once before animate(). Call the closure inside animate().
function animateDraw(line, durationSec, startSec) {
  var count = line.geometry.attributes.position.count;
  line.geometry.setDrawRange(0, 0);
  return function(elapsed) {
    var t = Math.min(Math.max((elapsed - startSec) / durationSec, 0), 1);
    line.geometry.setDrawRange(0, Math.ceil(t * count));
  };
}

// KEY RULE: returns a CLOSURE. Call once before animate(). Call the closure inside animate().
function fadeIn(mesh, durationSec, startSec) {
  if (mesh.material) mesh.material.opacity = 0;
  return function(elapsed) {
    if (!mesh.material) return;
    mesh.material.opacity = Math.min(Math.max((elapsed - startSec) / durationSec, 0), 1);
  };
}

// ── MAIN ENTRY POINT ─────────────────────────────────────────────────────────

function initScene(container, totalDuration, params) {

  // Graceful fail if THREE not loaded
  if (typeof THREE === 'undefined') {
    return {
      onResize: function(){}, onPinchZoom: function(){}, dispose: function(){},
      onPointerMove: function(){}, onPointerDown: function(){}, onPointerUp: function(){}
    };
  }

  var W = container.clientWidth  || 800;
  var H = container.clientHeight || 450;

  // ── RENDERER ───────────────────────────────────────────────────────────────
  var renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setSize(W, H);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x0d1117, 1);   // V3 standard — always this colour
  container.appendChild(renderer.domElement);

  // ── SCENE + CAMERA ─────────────────────────────────────────────────────────
  var scene  = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 100);
  camera.position.set(0, 0, 8);
  camera.lookAt(0, 0, 0);

  // ── LIGHTING ───────────────────────────────────────────────────────────────
  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  var dir = new THREE.DirectionalLight(0xffffff, 0.8);
  dir.position.set(5, 5, 5);
  scene.add(dir);

  // ── COLOUR PALETTE — always CLR, never C ──────────────────────────────────
  var CLR = {
    gold : 0xf6c44e,
    teal : 0x00d2b4,
    rose : 0xff6b8a,
    sky  : 0x79c0ff,
    lav  : 0xb8a9ff,
    grn  : 0x7ee787,
    white: 0xe6edf3,
    dim  : 0x555555
  };

  // ── SCENE OBJECTS — all added here, never inside animate() ────────────────
  // Right triangle: A (bottom-left), B (bottom-right, right angle), C (top-right)
  var ptA = new THREE.Vector3(-2.5, -1.5, 0);
  var ptB = new THREE.Vector3( 2.5, -1.5, 0);
  var ptC = new THREE.Vector3( 2.5,  2.0, 0);

  var lineAB = makeLine(ptA.x, ptA.y, 0, ptB.x, ptB.y, 0, CLR.teal,  2.5);
  var lineBC = makeLine(ptB.x, ptB.y, 0, ptC.x, ptC.y, 0, CLR.rose,  2.5);
  var lineAC = makeLine(ptA.x, ptA.y, 0, ptC.x, ptC.y, 0, CLR.gold,  3.0);
  scene.add(lineAB, lineBC, lineAC);

  // Right-angle marker at B
  var sq = 0.25;
  var ra1 = makeLine(ptB.x - sq, ptB.y, 0, ptB.x - sq, ptB.y + sq, 0, CLR.white, 1.5);
  var ra2 = makeLine(ptB.x - sq, ptB.y + sq, 0, ptB.x, ptB.y + sq, 0, CLR.white, 1.5);
  scene.add(ra1, ra2);

  // Vertex labels — added at setup, opacity 0, revealed by fadeIn closures
  var lblA = makeLabel('A', CLR.sky, 44);  lblA.position.set(ptA.x - 0.5, ptA.y - 0.2, 0);
  var lblB = makeLabel('B', CLR.sky, 44);  lblB.position.set(ptB.x + 0.5, ptB.y - 0.2, 0);
  var lblC = makeLabel('C', CLR.sky, 44);  lblC.position.set(ptC.x + 0.5, ptC.y + 0.1, 0);
  scene.add(lblA, lblB, lblC);

  // Side labels
  var lblHyp = makeLabel('Hypotenuse', CLR.gold, 36);
  lblHyp.position.set(-0.2, 0.4, 0);
  lblHyp.rotation.z = Math.atan2(ptC.y - ptA.y, ptC.x - ptA.x);
  scene.add(lblHyp);

  var lblOpp = makeLabel('Opposite', CLR.rose, 36);
  lblOpp.position.set(ptC.x + 1.1, (ptB.y + ptC.y) / 2, 0);
  scene.add(lblOpp);

  var lblAdj = makeLabel('Adjacent', CLR.teal, 36);
  lblAdj.position.set((ptA.x + ptB.x) / 2, ptA.y - 0.55, 0);
  scene.add(lblAdj);

  // ── INTERACTION SETUP (hover_highlight example) ───────────────────────────
  // The player wires onPointerMove → scene.onPointerMove(nx, ny, isDrag)
  // This scene implements hover_highlight on the three sides.
  var raycaster    = new THREE.Raycaster();
  var mouse        = new THREE.Vector2();
  var hoverTargets = [lineAB, lineBC, lineAC];
  var hovered      = null;

  // Give each line a base color for restore-on-unhover
  lineAB.userData = { baseColor: CLR.teal,  name: 'Adjacent'    };
  lineBC.userData = { baseColor: CLR.rose,  name: 'Opposite'    };
  lineAC.userData = { baseColor: CLR.gold,  name: 'Hypotenuse'  };

  // Hover tooltip label (shared, repositioned)
  var lblTooltip = makeLabel('', CLR.white, 32);
  lblTooltip.visible = false;
  scene.add(lblTooltip);

  function onPointerMove(nx, ny, isDrag) {
    mouse.x =  (nx * 2) - 1;
    mouse.y = -(ny * 2) + 1;
    raycaster.setFromCamera(mouse, camera);
    var hits = raycaster.intersectObjects(hoverTargets);
    var hit  = hits.length ? hits[0].object : null;

    if (hit !== hovered) {
      if (hovered) {
        hovered.material.color.setHex(hovered.userData.baseColor);
        lblTooltip.visible = false;
      }
      hovered = hit;
      if (hovered) {
        hovered.material.color.setHex(0xffffff);
        lblTooltip.visible = true;
        // Rebuild canvas texture with correct name
        var cvs = document.createElement('canvas');
        cvs.width = 512; cvs.height = 128;
        var ctx = cvs.getContext('2d');
        ctx.clearRect(0, 0, 512, 128);
        ctx.font = 'bold 38px Caveat, cursive, sans-serif';
        ctx.fillStyle = '#e6edf3';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(hovered.userData.name, 256, 64);
        lblTooltip.material.map = new THREE.CanvasTexture(cvs);
        lblTooltip.material.map.needsUpdate = true;
        lblTooltip.position.set(hovered.position ? hovered.position.x : 0, 3.0, 0);
        if (params && params.onInteract) {
          params.onInteract('hover', { target: hovered.userData.name });
        }
      }
    }
  }

  function onPointerDown(nx, ny) { /* click_reveal would go here */ }
  function onPointerUp(nx, ny)   { /* drag end would go here */ }

  // ── ANIMATION CLOSURES — created ONCE before animate() ───────────────────
  // Segment 1 (0.0s – 5.0s): draw triangle
  var drawAB = animateDraw(lineAB, 1.2, 0.5);
  var drawBC = animateDraw(lineBC, 1.2, 1.5);
  var drawAC = animateDraw(lineAC, 1.2, 2.5);
  var drawRA1 = animateDraw(ra1, 0.4, 3.5);
  var drawRA2 = animateDraw(ra2, 0.4, 3.8);

  // Segment 2 (5.0s – 10.0s): vertex labels
  var fadeLblA = fadeIn(lblA, 0.5, 5.2);
  var fadeLblB = fadeIn(lblB, 0.5, 5.7);
  var fadeLblC = fadeIn(lblC, 0.5, 6.2);

  // Segment 3 (10.0s – 15.0s): side labels
  var fadeHyp = fadeIn(lblHyp, 0.6, 10.2);
  var fadeOpp = fadeIn(lblOpp, 0.6, 11.5);
  var fadeAdj = fadeIn(lblAdj, 0.6, 13.0);

  // ── CLOCK ─────────────────────────────────────────────────────────────────
  var clock    = new THREE.Clock();
  var finished = false;
  var frameId  = null;

  function getElapsed() {
    return (params && typeof params.getTime === 'function')
      ? params.getTime()
      : clock.getElapsedTime();
  }

  // ── RENDER LOOP ───────────────────────────────────────────────────────────
  function animate() {
    frameId = requestAnimationFrame(animate);
    var e = getElapsed();

    // Segment 1 (0.0 – 5.0s): draw triangle
    if (e >= 0.0 && e < 5.0) {
      drawAB(e); drawBC(e); drawAC(e);
      drawRA1(e); drawRA2(e);
    }

    // Segment 2 (5.0 – 10.0s): vertex labels
    if (e >= 5.0 && e < 10.0) {
      fadeLblA(e); fadeLblB(e); fadeLblC(e);
    }

    // Segment 3 (10.0s – end): side labels
    if (e >= 10.0) {
      fadeHyp(e); fadeOpp(e); fadeAdj(e);
    }

    renderer.render(scene, camera);

    if (!finished && e >= totalDuration) {
      finished = true;
      cancelAnimationFrame(frameId);
      renderer.render(scene, camera);   // freeze last frame
    }
  }

  animate();

  // ── PUBLIC HOOKS ─────────────────────────────────────────────────────────
  function onResize() {
    W = container.clientWidth;
    H = container.clientHeight;
    camera.aspect = W / H;
    camera.updateProjectionMatrix();
    renderer.setSize(W, H);
    if (finished) renderer.render(scene, camera);
  }

  function onPinchZoom(delta) {
    camera.position.z = Math.max(2.0, Math.min(15.0, camera.position.z - delta));
  }

  function dispose() {
    if (frameId) cancelAnimationFrame(frameId);
    renderer.dispose();
    if (container.contains(renderer.domElement)) {
      container.removeChild(renderer.domElement);
    }
    scene.traverse(function(obj) {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (obj.material.map) obj.material.map.dispose();
        obj.material.dispose();
      }
    });
  }

  // All 6 hooks returned — onPointerMove/Down/Up are optional but always present
  return {
    onResize:      onResize,
    onPinchZoom:   onPinchZoom,
    dispose:       dispose,
    onPointerMove: onPointerMove,
    onPointerDown: onPointerDown,
    onPointerUp:   onPointerUp
  };
}
