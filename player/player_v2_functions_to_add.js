// ============================================
// V2.5 COMPLIANCE FUNCTIONS FOR PLAYER_V2.JS
// Insert after line 932 (after renderContent function)
// ============================================

// QUIZ RENDERER (V2.5 Compliance)
function renderQuiz(slide) {
    console.log('[V2.5] QuizRenderer: 3-step dance');

    const contentBox = document.getElementById('content-box');
    contentBox.innerHTML = '';

    const questions = slide.quiz_questions || [];

    questions.forEach((q, qIndex) => {
        const quizCard = document.createElement('div');
        quizCard.className = 'quiz-card quiz-hidden';
        quizCard.id = `quiz-${qIndex}`;

        const questionDiv = document.createElement('div');
        questionDiv.className = 'quiz-question';
        questionDiv.textContent = q.question;
        quizCard.appendChild(questionDiv);

        const choicesDiv = document.createElement('div');
        choicesDiv.className = 'quiz-choices';

        q.options.forEach((opt, optIndex) => {
            const choiceDiv = document.createElement('div');
            choiceDiv.className = 'quiz-choice';
            choiceDiv.dataset.index = optIndex;

            const letter = document.createElement('div');
            letter.className = 'choice-letter';
            letter.textContent = String.fromCharCode(65 + optIndex);
            choiceDiv.appendChild(letter);

            const text = document.createElement('div');
            text.className = 'choice-text';
            text.textContent = opt;
            choiceDiv.appendChild(text);

            choicesDiv.appendChild(choiceDiv);
        });

        quizCard.appendChild(choicesDiv);
        contentBox.appendChild(quizCard);
    });
}

// MEMORY FLASHCARD RENDERER (V2.5 Compliance)
function renderMemory(slide) {
    console.log('[V2.5] MemoryRenderer: Flashcards with flip animation');

    const contentBox = document.getElementById('content-box');
    contentBox.innerHTML = '';

    const flashcards = slide.flashcards || slide.memory_items || [];
    const container = document.createElement('div');
    container.className = 'flashcard-container';

    flashcards.forEach((card, index) => {
        const cardDiv = document.createElement('div');
        cardDiv.className = 'flashcard';
        cardDiv.id = `flashcard-${index}`;
        cardDiv.dataset.flipped = 'false';

        const front = document.createElement('div');
        front.className = 'flashcard-front';
        front.innerHTML = `<div class="flashcard-title" style="font-size: 1.3em; font-weight: 600;">${sanitizeMarkdown(card.front)}</div>`;

        const back = document.createElement('div');
        back.className = 'flashcard-back';
        back.innerHTML = `<div class="flashcard-mnemonic" style="font-size: 1.1em;">${sanitizeMarkdown(card.back)}</div>`;

        cardDiv.appendChild(front);
        cardDiv.appendChild(back);
        container.appendChild(cardDiv);
    });

    contentBox.appendChild(container);
}

// MEDIA PRELOADING (V2.5 UX Enhancement)
function preloadNextSection(nextIndex) {
    if (nextIndex >= slides.length) return;

    const nextSlide = slides[nextIndex];

    if (nextSlide.video_path) {
        const videoPreloader = document.createElement('video');
        videoPreloader.src = resolveMediaPath(nextSlide.video_path, 'video');
        videoPreloader.preload = 'auto';
        videoPreloader.load();
        console.log(`[V2.5] Preloading next video: ${nextSlide.video_path}`);
    }

    if (nextSlide.avatar_video) {
        const avatarPreloader = document.createElement('video');
        avatarPreloader.src = resolveMediaPath(nextSlide.avatar_video, 'video');
        avatarPreloader.preload = 'auto';
        avatarPreloader.load();
        console.log(`[V2.5] Preloading next avatar: ${nextSlide.avatar_video}`);
    }

    if (nextSlide.audio_path) {
        const audioPreloader = new Audio(resolveMediaPath(nextSlide.audio_path, 'audio'));
        audioPreloader.preload = 'auto';
        audioPreloader.load();
        console.log(`[V2.5] Preloading next audio: ${nextSlide.audio_path}`);
    }
}

async function checkMediaExists(path) {
    try {
        const response = await fetch(path, { method: 'HEAD' });
        return response.ok;
    } catch {
        return false;
    }
}

function showMediaGeneratingPlaceholder(type, container) {
    container.innerHTML = `
    <div class="media-generating-placeholder">
      <div class="spinner"></div>
      <div style="font-size: 1.2em; font-weight: 600;">Generating ${type}...</div>
      <div style="font-size: 0.9em; opacity: 0.9;">This may take a few moments</div>
    </div>
  `;
}

// DISPLAY DIRECTIVES PARSER (V2.5 Core)
function parseDisplayDirectives(slide) {
    const directives = [];
    const segments = slide.narration?.segments || [];

    segments.forEach((seg, i) => {
        if (seg.display_directives) {
            directives.push({
                time: seg.start_time_sec || 0,
                action: seg.display_directives.action_type,
                data: seg.display_directives
            });
        }
    });

    if (slide.flip_timing_sec) {
        directives.push({
            time: slide.flip_timing_sec,
            action: 'show_video',
            data: {}
        });
    }

    return directives.sort((a, b) => a.time - b.time);
}
