/**
 * PLAYER V2.5 - Director Bible Compliant
 * Clean, compliant implementation following V2.5 Architecture
 * Redundant code removed, proper section handling implemented
 */

// ============================================
// CONFIGURATION
// ============================================
const AVATAR_URL = "/player/assets/avatar_placeholder.mp4";

// Determine job ID from URL parameter or derive from current path
const urlParams = new URLSearchParams(window.location.search);
const JOB_ID = urlParams.get('job');

// Derive BASE_PATH from current URL location when accessed directly from job folder
const CURRENT_PATH = new URL('.', window.location.href).pathname;
const IS_JOB_FOLDER = CURRENT_PATH.includes('/jobs/') || CURRENT_PATH.includes('/player/jobs/');

// Set paths based on whether we have a job ID or are in a job folder
let BASE_PATH, PRESENTATION_PATH, SOURCE_MARKDOWN_PATH;
if (JOB_ID) {
  BASE_PATH = `/player/jobs/${JOB_ID}/`;
  PRESENTATION_PATH = `/player/jobs/${JOB_ID}/presentation.json`;
  SOURCE_MARKDOWN_PATH = `/player/jobs/${JOB_ID}/source_markdown.md`;
} else if (IS_JOB_FOLDER) {
  BASE_PATH = CURRENT_PATH;
  PRESENTATION_PATH = CURRENT_PATH + 'presentation.json';
  SOURCE_MARKDOWN_PATH = CURRENT_PATH + 'source_markdown.md';
} else {
  BASE_PATH = '/player_v2/';
  PRESENTATION_PATH = 'presentation.json';
  SOURCE_MARKDOWN_PATH = 'source_markdown.md';
}

// Media path resolver - handles audio, video, avatar, and image paths
function resolveMediaPath(path, type = 'audio') {
  if (!path) return '';

  // Handle Windows paths with backslashes (from JSON)
  if (path.includes(':\\') || path.includes('\\') || path.includes('\u005C')) {
    path = path.replace(/\\/g, '/').replace(/\u005C/g, '/');
    const parts = path.split('/');
    path = parts[parts.length - 1];
    console.log(`[V2.5] Extracted filename from Windows path: ${path}`);
  }

  // If path starts with /jobs/, return as-is
  if (path.startsWith('/jobs/') || path.startsWith('/player/jobs/')) {
    return path;
  }

  // If path is already HTTP URL, return as-is
  if (path.startsWith('http')) {
    return path;
  }

  // If path contains subfolder structure, prepend BASE_PATH
  if (path.includes('avatars/') || path.includes('videos/') || path.includes('audio/') || path.includes('images/')) {
    return BASE_PATH + path;
  }

  // Simple filename - prepend BASE_PATH + appropriate folder
  if (type === 'avatar') return BASE_PATH + 'avatars/' + path;
  if (type === 'video') return BASE_PATH + 'videos/' + path;
  if (type === 'image') return BASE_PATH + 'images/' + path;
  if (type === 'audio') return BASE_PATH + 'audio/' + path;

  return BASE_PATH + path;
}

// ============================================
// STATE
// ============================================
let lessonData = null;
let sourceMarkdown = "";
let slides = [];
let currentSlideIndex = 0;
let isPlaying = false;
let currentSegmentIndex = 0;
let slideEnded = false;

// DOM Elements
let stage, contentLayer, contentBox, avatarLayer, avatarVideo, avatarCanvas, avatarCtx;
let sectionTitle, headerTitle;
let videoLayer, contentVideo, narrationAudio;
let btnPlay, btnPrev, btnNext, slidePicker;
let timelineFill, timelineHandle, timeDisplay;
let devPanel, btnDev;

// Reveal state
let revealItems = [];
let chromaThreshold = 100;
let devModeEnabled = false;

// Time Source State (Avatar Video only per V2.5)
let activeTimeSource = null; // Will be set to avatarVideo in loadSlide
let useTimerFallback = false;

// Beat video playlist for multi-segment videos
let beatVideoPlaylist = [];
let currentBeatIndex = -1;

// Timer fallback object
const timerFallback = {
  currentTime: 0,
  duration: 30,
  paused: true,
  intervalId: null,
  
  play() {
    if (!this.paused) return;
    this.paused = false;
    this.intervalId = setInterval(() => {
      this.currentTime += 0.1;
      if (this.currentTime >= this.duration) {
        this.pause();
        onSlideEnd();
      }
      if (typeof this.ontimeupdate === 'function') {
        this.ontimeupdate();
      }
    }, 100);
  },
  
  pause() {
    this.paused = true;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  },
  
  reset(duration) {
    this.pause();
    this.currentTime = 0;
    this.duration = duration || 30;
  },
  
  addEventListener(event, handler) {
    if (event === 'timeupdate') {
      this.ontimeupdate = handler;
    } else if (event === 'ended') {
      this.onended = handler;
    }
  },
  
  removeEventListener(event, handler) {
    if (event === 'timeupdate') {
      this.ontimeupdate = null;
    } else if (event === 'ended') {
      this.onended = null;
    }
  }
};

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', init);

async function init() {
  cacheDOMElements();
  setupEventListeners();
  await loadPresentation();

  // Check URL hash for starting slide (#slide=N)
  const hash = window.location.hash;
  const match = hash.match(/slide=(\d+)/);
  if (match) {
    const startSlide = parseInt(match[1]);
    if (startSlide > 0 && startSlide <= slides.length) {
      loadSlide(startSlide - 1);
    }
  }
}

function cacheDOMElements() {
  stage = document.getElementById('stage');
  contentLayer = document.getElementById('content-layer');
  contentBox = document.getElementById('content-box');
  sectionTitle = document.getElementById('section-title');
  headerTitle = document.getElementById('header-title');
  avatarLayer = document.getElementById('avatar-layer');
  avatarVideo = document.getElementById('avatar-video');
  avatarCanvas = document.getElementById('avatar-canvas');
  avatarCtx = avatarCanvas.getContext('2d', { willReadFrequently: true });
  videoLayer = document.getElementById('video-layer');
  contentVideo = document.getElementById('content-video');
  narrationAudio = document.getElementById('narration-audio');
  btnPlay = document.getElementById('btn-play');
  btnPrev = document.getElementById('btn-prev');
  btnNext = document.getElementById('btn-next');
  slidePicker = document.getElementById('slide-picker');
  timelineFill = document.getElementById('timeline-fill');
  timelineHandle = document.getElementById('timeline-handle');
  timeDisplay = document.getElementById('time-display');
  devPanel = document.getElementById('dev-panel');
  btnDev = document.getElementById('btn-dev');
}

function setupEventListeners() {
  btnPlay.addEventListener('click', togglePlay);
  btnPrev.addEventListener('click', prevSlide);
  btnNext.addEventListener('click', nextSlide);
  slidePicker.addEventListener('change', (e) => loadSlide(parseInt(e.target.value)));

  // Content video ended handler
  contentVideo.addEventListener('ended', onContentVideoEnd);
  contentVideo.onerror = (e) => {
    if (contentVideo.src && !contentVideo.src.includes('player_v2')) {
      console.error('[V2.5] Content video error:', contentVideo.error);
    }
  };

  document.getElementById('timeline-track').addEventListener('click', seekTimeline);
  document.getElementById('btn-fullscreen').addEventListener('click', toggleFullscreen);

  // Dev panel controls
  if (btnDev) btnDev.addEventListener('click', toggleDevPanel);
  setupDevControls();

  // Keyboard shortcuts
  document.addEventListener('keydown', handleKeyPress);
}

function handleKeyPress(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  
  switch(e.key) {
    case ' ':
      e.preventDefault();
      togglePlay();
      break;
    case 'ArrowLeft':
      e.preventDefault();
      prevSlide();
      break;
    case 'ArrowRight':
      e.preventDefault();
      nextSlide();
      break;
    case 'f':
      toggleFullscreen();
      break;
  }
}

// ============================================
// PLAYBACK CONTROLS
// ============================================
function togglePlay() {
  if (isPlaying) {
    pause();
  } else {
    play();
  }
}

function play() {
  if (slideEnded) {
    // Restart current slide
    loadSlide(currentSlideIndex);
    slideEnded = false;
  }

  isPlaying = true;
  btnPlay.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20"><rect x="6" y="4" width="3" height="12" fill="white"/><rect x="11" y="4" width="3" height="12" fill="white"/></svg>';
  
  if (activeTimeSource) {
    if (activeTimeSource === timerFallback) {
      activeTimeSource.play();
    } else {
      activeTimeSource.play().catch(e => {
        console.error('[V2.5] Play failed:', e);
      });
    }
  }

  // Resume content video if it's currently showing
  if (contentVideo && !contentVideo.paused && !videoLayer.classList.contains('hidden')) {
    contentVideo.play().catch(e => console.log('[V2.5] Content video play failed:', e));
  }

  console.log('[V2.5] Playback started');
}

function pause() {
  isPlaying = false;
  btnPlay.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20"><path d="M6 4 L16 10 L6 16 Z" fill="white"/></svg>';
  
  pauseAllMedia();
  console.log('[V2.5] Playback paused');
}

function pauseAllMedia() {
  if (avatarVideo && !avatarVideo.paused) avatarVideo.pause();
  if (contentVideo && !contentVideo.paused) contentVideo.pause();
  if (timerFallback && !timerFallback.paused) timerFallback.pause();
}

function nextSlide() {
  if (currentSlideIndex < slides.length - 1) {
    loadSlide(currentSlideIndex + 1);
  }
}

function prevSlide() {
  if (currentSlideIndex > 0) {
    loadSlide(currentSlideIndex - 1);
  }
}

// ============================================
// V2.5 CORE: LOAD SLIDE WITH SECTION-SPECIFIC HANDLING
// ============================================
function loadSlide(index) {
  if (!slides[index]) {
    console.error('[V2.5] Invalid slide index:', index);
    return;
  }

  isPlaying = false;
  slideEnded = false;
  currentSlideIndex = index;
  currentSegmentIndex = 0;
  currentBeatIndex = -1;
  beatVideoPlaylist = [];

  // Update UI
  slidePicker.value = index;
  const slide = slides[index];
  const sectionType = slide.section_type || 'content';

  console.log(`[V2.5] Loading slide ${index + 1}: ${sectionType} - ${slide.title || 'Untitled'}`);

  // Stop any playing media first
  pauseAllMedia();

  if (activeTimeSource) {
    activeTimeSource.currentTime = 0;
    unbindTimeEvents(activeTimeSource);
  }

  // Clean up event handlers
  if (avatarVideo) {
    avatarVideo.onloadeddata = null;
    avatarVideo.onplay = null;
    avatarVideo.onpause = null;
    avatarVideo.onerror = null;
  }
  if (contentVideo) {
    contentVideo.src = '';
    contentVideo.onloadeddata = null;
    contentVideo.onerror = null;
    contentVideo.onended = null;
  }

  // Reset all layer states
  contentBox.innerHTML = '';
  videoLayer.classList.add('hidden');
  contentLayer.classList.remove('video-mode');
  contentLayer.classList.remove('hidden');

  // V2.5: Apply section-specific display directives
  applyV25DisplayDirectives(slide);

  // Set section title (V2.5: INTRO has no title)
  if (sectionType !== 'intro' && slide.title) {
    sectionTitle.textContent = slide.title;
    sectionTitle.style.display = 'flex';
  } else {
    sectionTitle.textContent = '';
    sectionTitle.style.display = 'none';
  }

  setStageMode(sectionType);

  // V2.5: Section-specific rendering
  switch (sectionType) {
    case 'intro':
      renderIntro(slide);
      break;
    case 'summary':
      renderSummary(slide);
      break;
    case 'quiz':
      renderQuiz(slide);
      break;
    case 'memory':
      renderMemory(slide);
      break;
    case 'recap':
      renderRecap(slide);
      break;
    case 'content':
    case 'example':
    default:
      renderContent(slide);
      break;
  }

  setupMediaSource(slide);

  // Update header title
  if (headerTitle) {
    if (sectionType === 'intro') {
      headerTitle.textContent = lessonData?.lesson_title || 'Lesson';
    } else {
      headerTitle.textContent = slide.title || lessonData?.lesson_title || 'Lesson';
    }
  }

  requestAnimationFrame(async () => {
    fitContentToContainer(contentBox);
    setupProgressiveReveal(slide);
    updateDevInfo();

    // Typeset LaTeX after content is rendered
    await typesetMath(contentBox);

    // Force initial reveal tick (critical for direct jumps)
    handleTimeUpdateMain();
  });
}

// ============================================
// V2.5 DISPLAY DIRECTIVES: SECTION-SPECIFIC LAYER CONTROL
// ============================================
function applyV25DisplayDirectives(slide) {
  const sectionType = slide.section_type || 'content';

  // V2.5 Director Bible Section Definitions:
  switch (sectionType) {
    case 'intro':
      // INTRO: text_layer: HIDE, visual_layer: HIDE, avatar_layer: SHOW
      contentLayer.classList.add('hidden');
      videoLayer.classList.add('hidden');
      avatarLayer.style.display = 'block';
      console.log('[V2.5] INTRO: Avatar ONLY mode');
      break;

    case 'summary':
      // SUMMARY: text_layer: SHOW, avatar_layer: SHOW
      contentLayer.classList.remove('hidden');
      videoLayer.classList.add('hidden');
      avatarLayer.style.display = 'block';
      console.log('[V2.5] SUMMARY: Text + Avatar mode');
      break;

    case 'content':
    case 'example':
      // CONTENT: Teach → Show pattern (handled in segments)
      // Default: Show text, hide video initially
      contentLayer.classList.remove('hidden');
      videoLayer.classList.add('hidden');
      avatarLayer.style.display = 'block';
      console.log('[V2.5] CONTENT: Teach phase (Text + Avatar)');
      break;

    case 'quiz':
      // QUIZ: text_layer: SHOW, visual_layer: HIDE
      contentLayer.classList.remove('hidden');
      videoLayer.classList.add('hidden');
      avatarLayer.style.display = 'block';
      console.log('[V2.5] QUIZ: Question display mode');
      break;

    case 'memory':
      // MEMORY: text_layer: SHOW, avatar_layer: SHOW
      contentLayer.classList.remove('hidden');
      videoLayer.classList.add('hidden');
      avatarLayer.style.display = 'block';
      console.log('[V2.5] MEMORY: Flashcard mode');
      break;

    case 'recap':
      // RECAP: visual_layer: SHOW (FULL), text_layer: HIDE
      contentLayer.classList.add('hidden');
      videoLayer.classList.remove('hidden');
      videoLayer.classList.add('fullscreen');
      avatarLayer.style.display = 'block'; // Avatar still present per V2.5
      console.log('[V2.5] RECAP: Full-screen video mode');
      break;

    default:
      contentLayer.classList.remove('hidden');
      videoLayer.classList.add('hidden');
      avatarLayer.style.display = 'block';
  }
}

// ============================================
// V2.5 SECTION RENDERERS
// ============================================
function renderIntro(slide) {
  // V2.5: INTRO = AVATAR ONLY (Clean Start)
  console.log('[V2.5] INTRO: Clean avatar-only start');
  contentBox.innerHTML = '';
  // All visibility handled by applyV25DisplayDirectives
}

function setStageMode(sectionType) {
  stage.className = '';

  if (sectionType === 'intro') {
    stage.classList.add('mode-intro');
  }
}

function renderSummary(slide) {
  // V2.5: SUMMARY = Bullet List with Text
  console.log('[V2.5] SUMMARY: Rendering bullet points');

  contentBox.innerHTML = '';

  const collectedBullets = new Set();

  // Strategy 1: Visual Beats (Primary for V2.5)
  if (slide.visual_beats && slide.visual_beats.length > 0) {
    slide.visual_beats.forEach(beat => {
      if (beat.visual_type === 'bullet_list' && beat.display_text) {
        if (Array.isArray(beat.display_text)) {
          beat.display_text.forEach(item => {
            const text = (typeof item === 'string' ? item : (item.text || '')).trim();
            if (text) collectedBullets.add(sanitizeMarkdown(text));
          });
        } else if (typeof beat.display_text === 'string') {
          const text = beat.display_text.trim();
          if (text) collectedBullets.add(sanitizeMarkdown(text));
        }
      }
    });
  }

  // Strategy 2: Slide-Level Visual Content
  if (collectedBullets.size === 0 && slide.visual_content?.bullet_points) {
    slide.visual_content.bullet_points.forEach(bp => {
      const text = (typeof bp === 'string' ? bp : (bp.text || '')).trim();
      if (!bp.level || bp.level === 1) {
        collectedBullets.add(sanitizeMarkdown(text));
      }
    });
  }

  // Strategy 3: Narration Segments (Fallback)
  if (collectedBullets.size === 0) {
    const segments = slide.narration?.segments || [];
    segments.forEach(seg => {
      const vc = seg.visual_content;
      const bulletData = vc?.bullet_points || vc?.items || [];
      bulletData.forEach(bp => {
        const text = (typeof bp === 'string' ? bp : (bp.text || '')).trim();
        if (text && (!bp.level || bp.level === 1)) {
          collectedBullets.add(sanitizeMarkdown(text));
        }
      });
    });
  }

  const allBulletsArray = Array.from(collectedBullets);
  const list = document.createElement('ul');
  list.className = 'summary-list';

  allBulletsArray.forEach((text, i) => {
    const item = document.createElement('li');
    item.className = 'summary-item reveal-hidden';
    item.id = `summary-bullet-${i}`;
    item.innerHTML = `<span class="summary-marker">✓</span><span class="summary-text">${text}</span>`;
    list.appendChild(item);
  });

  contentBox.appendChild(list);

  window.summaryBulletCount = allBulletsArray.length;
  console.log(`[V2.5] SUMMARY: ${allBulletsArray.length} bullets ready for progressive reveal`);
}

function renderContent(slide) {
  // V2.5: CONTENT = Teach → Show Pattern
  console.log('[V2.5] CONTENT: Teaching content with optional video');

  const videoPath = slide.video_path || slide.content_video_path;
  const beatVideoPaths = slide.beat_video_paths || [];
  const hasVideo = videoPath || beatVideoPaths.length > 0;

  // Render text content first (TEACH phase)
  if (slide.markdown_content && slide.markdown_content.length > 0) {
    console.log(`[V2.5] Rendering from Markdown Source (${slide.markdown_content.length} lines)`);
    
    const fullMarkdown = slide.markdown_content.join('\n');
    const mdContainer = document.createElement('div');
    mdContainer.className = 'markdown-content-container';
    mdContainer.innerHTML = sanitizeMarkdown(fullMarkdown);
    contentBox.appendChild(mdContainer);

    // Handle images
    const images = contentBox.querySelectorAll('img');
    images.forEach(img => {
      img.style.display = 'block';
      img.style.maxWidth = '100%';
      img.style.margin = '16px auto';
      img.onerror = () => {
        console.warn('[V2.5] Image failed to load:', img.src);
        img.style.display = 'none';
      };
    });
  } else if (slide.visual_beats && slide.visual_beats.length > 0) {
    console.log(`[V2.5] Rendering ${slide.visual_beats.length} visual beats`);
    
    slide.visual_beats.forEach((beat, i) => {
      const beatDiv = document.createElement('div');
      beatDiv.className = 'beat-block reveal-hidden'; // Add reveal-hidden for progressive reveal
      beatDiv.id = `beat-${i}`;

      // Handle images
      if (beat.visual_type === 'image' || beat.visual_type === 'diagram') {
        const imgPath = beat.image_id || beat.image_path || beat.file_path;
        if (imgPath) {
          const imgContainer = document.createElement('div');
          imgContainer.className = 'image-container';
          const img = document.createElement('img');
          img.className = 'content-image';
          img.src = resolveMediaPath(imgPath, 'image');
          img.alt = beat.description || 'Visual beat image';
          imgContainer.appendChild(img);

          if (beat.description) {
            const cap = document.createElement('div');
            cap.className = 'image-caption';
            cap.textContent = beat.description;
            imgContainer.appendChild(cap);
          }
          beatDiv.appendChild(imgContainer);
        }
      }

      // Handle text
      if (beat.display_text) {
        const texts = Array.isArray(beat.display_text) ? beat.display_text : [beat.display_text];
        texts.forEach(text => {
          if (!text) return;
          const p = document.createElement('div');
          p.className = 'paragraph-block'; // Remove reveal-hidden from individual paragraphs
          p.id = `content-item-${i}-${texts.indexOf(text)}`;
          p.innerHTML = sanitizeMarkdown(text);
          beatDiv.appendChild(p);
        });
      }

      if (beatDiv.children.length > 0) {
        contentBox.appendChild(beatDiv);
      }
    });
  }

  // Setup video for SHOW phase (triggered by segments)
  if (hasVideo) {
    if (beatVideoPaths.length > 1) {
      beatVideoPlaylist = buildBeatPlaylistWithTiming(slide);
      if (beatVideoPlaylist.length > 0) {
        loadBeatVideo(0);
      }
    } else if (videoPath) {
      const fullPath = resolveMediaPath(videoPath, 'video');
      contentVideo.src = fullPath;
      console.log(`[V2.5] Video loaded for SHOW phase: ${fullPath}`);
    }
  }
}

function renderRecap(slide) {
  // V2.5: RECAP = Full-Screen Video ONLY (Text Hidden)
  console.log('[V2.5] RECAP: Cinematic full-screen video');
  
  contentBox.innerHTML = '';
  
  const videoPath = slide.video_path || slide.content_video_path;
  const beatVideoPaths = slide.beat_video_paths || [];

  if (beatVideoPaths.length > 0) {
    beatVideoPlaylist = buildBeatPlaylistWithTiming(slide);
    if (beatVideoPlaylist.length > 0) {
      videoLayer.classList.remove('hidden');
      videoLayer.classList.add('fullscreen');
      loadBeatVideo(0);
    }
  } else if (videoPath) {
    const fullPath = resolveMediaPath(videoPath, 'video');
    contentVideo.src = fullPath;
    videoLayer.classList.remove('hidden');
    videoLayer.classList.add('fullscreen');
    console.log(`[V2.5] RECAP video: ${fullPath}`);
  }
}

function renderQuiz(slide) {
  // V2.5: QUIZ = 3-Step Dance (Introduce → Pause → Reveal)
  console.log('[V2.5] QUIZ: Rendering questions with 3-step choreography');

  contentBox.innerHTML = '';

  const questions = slide.quiz_questions || [];

  questions.forEach((q, i) => {
    const card = document.createElement('div');
    card.className = 'quiz-card quiz-hidden';
    card.id = `quiz-${i}`;

    const questionDiv = document.createElement('div');
    questionDiv.className = 'quiz-question';
    questionDiv.textContent = q.question || q.question_text || '';
    card.appendChild(questionDiv);

    const choices = q.choices || q.options || [];
    const choicesDiv = document.createElement('div');
    choicesDiv.className = 'quiz-choices';

    choices.forEach((choice, j) => {
      const choiceDiv = document.createElement('div');
      choiceDiv.className = 'quiz-choice';
      
      const letter = document.createElement('div');
      letter.className = 'choice-letter';
      letter.textContent = String.fromCharCode(65 + j);
      choiceDiv.appendChild(letter);

      const text = document.createElement('div');
      text.className = 'choice-text';
      text.textContent = typeof choice === 'string' ? choice : choice.text || '';
      choiceDiv.appendChild(text);

      choicesDiv.appendChild(choiceDiv);
    });

    card.appendChild(choicesDiv);

    if (q.explanation) {
      const explanation = document.createElement('div');
      explanation.className = 'quiz-explanation';
      explanation.style.display = 'none';
      explanation.textContent = q.explanation;
      card.appendChild(explanation);
    }

    contentBox.appendChild(card);
  });

  console.log(`[V2.5] QUIZ: ${questions.length} questions rendered`);
}

function renderMemory(slide) {
  // V2.5: MEMORY = Flashcards (Front → Pause → Back Flip)
  console.log('[V2.5] MEMORY: Rendering flashcards');

  contentBox.innerHTML = '';

  const flashcards = slide.flashcards || slide.memory_items || [];
  const container = document.createElement('div');
  container.className = 'flashcard-container';

  flashcards.forEach((card, i) => {
    const cardDiv = document.createElement('div');
    cardDiv.className = 'flashcard';
    cardDiv.id = `flashcard-${i}`;

    const front = document.createElement('div');
    front.className = 'flashcard-front';
    front.innerHTML = `<strong>${card.front || card.term || ''}</strong>`;
    cardDiv.appendChild(front);

    const back = document.createElement('div');
    back.className = 'flashcard-back';
    back.innerHTML = sanitizeMarkdown(card.back || card.definition || card.mnemonic || '');
    cardDiv.appendChild(back);

    container.appendChild(cardDiv);
  });

  contentBox.appendChild(container);
  console.log(`[V2.5] MEMORY: ${flashcards.length} flashcards rendered`);
}

// ============================================
// MEDIA SOURCE SETUP
// ============================================
function setupMediaSource(slide) {
  const avatarPath = slide.avatar_video ? resolveMediaPath(slide.avatar_video, 'avatar') : null;

  if (avatarPath) {
    avatarLayer.style.display = 'block';
    avatarVideo.src = avatarPath;
    avatarVideo.muted = false;

    useTimerFallback = false;
    activeTimeSource = avatarVideo;
    bindTimeEvents(avatarVideo);

    console.log('[V2.5] Avatar set as time source:', avatarPath);
  } else {
    // NO AVATAR → Timer Fallback
    avatarVideo.pause();
    avatarVideo.removeAttribute('src');
    avatarVideo.load();

    avatarLayer.style.display = 'none';

    useTimerFallback = true;
    activeTimeSource = timerFallback;

    const duration = getTotalDuration(slide);
    timerFallback.reset(duration);
    bindTimeEvents(timerFallback);

    console.log('[V2.5] No avatar — using timer fallback');
  }
}

function getTotalDuration(slide) {
  const segments = slide.narration?.segments || [];
  return segments.reduce((sum, seg) => sum + (seg.duration_seconds || 5), 0) || 30;
}

// ============================================
// TIME EVENTS BINDING
// ============================================
function bindTimeEvents(source) {
  unbindTimeEvents(source);

  if (source === timerFallback) {
    source.addEventListener('timeupdate', handleTimeUpdateMain);
  } else {
    source.addEventListener('timeupdate', handleTimeUpdateMain);
    source.addEventListener('ended', onSlideEnd);
  }
}

function unbindTimeEvents(source) {
  if (!source) return;
  
  if (source === timerFallback) {
    source.removeEventListener('timeupdate', handleTimeUpdateMain);
  } else {
    source.removeEventListener('timeupdate', handleTimeUpdateMain);
    source.removeEventListener('ended', onSlideEnd);
  }
}

// ============================================
// TIME UPDATE HANDLER (Main Loop)
// ============================================
function handleTimeUpdateMain() {
  if (!activeTimeSource) return;

  const currentTime = getTime();
  const duration = getDuration();

  // Update timeline
  if (duration > 0) {
    const progress = Math.min(currentTime / duration, 1);
    timelineFill.style.width = `${progress * 100}%`;
    timelineHandle.style.left = `${progress * 100}%`;
  }

  // Update time display
  timeDisplay.textContent = `${formatTime(currentTime)} / ${formatTime(duration)}`;

  // V2.5: Section-specific progressive reveals
  const slide = slides[currentSlideIndex];
  if (!slide) return;

  const sectionType = slide.section_type || 'content';

  switch (sectionType) {
    case 'summary':
      updateSummaryProgressiveReveal();
      break;
    case 'quiz':
      updateQuizProgressiveReveal();
      break;
    case 'memory':
      updateMemoryFlip();
      break;
    case 'content':
    case 'example':
      updateContentProgressiveReveal(); // Progressive beat reveal
      updateContentTeachShowPhase(); // Teach→Show video switching
      break;
  }

  // Update beat video timing
  checkBeatVideoSwitch();

  // Update dev panel if enabled
  if (devModeEnabled) updateDevInfo();
}

// ============================================
// V2.5 PROGRESSIVE REVEAL FUNCTIONS
// ============================================
function updateSummaryProgressiveReveal() {
  const slide = slides[currentSlideIndex];
  if (!slide) return;

  const currentTime = getTime();
  const segments = slide.narration?.segments || [];
  const visualBeats = slide.visual_beats?.filter(b => b.visual_type === 'bullet_list') || [];
  
  if (visualBeats.length === 0) return;

  // CRITICAL FIX: start_time/end_time in JSON are SEGMENT INDICES, not seconds
  // We need to map them to actual time using segment durations
  
  // Build cumulative time map for segments
  const segmentTimeMap = {};
  let cumulativeTime = 0;
  
  segments.forEach((seg, index) => {
    segmentTimeMap[index] = {
      startTime: cumulativeTime,
      endTime: cumulativeTime + (seg.duration_seconds || 5),
      duration: seg.duration_seconds || 5
    };
    cumulativeTime += (seg.duration_seconds || 5);
  });

  // Reveal bullets based on their segment indices mapped to actual time
  visualBeats.forEach((beat, beatIndex) => {
    const segmentIndex = beat.start_time; // This is actually a segment index (0, 1, 2, 3...)
    const segmentTiming = segmentTimeMap[segmentIndex];
    
    if (!segmentTiming) {
      console.warn(`[V2.5] Beat ${beatIndex}: segment ${segmentIndex} not found`);
      return;
    }

    const actualStartTime = segmentTiming.startTime;
    const bullet = document.getElementById(`summary-bullet-${beatIndex}`);

    if (bullet && currentTime >= actualStartTime && bullet.classList.contains('reveal-hidden')) {
      bullet.classList.remove('reveal-hidden');
      bullet.classList.add('reveal-visible');
      console.log(`[V2.5] ✓ Revealed bullet ${beatIndex + 1} at ${currentTime.toFixed(1)}s (segment ${segmentIndex} @ ${actualStartTime.toFixed(1)}s)`);
    }
  });
}

function updateQuizProgressiveReveal() {
  // V2.5: Quiz 3-Step Dance
  // Step 1 (Introduce): Show question + options
  // Step 2 (Pause): Thinking time (3-5s)
  // Step 3 (Reveal): Highlight correct answer

  const slide = slides[currentSlideIndex];
  if (!slide) return;

  const currentTime = getTime();
  const segments = slide.narration?.segments || [];
  const questions = slide.quiz_questions || [];

  // Find current segment
  let segmentIndex = 0;
  let accumulatedTime = 0;
  for (let i = 0; i < segments.length; i++) {
    const segDuration = segments[i].duration_seconds || 5;
    if (currentTime < accumulatedTime + segDuration) {
      segmentIndex = i;
      break;
    }
    accumulatedTime += segDuration;
  }

  // Quiz segments pattern: Q1-Introduce, Q1-Pause, Q1-Reveal, Q2-Introduce, etc.
  const questionIndex = Math.floor(segmentIndex / 3);
  const stepInQuestion = segmentIndex % 3;

  const quizCard = document.getElementById(`quiz-${questionIndex}`);
  if (!quizCard) return;

  // Step 1: Introduce (show question)
  if (quizCard.classList.contains('quiz-hidden')) {
    quizCard.classList.remove('quiz-hidden');
    quizCard.classList.add('quiz-active');
    console.log(`[V2.5] QUIZ: Showing Q${questionIndex + 1}`);
  }

  // Step 3: Reveal (show answer)
  if (stepInQuestion === 2) {
    const question = questions[questionIndex];
    if (!question) return;

    const correctIndex = question.correct_index ?? question.answer_index ?? 0;
    const choices = quizCard.querySelectorAll('.quiz-choice');

    choices.forEach((choice, idx) => {
      if (idx === correctIndex) {
        choice.classList.add('correct-revealed');
        const letter = choice.querySelector('.choice-letter');
        if (letter) letter.classList.add('correct');
        console.log(`[V2.5] QUIZ: Revealed answer Q${questionIndex + 1} - Option ${String.fromCharCode(65 + correctIndex)}`);
      }
    });

    // Show explanation
    const explanation = quizCard.querySelector('.quiz-explanation');
    if (explanation) explanation.style.display = 'block';
  }
}

function updateMemoryFlip() {
  // V2.5: Memory Flashcard Flip
  // Front shows → Pause → Back Flips (~10s per side)

  const slide = slides[currentSlideIndex];
  if (!slide) return;

  const flashcards = slide.flashcards || slide.memory_items || [];
  if (flashcards.length === 0) return;

  const currentTime = getTime();
  const totalDuration = getDuration() || 60;

  const timePerCard = totalDuration / flashcards.length;
  const flipDelay = timePerCard * 0.5;

  for (let i = 0; i < flashcards.length; i++) {
    const card = document.getElementById(`flashcard-${i}`);
    if (!card) continue;

    const cardStartTime = i * timePerCard;
    const cardFlipTime = cardStartTime + flipDelay;

    // Show card
    if (currentTime >= cardStartTime && !card.classList.contains('memory-visible')) {
      card.classList.add('memory-visible');
      console.log(`[V2.5] MEMORY: Showing card ${i + 1}`);
    }

    // Flip card
    if (currentTime >= cardFlipTime && !card.classList.contains('flipped')) {
      card.classList.add('flipped');
      console.log(`[V2.5] MEMORY: Flipped card ${i + 1}`);
    }
  }
}

function updateContentProgressiveReveal() {
  // V2.5: Progressive reveal for content beats (text, images, formulas)
  const slide = slides[currentSlideIndex];
  const sectionType = slide?.section_type || '';
  
  if (sectionType !== 'content' && sectionType !== 'example') return;

  const visualBeats = slide.visual_beats || [];
  if (visualBeats.length === 0) return;

  const segments = slide.narration?.segments || [];
  const currentTime = getTime();

  // Build segment time map
  const segmentTimeMap = {};
  let cumulativeTime = 0;
  segments.forEach((seg, index) => {
    segmentTimeMap[index] = {
      startTime: cumulativeTime,
      endTime: cumulativeTime + (seg.duration_seconds || 5)
    };
    cumulativeTime += (seg.duration_seconds || 5);
  });

  // Reveal beats progressively
  visualBeats.forEach((beat, beatIndex) => {
    const beatDiv = document.getElementById(`beat-${beatIndex}`);
    if (!beatDiv) return;

    let revealTime = 0;

    // Strategy 1: Use beat.start_time if present (segment index)
    if (beat.start_time !== null && beat.start_time !== undefined) {
      const timing = segmentTimeMap[beat.start_time];
      if (timing) {
        revealTime = timing.startTime;
      }
    } 
    // Strategy 2: Infer timing - distribute beats evenly across TEACH segments
    else {
      // Calculate total teach duration (before video trigger)
      const totalDuration = getDuration();
      const teachDuration = totalDuration * 0.7; // 70% is teach, 30% is video
      const timePerBeat = teachDuration / visualBeats.length;
      revealTime = beatIndex * timePerBeat;
    }

    // Reveal when time is reached
    if (currentTime >= revealTime && beatDiv.classList.contains('reveal-hidden')) {
      beatDiv.classList.remove('reveal-hidden');
      beatDiv.classList.add('reveal-visible');
      console.log(`[V2.5] ✓ Revealed beat ${beatIndex} at ${currentTime.toFixed(1)}s (target: ${revealTime.toFixed(1)}s)`);
    }
  });
}

function updateContentTeachShowPhase() {
  // V2.5: Content Teach → Show Pattern
  // TEACH: Avatar explains with text/diagrams visible
  // SHOW: Video demonstrates (text hidden, video fullscreen)

  const slide = slides[currentSlideIndex];
  if (!slide) return;

  const currentTime = getTime();
  const segments = slide.narration?.segments || [];

  // Find current segment
  let segmentIndex = 0;
  let accumulatedTime = 0;
  for (let i = 0; i < segments.length; i++) {
    const segDuration = segments[i].duration_seconds || 5;
    if (currentTime < accumulatedTime + segDuration) {
      segmentIndex = i;
      break;
    }
    accumulatedTime += segDuration;
  }

  const segment = segments[segmentIndex];
  if (!segment) return;

  const purpose = (segment.purpose || '').toLowerCase();

  // TEACH phase: show text, hide video
  if (purpose === 'teach' || purpose === 'explain') {
    contentLayer.classList.remove('hidden');
    videoLayer.classList.add('hidden');
    videoLayer.classList.remove('fullscreen');
  }

  // SHOW phase: hide text, show video fullscreen
  if (purpose === 'show' || purpose === 'demonstrate') {
    contentLayer.classList.add('hidden');
    videoLayer.classList.remove('hidden');
    videoLayer.classList.add('fullscreen');

    // Start content video if not playing
    if (contentVideo.src && contentVideo.paused && isPlaying) {
      contentVideo.play().catch(e => console.log('[V2.5] Video play failed:', e));
    }
  }

  // WORKAROUND: Auto-trigger video at 70% of slide duration if no SHOW segment exists
  // This handles JSON files where segments only have purpose='introduce' or 'explain'
  const hasVideo = slide.video_path || (slide.beat_video_paths && slide.beat_video_paths.length > 0);
  const totalDuration = getDuration();
  const videoTriggerTime = totalDuration * 0.7; // 70% through the slide
  
  if (hasVideo && currentTime >= videoTriggerTime) {
    // Check if any segment has SHOW purpose
    const hasShowSegment = segments.some(s => {
      const p = (s.purpose || '').toLowerCase();
      return p === 'show' || p === 'demonstrate';
    });

    // If no SHOW segment exists, auto-trigger video
    if (!hasShowSegment && videoLayer.classList.contains('hidden')) {
      console.log(`[V2.5 WORKAROUND] Auto-triggering video at ${currentTime.toFixed(1)}s (70% mark)`);
      contentLayer.classList.add('hidden');
      videoLayer.classList.remove('hidden');
      videoLayer.classList.add('fullscreen');

      // Start content video if not playing
      if (contentVideo.src && contentVideo.paused && isPlaying) {
        contentVideo.play().catch(e => console.log('[V2.5] Video play failed:', e));
      }
    }
  }
}

// ============================================
// BEAT VIDEO HANDLING
// ============================================
function buildBeatPlaylistWithTiming(slide) {
  const beatVideoPaths = slide.beat_video_paths || [];
  const segments = slide.narration?.segments || [];
  const playlist = [];

  let accumulatedTime = 0;
  segments.forEach((seg, i) => {
    const duration = seg.duration_seconds || 5;
    const videoPath = beatVideoPaths[i];

    if (videoPath) {
      playlist.push({
        videoPath: resolveMediaPath(videoPath, 'video'),
        startTime: accumulatedTime,
        endTime: accumulatedTime + duration,
        segmentIndex: i
      });
    }

    accumulatedTime += duration;
  });

  return playlist;
}

function loadBeatVideo(index) {
  if (index < 0 || index >= beatVideoPlaylist.length) return;

  const beat = beatVideoPlaylist[index];
  currentBeatIndex = index;

  contentVideo.src = beat.videoPath;
  contentVideo.onloadeddata = () => {
    console.log(`[V2.5] Beat video ${index + 1}/${beatVideoPlaylist.length} loaded`);
  };

  console.log(`[V2.5] Loading beat video ${index + 1}: ${beat.videoPath}`);
}

function checkBeatVideoSwitch() {
  if (beatVideoPlaylist.length === 0) return;

  const currentTime = getTime();

  for (let i = 0; i < beatVideoPlaylist.length; i++) {
    const beat = beatVideoPlaylist[i];
    if (currentTime >= beat.startTime && currentTime < beat.endTime) {
      if (currentBeatIndex !== i) {
        loadBeatVideo(i);

        // Auto-play if currently playing
        if (isPlaying && contentVideo.paused) {
          contentVideo.play().catch(e => console.log('[V2.5] Beat video play failed:', e));
        }
      }
      break;
    }
  }
}

function onContentVideoEnd() {
  console.log('[V2.5] Content video ended');
  
  // If using beat videos, advance to next
  if (beatVideoPlaylist.length > 0 && currentBeatIndex < beatVideoPlaylist.length - 1) {
    loadBeatVideo(currentBeatIndex + 1);
    if (isPlaying) {
      contentVideo.play().catch(e => console.log('[V2.5] Next beat video play failed:', e));
    }
  }
}

// ============================================
// SLIDE END HANDLER
// ============================================
function onSlideEnd() {
  console.log('[V2.5] Slide ended');
  
  slideEnded = true;
  isPlaying = false;
  
  pauseAllMedia();

  // Auto-advance to next slide
  if (currentSlideIndex < slides.length - 1) {
    setTimeout(() => {
      nextSlide();
      setTimeout(() => play(), 300);
    }, 500);
  } else {
    console.log('[V2.5] Lesson complete');
  }
}

// ============================================
// TIMELINE CONTROLS
// ============================================
function seekTimeline(e) {
  const track = e.currentTarget;
  const rect = track.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const percentage = x / rect.width;
  const duration = getDuration();
  const newTime = duration * percentage;

  if (activeTimeSource) {
    activeTimeSource.currentTime = newTime;
    
    // Also seek content video if it's playing
    if (contentVideo && contentVideo.src && !videoLayer.classList.contains('hidden')) {
      const beatDuration = contentVideo.duration || 0;
      if (beatDuration > 0) {
        contentVideo.currentTime = Math.min(newTime, beatDuration);
      }
    }
  }

  console.log(`[V2.5] Seeked to ${formatTime(newTime)}`);
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.getElementById('player-container').requestFullscreen().catch(err => {
      console.error('[V2.5] Fullscreen error:', err);
    });
  } else {
    document.exitFullscreen();
  }
}

// ============================================
// UTILITY FUNCTIONS
// ============================================
function getTime() {
  if (!activeTimeSource) return 0;
  return activeTimeSource.currentTime || 0;
}

function getDuration() {
  if (!activeTimeSource) return 0;
  if (activeTimeSource === timerFallback) {
    return activeTimeSource.duration;
  }
  return activeTimeSource.duration || getTotalDuration(slides[currentSlideIndex]);
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// ============================================
// PROGRESSIVE REVEAL SETUP
// ============================================
function setupProgressiveReveal(slide) {
  // Already handled in section-specific renderers
  // This function can be extended for additional reveal patterns
}

// ============================================
// CHROMA KEYING
// ============================================
function syncCanvasSize() {
  if (avatarVideo.videoWidth > 0 && avatarVideo.videoHeight > 0) {
    avatarCanvas.width = avatarVideo.videoWidth;
    avatarCanvas.height = avatarVideo.videoHeight;
  }
}

function startChromaKeyLoop() {
  requestAnimationFrame(renderChromaFrame);
}

function renderChromaFrame() {
  if (avatarVideo.readyState < 2) {
    requestAnimationFrame(renderChromaFrame);
    return;
  }

  if (avatarCanvas.width !== avatarVideo.videoWidth && avatarVideo.videoWidth > 0) {
    syncCanvasSize();
  }

  if (avatarCanvas.width === 0 || avatarCanvas.height === 0) {
    requestAnimationFrame(renderChromaFrame);
    return;
  }

  try {
    avatarCtx.drawImage(avatarVideo, 0, 0, avatarCanvas.width, avatarCanvas.height);
    const frame = avatarCtx.getImageData(0, 0, avatarCanvas.width, avatarCanvas.height);
    const data = frame.data;

    // Green screen detection
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];

      if (g > chromaThreshold && g > r * 1.3 && g > b * 1.3) {
        data[i + 3] = 0; // Transparent
      }
    }

    avatarCtx.putImageData(frame, 0, 0);
  } catch (e) {
    console.error('[V2.5] Chroma key error:', e);
  }

  requestAnimationFrame(renderChromaFrame);
}

// Start chroma key loop on init
document.addEventListener('DOMContentLoaded', () => {
  if (avatarVideo) {
    startChromaKeyLoop();
  }
});

// ============================================
// MARKDOWN & LATEX
// ============================================
function sanitizeMarkdown(text) {
  if (!text) return '';

  // Preserve LaTeX expressions
  const latexPatterns = [];
  
  // Block LaTeX: $$...$$
  text = text.replace(/\$\$([^$]+)\$\$/g, (match, latex) => {
    latexPatterns.push(match);
    return `__LATEX_BLOCK_${latexPatterns.length - 1}__`;
  });

  // Inline LaTeX: $...$
  text = text.replace(/\$([^$]+)\$/g, (match, latex) => {
    latexPatterns.push(match);
    return `__LATEX_INLINE_${latexPatterns.length - 1}__`;
  });

  // Markdown Tables
  text = text.replace(/\|(.+)\|\n\s*\|[-:| ]+\|\s*\n((?:\|.*\|\n?)+)/g, (match, headerLine, bodyLines) => {
    const headers = headerLine.split('|').filter(c => c.trim()).map(c => c.trim());
    const headerHtml = '<thead><tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr></thead>';

    const rows = bodyLines.trim().split('\n').map(row => {
      const cells = row.split('|').filter(c => c.trim() !== '').map(c => c.trim());
      return '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
    }).join('');

    return `<div class="table-wrapper"><table class="md-table">${headerHtml}<tbody>${rows}</tbody></table></div>`;
  });

  // Markdown Lists
  text = text.replace(/^(\s*[\*\-]\s+.*(?:\n\s*[\*\-]\s+.*)*)/gm, (match) => {
    const items = match.split('\n').filter(l => l.trim());
    const listItems = items.map(item => `<li>${item.replace(/^\s*[\*\-]\s+/, '')}</li>`).join('');
    return `<ul class="md-list">${listItems}</ul>`;
  });

  text = text.replace(/^(\s*\d+\.\s+.*(?:\n\s*\d+\.\s+.*)*)/gm, (match) => {
    const items = match.split('\n').filter(l => l.trim());
    const listItems = items.map(item => `<li>${item.replace(/^\s*\d+\.\s+/, '')}</li>`).join('');
    return `<ol class="md-list">${listItems}</ol>`;
  });

  // Basic Formatting
  text = text.replace(/^#{1,6}\s*(.+)$/gm, '<h3>$1</h3>');
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/__([^_]+)__/g, '<strong>$1</strong>');
  text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  text = text.replace(/_([^_]+)_/g, '<em>$1</em>');
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
  text = text.replace(/^>\s*(.+)$/gm, '<blockquote>$1</blockquote>');
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

  // Restore LaTeX
  text = text.replace(/__LATEX_(BLOCK|INLINE)_(\d+)__/g, (match, type, idx) => {
    return latexPatterns[parseInt(idx)] || match;
  });

  return text.trim();
}

async function typesetMath(element) {
  if (typeof MathJax !== 'undefined' && MathJax.typesetPromise) {
    try {
      await MathJax.typesetPromise([element]);
    } catch (e) {
      console.error('[V2.5] MathJax error:', e);
    }
  }
}

function fitContentToContainer(element, options = {}) {
  const { minScale = 0.65, maxScale = 1.0, step = 0.05 } = options;

  if (!element || !element.parentElement) return;

  const container = element.parentElement;
  let scale = maxScale;

  element.style.fontSize = '';
  element.style.lineHeight = '';

  const checkOverflow = () => {
    return element.scrollHeight > container.clientHeight;
  };

  while (checkOverflow() && scale > minScale) {
    scale -= step;
    element.style.fontSize = `${scale}em`;
    element.style.lineHeight = `${1.4 + (1 - scale) * 0.2}`;
  }

  if (checkOverflow()) {
    element.style.overflowY = 'auto';
  }

  console.log(`[V2.5] Content scaled to ${(scale * 100).toFixed(0)}%`);
}

// ============================================
// PRESENTATION LOADING
// ============================================
async function loadPresentation() {
  try {
    const response = await fetch(PRESENTATION_PATH + '?t=' + Date.now());
    lessonData = await response.json();
    slides = lessonData.sections || [];

    console.log(`[V2.5] Loaded ${slides.length} slides`);

    // Build slide picker
    slidePicker.innerHTML = '';
    slides.forEach((slide, i) => {
      const option = document.createElement('option');
      option.value = i;
      option.textContent = `${i + 1}. ${slide.title || slide.section_type || 'Slide'}`;
      slidePicker.appendChild(option);
    });

    // Load first slide
    if (slides.length > 0) {
      loadSlide(0);
    }

  } catch (error) {
    console.error('[V2.5] Failed to load presentation:', error);
    contentBox.innerHTML = '<div class="error">Failed to load lesson content</div>';
  }
}

// ============================================
// DEV PANEL
// ============================================
function setupDevControls() {
  const avatarScaleSlider = document.getElementById('dev-avatar-scale');
  const chromaSlider = document.getElementById('dev-chroma-threshold');
  const contentWidthSlider = document.getElementById('dev-content-width');

  if (avatarScaleSlider) {
    avatarScaleSlider.addEventListener('input', (e) => {
      const scale = parseFloat(e.target.value);
      avatarCanvas.style.transform = `scale(${scale})`;
    });
  }

  if (chromaSlider) {
    chromaSlider.addEventListener('input', (e) => {
      chromaThreshold = parseInt(e.target.value);
      console.log(`[V2.5] Chroma threshold: ${chromaThreshold}`);
    });
  }

  if (contentWidthSlider) {
    contentWidthSlider.addEventListener('input', (e) => {
      const width = parseInt(e.target.value);
      contentLayer.style.width = `${width}%`;
    });
  }
}

function toggleDevPanel() {
  if (devPanel) {
    devPanel.classList.toggle('show');
    devModeEnabled = devPanel.classList.contains('show');
    if (devModeEnabled) {
      updateDevInfo();
    }
  }
}

function updateDevInfo() {
  if (!devModeEnabled || !devPanel) return;

  const slide = slides[currentSlideIndex];
  if (!slide) return;

  const slideInfo = document.getElementById('dev-slide-info');
  const sectionInfo = document.getElementById('dev-section-info');
  const audioInfo = document.getElementById('dev-audio-info');
  const videoInfo = document.getElementById('dev-video-info');

  if (slideInfo) slideInfo.textContent = `${currentSlideIndex + 1}/${slides.length}`;
  if (sectionInfo) sectionInfo.textContent = slide.section_type || 'unknown';
  if (audioInfo) audioInfo.textContent = slide.audio_path || 'none';
  if (videoInfo) videoInfo.textContent = slide.video_path || 'none';
}

// ============================================
// V2.5 INVARIANT CHECK
// ============================================
setInterval(() => {
  if (!isPlaying) {
    if ((avatarVideo && !avatarVideo.paused) || (contentVideo && !contentVideo.paused)) {
      console.error('[V2.5 FAIL] Media playing while paused');
      pauseAllMedia();
    }
  }
}, 500);
