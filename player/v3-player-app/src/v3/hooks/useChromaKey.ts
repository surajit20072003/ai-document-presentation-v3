import { useEffect, useRef, useCallback } from 'react';
import * as THREE from 'three';

interface UseChromaKeyOptions {
    videoRef: React.RefObject<HTMLVideoElement | null>;
    canvasRef: React.RefObject<HTMLCanvasElement | null>;
    overlayRef: React.RefObject<HTMLDivElement | null>;
    enabled?: boolean;
}

interface ChromaKeyState {
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    camera: THREE.OrthographicCamera;
    material: THREE.ShaderMaterial;
    texture: THREE.VideoTexture;
    animId: number;
}

const VERTEX_SHADER = `
  varying vec2 vUv;
  void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
`;

const FRAGMENT_SHADER = `
  uniform sampler2D map;
  uniform vec3 keyColor;
  uniform float similarity;
  uniform float smoothness;
  uniform float uCanvasAspect;
  uniform float uVideoAspect;
  varying vec2 vUv;
  void main() {
    vec2 uv = vUv;
    if (uCanvasAspect > uVideoAspect) {
      float scale = uCanvasAspect / uVideoAspect;
      uv.x = (uv.x - 0.5) * scale + 0.5;
    } else {
      float scale = uVideoAspect / uCanvasAspect;
      uv.y = (uv.y - 0.5) * scale + 0.5;
    }
    vec4 videoColor = (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) ? vec4(0.0) : texture2D(map, uv);
    float Y1 = 0.299 * keyColor.r + 0.587 * keyColor.g + 0.114 * keyColor.b;
    float Cr1 = keyColor.r - Y1;
    float Cb1 = keyColor.b - Y1;
    float Y2 = 0.299 * videoColor.r + 0.587 * videoColor.g + 0.114 * videoColor.b;
    float Cr2 = videoColor.r - Y2;
    float Cb2 = videoColor.b - Y2;
    float blend = distance(vec2(Cr2, Cb2), vec2(Cr1, Cb1));
    float alpha = smoothstep(similarity, similarity + max(smoothness, 0.001), blend);
    gl_FragColor = vec4(videoColor.rgb * alpha, alpha);
  }
`;

function sampleKeyColor(video: HTMLVideoElement): THREE.Color {
    const fallback = new THREE.Color(0x00b140);
    try {
        const sc = document.createElement('canvas');
        sc.width = 16; sc.height = 16;
        const ctx = sc.getContext('2d');
        if (!ctx) return fallback;
        ctx.drawImage(video, 0, 0, 16, 16);
        const px = ctx.getImageData(2, 2, 1, 1).data;
        if (px[1] > px[0] && px[1] > px[2]) {
            return new THREE.Color(px[0] / 255, px[1] / 255, px[2] / 255);
        }
    } catch (_) { }
    return fallback;
}

export function useChromaKey({ videoRef, canvasRef, overlayRef, enabled = true }: UseChromaKeyOptions) {
    const stateRef = useRef<ChromaKeyState | null>(null);

    const resizeCanvas = useCallback(() => {
        const ov = overlayRef.current;
        const vid = videoRef.current;
        const st = stateRef.current;
        if (!ov || !vid || !st) return;
        const dpr = window.devicePixelRatio || 1;
        const h = ov.clientHeight || 356;
        const vw = vid.videoWidth || 1080;
        const vh = vid.videoHeight || 1920;
        const aspect = vw / vh;
        const w = h * aspect;
        ov.style.width = w + 'px';
        st.renderer.setSize(w, h, false);
        st.renderer.setPixelRatio(dpr);
        st.material.uniforms.uCanvasAspect.value = w / h;
        st.material.uniforms.uVideoAspect.value = aspect;
    }, [overlayRef, videoRef]);

    const resample = useCallback(() => {
        const vid = videoRef.current;
        const st = stateRef.current;
        if (!vid || !st) return;
        const color = sampleKeyColor(vid);
        st.material.uniforms.keyColor.value.copy(color);
    }, [videoRef]);

    useEffect(() => {
        if (!enabled) return;
        const canvas = canvasRef.current;
        const video = videoRef.current;
        if (!canvas || !video) return;

        const dpr = window.devicePixelRatio || 1;
        let renderer: THREE.WebGLRenderer;
        try {
            renderer = new THREE.WebGLRenderer({ canvas, alpha: true, premultipliedAlpha: false });
        } catch (err) {
            console.warn('[useChromaKey] WebGL init failed:', err);
            return;
        }
        renderer.setPixelRatio(dpr);
        renderer.setClearColor(0x000000, 0);

        const scene = new THREE.Scene();
        const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
        const texture = new THREE.VideoTexture(video);
        texture.minFilter = THREE.LinearFilter;
        texture.magFilter = THREE.LinearFilter;
        texture.format = THREE.RGBAFormat;

        const material = new THREE.ShaderMaterial({
            transparent: true,
            uniforms: {
                map: { value: texture },
                keyColor: { value: new THREE.Color(0x00b140) },
                similarity: { value: 0.15 },
                smoothness: { value: 0.0 },
                uCanvasAspect: { value: 1.0 },
                uVideoAspect: { value: 9 / 16 },
            },
            vertexShader: VERTEX_SHADER,
            fragmentShader: FRAGMENT_SHADER,
        });

        const plane = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
        scene.add(plane);

        let animId = 0;
        function animate() {
            animId = requestAnimationFrame(animate);
            renderer.render(scene, camera);
        }
        animate();

        stateRef.current = { renderer, scene, camera, material, texture, animId };
        const onResize = () => resizeCanvas();
        window.addEventListener('resize', onResize);

        return () => {
            window.removeEventListener('resize', onResize);
            cancelAnimationFrame(animId);
            material.dispose();
            texture.dispose();
            plane.geometry.dispose();
            renderer.dispose();
            stateRef.current = null;
        };
    }, [enabled, canvasRef, videoRef, resizeCanvas]);

    return { resizeCanvas, resample };
}
