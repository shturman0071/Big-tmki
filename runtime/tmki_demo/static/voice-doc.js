const VoiceDoc = (() => {
  let sessionId = null;
  let pendingQuestion = null;
  let recording = false;
  let mediaRecorder = null;
  let chunks = [];
  let stream = null;
  let busy = false;
  let speakToken = 0;
  let currentAudio = null;
  let russianVoice = null;
  let draftRawText = null;
  let draftShownText = null;

  function corpus() {
    return document.getElementById('corpus').value || 'skru-2';
  }

  function llm() {
    return document.getElementById('llm').value || 'ollama';
  }

  function hint(text) {
    document.getElementById('voice-hint').textContent = text || '';
  }

  async function api(path, body) {
    const r = await fetch(path, {
      method: body ? 'POST' : 'GET',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || r.statusText);
    return data;
  }

  function setSkipVisible(on) {
    const btn = document.getElementById('skip-speak');
    if (btn) btn.hidden = !on;
  }

  function stopSpeaking() {
    speakToken += 1;
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      currentAudio = null;
    }
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    setSkipVisible(false);
  }

  function pickRussianVoice() {
    if (!('speechSynthesis' in window)) return null;
    const voices = window.speechSynthesis.getVoices();
    const score = (v) => {
      if (!v.lang || !v.lang.toLowerCase().startsWith('ru')) return -1;
      const name = (v.name || '').toLowerCase();
      if (/natural|neural|premium|online/i.test(name)) return 4;
      if (/google|yandex|microsoft/i.test(name)) return 3;
      if (/robot|eugene|compact|mobile/i.test(name)) return 0;
      return 2;
    };
    let best = null;
    let bestScore = -1;
    voices.forEach((v) => {
      const s = score(v);
      if (s > bestScore) {
        best = v;
        bestScore = s;
      }
    });
    return best;
  }

  function ensureRussianVoice() {
    if (russianVoice || !('speechSynthesis' in window)) return;
    russianVoice = pickRussianVoice();
    if (!russianVoice) {
      window.speechSynthesis.onvoiceschanged = () => {
        russianVoice = pickRussianVoice();
      };
    }
  }

  function speak(text, tts) {
    const t = (text || '').trim();
    if (!t) return Promise.resolve();
    stopSpeaking();
    const token = speakToken;
    setSkipVisible(true);

    if (tts && tts.audio_base64) {
      return new Promise((resolve, reject) => {
        const audio = new Audio(`data:${tts.mime || 'audio/wav'};base64,${tts.audio_base64}`);
        currentAudio = audio;
        const finish = () => {
          if (token !== speakToken) return resolve();
          currentAudio = null;
          setSkipVisible(false);
          resolve();
        };
        audio.onended = finish;
        audio.onerror = () => {
          finish();
          reject(new Error('audio play failed'));
        };
        audio.play().catch((err) => {
          finish();
          reject(err);
        });
      });
    }

    if ('speechSynthesis' in window) {
      ensureRussianVoice();
      return new Promise((resolve) => {
        const u = new SpeechSynthesisUtterance(t);
        u.lang = 'ru-RU';
        if (russianVoice) u.voice = russianVoice;
        u.rate = 1;
        u.pitch = 1;
        const finish = () => {
          if (token !== speakToken) return resolve();
          setSkipVisible(false);
          resolve();
        };
        u.onend = finish;
        u.onerror = finish;
        window.speechSynthesis.speak(u);
      });
    }

    setSkipVisible(false);
    return Promise.resolve();
  }

  function renderChat(turns) {
    const log = document.getElementById('chat-log');
    log.innerHTML = '';
    (turns || []).forEach((t) => {
      if (t.kind === 'system') return;
      const div = document.createElement('div');
      const isFeedback = t.kind === 'user_feedback' || t.feedback;
      div.className = 'bubble ' + (t.role === 'user' ? 'user' : 'assistant') + (isFeedback ? ' feedback' : '');
      const who = document.createElement('div');
      who.className = 'who';
      if (t.role === 'user') {
        who.textContent = isFeedback ? 'Вы — исправление' : 'Вы';
      } else {
        who.textContent = 'TMKI';
      }
      const body = document.createElement('div');
      body.textContent = t.text || '';
      div.appendChild(who);
      div.appendChild(body);
      log.appendChild(div);
    });
    log.scrollTop = log.scrollHeight;
  }

  function setFeedbackPanelVisible(on) {
    const panel = document.getElementById('feedback-panel');
    if (panel) panel.hidden = !on;
  }

  function showDraftPanel(text, rawText) {
    draftRawText = rawText || text || '';
    draftShownText = text || '';
    const panel = document.getElementById('draft-panel');
    const area = document.getElementById('draft-text');
    if (!panel || !area) return;
    area.value = text || '';
    panel.hidden = false;
    area.focus();
  }

  function hideDraftPanel() {
    draftRawText = null;
    draftShownText = null;
    const panel = document.getElementById('draft-panel');
    const area = document.getElementById('draft-text');
    if (panel) panel.hidden = true;
    if (area) area.value = '';
  }

  function renderPending(pq) {
    const el = document.getElementById('pending-hint');
    if (pq) {
      el.hidden = false;
      el.textContent = 'Ответьте голосом на вопрос: «' + pq + '»';
    } else {
      el.hidden = true;
      el.textContent = '';
    }
  }

  function docRawUrl(c, rel) {
    return `/api/doc/raw?corpus=${encodeURIComponent(c)}&rel=${encodeURIComponent(rel)}`;
  }

  function docPreviewUrl(c, rel) {
    return `/api/doc/preview?corpus=${encodeURIComponent(c)}&rel=${encodeURIComponent(rel)}`;
  }

  async function renderDocument(doc) {
    const fmt = document.getElementById('doc-fmt');
    const title = document.getElementById('doc-title');
    const path = document.getElementById('doc-path');
    const viewer = document.getElementById('viewer');
    const openBtn = document.getElementById('open-os');
    const mic = document.getElementById('mic');
    const quiz = document.getElementById('ai-quiz');

    if (!doc) {
      fmt.textContent = '';
      title.textContent = 'Выберите файл слева';
      path.textContent = '';
      viewer.innerHTML = '<div class="placeholder">—</div>';
      openBtn.hidden = true;
      mic.disabled = true;
      quiz.disabled = true;
      setFeedbackPanelVisible(false);
      hideDraftPanel();
      return;
    }

    fmt.textContent = doc.format || '?';
    title.textContent = doc.file_name || '—';
    path.textContent = doc.absolute_path || doc.relative_path || '';
    viewer.innerHTML = '';
    mic.disabled = false;
    quiz.disabled = false;
    setFeedbackPanelVisible(true);

    if (!doc.exists) {
      viewer.innerHTML = '<div class="placeholder">Файл не найден на диске</div>';
    } else if (doc.view_mode === 'embed' && doc.relative_path) {
      const url = docRawUrl(doc.corpus_id || corpus(), doc.relative_path);
      const ext = (doc.format || '').toLowerCase();
      if (ext === 'pdf') {
        const iframe = document.createElement('iframe');
        iframe.src = url;
        viewer.appendChild(iframe);
      } else {
        const img = document.createElement('img');
        img.src = url;
        img.alt = doc.file_name || '';
        viewer.appendChild(img);
      }
    } else if (doc.view_mode === 'preview' && doc.relative_path) {
      viewer.innerHTML = '<div class="placeholder">Загрузка текста…</div>';
      try {
        const prev = await api(docPreviewUrl(doc.corpus_id || corpus(), doc.relative_path));
        viewer.innerHTML = '';
        if (prev.text) {
          const pre = document.createElement('pre');
          pre.className = 'doc-preview-text';
          pre.textContent = prev.text;
          viewer.appendChild(pre);
        } else {
          viewer.innerHTML = '<div class="placeholder">Текст не извлечён — откройте в приложении</div>';
        }
      } catch (_) {
        viewer.innerHTML = '<div class="placeholder">Не удалось загрузить превью</div>';
      }
    } else {
      viewer.innerHTML = '<div class="placeholder">Формат .' + (doc.format || '?') + ' — откройте в приложении</div>';
    }

    if (doc.absolute_path) {
      openBtn.hidden = false;
      openBtn.onclick = () => api('/api/doc/open', { absolute_path: doc.absolute_path });
    } else {
      openBtn.hidden = true;
    }
  }

  async function loadDocs(q) {
    const data = await api(`/api/voice-doc/docs?corpus=${encodeURIComponent(corpus())}&q=${encodeURIComponent(q || '')}&limit=50`);
    const ul = document.getElementById('doc-list');
    const count = document.getElementById('doc-count');
    count.textContent = String(data.total || 0);
    ul.innerHTML = '';
    (data.items || []).forEach((item) => {
      const li = document.createElement('li');
      li.innerHTML = '<span class="fname">' + (item.file_name || '') + '</span>' +
        '<span class="fpath">' + (item.relative_path || '') + '</span>';
      li.addEventListener('click', () => openDoc(item.relative_path, li));
      ul.appendChild(li);
    });
  }

  async function openDoc(relativePath, liEl) {
    if (busy) return;
    busy = true;
    hint('Открываю документ…');
    document.querySelectorAll('.file-list li').forEach((x) => x.classList.remove('active'));
    if (liEl) liEl.classList.add('active');
    try {
      const snap = await api('/api/voice-doc/open', {
        corpus: corpus(),
        relative_path: relativePath,
        session_id: sessionId,
        llm: llm(),
      });
      sessionId = snap.session_id;
      pendingQuestion = snap.pending_ai_question || null;
      await renderDocument(snap.document);
      renderChat(snap.turns);
      renderPending(pendingQuestion);
      hint('Говорите в микрофон или нажмите «Спроси меня»');
      const greet = snap.greeting || (snap.turns && snap.turns[0] && snap.turns[0].text);
      if (greet && snap.tts) speak(greet, snap.tts).catch(() => {});
    } catch (e) {
      hint('Ошибка: ' + e.message);
    } finally {
      busy = false;
    }
  }

  async function runTurn(kind, text, rawText, options) {
    if (!sessionId) throw new Error('сначала откройте документ');
    const opts = options || {};
    const body = {
      session_id: sessionId,
      kind,
      text,
      llm: llm(),
    };
    if (rawText && rawText.trim() && rawText.trim() !== (text || '').trim()) {
      body.raw_text = rawText.trim();
    }
    const snap = await api('/api/voice-doc/turn', body);
    pendingQuestion = snap.pending_ai_question || null;
    renderChat(snap.turns);
    renderPending(pendingQuestion);
    if (snap.stt_learned && snap.stt_learned.length) {
      hint('Сохранено в базу STT: ' + snap.stt_learned.map((x) => x.wrong + '→' + x.replacement).join(', '));
    } else if (snap.feedback_recorded) {
      hint('Исправление учтено');
    }
    const reply = snap.assistant_text || '';
    if (reply && opts.speak !== false) await speak(reply, snap.tts);
    return snap;
  }

  async function submitFeedback() {
    if (!sessionId) {
      hint('Сначала откройте документ');
      return;
    }
    const area = document.getElementById('feedback-text');
    const text = (area && area.value || '').trim();
    if (!text) {
      hint('Введите замечание');
      return;
    }
    stopSpeaking();
    hint('Учитываю исправление…');
    try {
      await runTurn('user_feedback', text, null, { speak: true });
      if (area) area.value = '';
      hint('Ответ обновлён. Продолжайте диалог');
    } catch (e) {
      hint('Ошибка: ' + e.message);
    }
  }

  async function transcribe(blob) {
    const res = await fetch('/api/transcribe', {
      method: 'POST',
      headers: { 'Content-Type': blob.type || 'audio/webm' },
      body: blob,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.hint || data.error || res.statusText);
    return {
      text: (data.text || '').trim(),
      rawText: (data.raw_text || data.text || '').trim(),
    };
  }

  function pickMime() {
    const c = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg'];
    for (const t of c) {
      if (MediaRecorder.isTypeSupported(t)) return t;
    }
    return '';
  }

  async function submitDraft() {
    const area = document.getElementById('draft-text');
    const text = (area && area.value || '').trim();
    if (!text) {
      hint('Введите текст');
      return;
    }
    const kind = pendingQuestion ? 'user_answer' : 'user_question';
    const raw = draftRawText || text;
    const userEdited = text !== (draftShownText || '');
    hideDraftPanel();
    busy = true;
    try {
      await runTurn(kind, text, userEdited ? raw : null);
      hint(kind === 'user_answer' ? 'Ответ оценён. Говорите или исправьте модель' : 'Ответ готов. Говорите ещё или «Спроси меня»');
    } catch (e) {
      hint('Ошибка: ' + e.message);
    } finally {
      busy = false;
    }
  }

  async function handleMicBlob(blob) {
    if (!blob || !blob.size) {
      hint('Ничего не записано');
      return;
    }
    busy = true;
    hint('Распознаю…');
    try {
      const result = await transcribe(blob);
      if (!result.text) {
        hint('Речь не распознана');
        return;
      }
      showDraftPanel(result.text, result.rawText);
      hint('Проверьте текст и нажмите «Отправить»');
    } catch (e) {
      hint('Ошибка: ' + e.message);
    } finally {
      busy = false;
    }
  }

  function initMic() {
    const btn = document.getElementById('mic');
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      btn.disabled = true;
      return;
    }
    btn.addEventListener('click', async () => {
      if (busy || !sessionId) return;
      if (recording) {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
        recording = false;
        btn.classList.remove('listening');
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      } catch (_) {
        hint('Разрешите доступ к микрофону');
        return;
      }
      chunks = [];
      const mime = pickMime();
      mediaRecorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
      mediaRecorder.onstop = () => {
        if (stream) {
          stream.getTracks().forEach((t) => t.stop());
          stream = null;
        }
        handleMicBlob(new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' }));
      };
      mediaRecorder.start();
      recording = true;
      btn.classList.add('listening');
      hint(pendingQuestion ? 'Отвечайте на вопрос… (ещё раз — стоп)' : 'Задайте вопрос… (ещё раз — стоп)');
    });
  }

  function init() {
    let searchTimer = null;
    document.getElementById('doc-search').addEventListener('input', (e) => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => loadDocs(e.target.value.trim()).catch(() => {}), 300);
    });
    document.getElementById('corpus').addEventListener('change', () => {
      sessionId = null;
      pendingQuestion = null;
      loadDocs('').catch(() => {});
      renderDocument(null);
      renderChat([]);
      renderPending(null);
      setFeedbackPanelVisible(false);
      hideDraftPanel();
      hint('Выберите документ');
    });
    document.getElementById('ai-quiz').addEventListener('click', async () => {
      if (busy || !sessionId) return;
      busy = true;
      hint('Готовлю вопрос…');
      try {
        await runTurn('ai_quiz', '');
        hint('Слушайте вопрос и отвечайте в микрофон');
      } catch (e) {
        hint('Ошибка: ' + e.message);
      } finally {
        busy = false;
      }
    });
    const skipBtn = document.getElementById('skip-speak');
    if (skipBtn) {
      skipBtn.addEventListener('click', () => {
        stopSpeaking();
        hint('Озвучка пропущена');
      });
    }
    const draftSend = document.getElementById('draft-send');
    const draftCancel = document.getElementById('draft-cancel');
    if (draftSend) draftSend.addEventListener('click', () => { if (!busy) submitDraft(); });
    if (draftCancel) draftCancel.addEventListener('click', () => { hideDraftPanel(); hint('Отменено'); });
    const feedbackSend = document.getElementById('feedback-send');
    const feedbackArea = document.getElementById('feedback-text');
    if (feedbackSend) {
      feedbackSend.addEventListener('click', (e) => {
        e.preventDefault();
        submitFeedback();
      });
    }
    if (feedbackArea) {
      feedbackArea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
          e.preventDefault();
          submitFeedback();
        }
      });
    }
    initMic();
    loadDocs('').catch(() => {});
  }

  return { init };
})();
