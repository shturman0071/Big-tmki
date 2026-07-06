const QaLab = (() => {
  const POLL_MS = 2000;
  let lastCursor = -1;
  let lastDocKey = '';
  let lastAnswerAt = '';
  let lastVerdictKey = '';
  let lastListKey = '';

  function listKey(state) {
    const items = state.suite_list || [];
    return items.map((i) => `${i.index}:${i.status}`).join('|') + ':' + state.cursor;
  }

  function docKey(state) {
    const cur = state.current;
    if (!cur) return state.done ? 'done' : 'empty';
    return `${state.cursor}:${cur.id || cur.document_relative_path || ''}`;
  }

  function verdictKey(state) {
    const v = state.verdicts || [];
    const ans = state.current_answer;
    const at = ans && ans.asked_at ? ans.asked_at : '';
    return `${state.cursor}:${v.length}:${state.done}:${at}`;
  }

  async function fetchState() {
    const r = await fetch('/api/qa-lab/state');
    return r.json();
  }

  async function fetchFiles() {
    const r = await fetch('/api/qa-lab/files');
    if (!r.ok) {
      const s = await fetchState();
      return { suite_list: s.suite_list || [], cursor: s.cursor, total: s.total };
    }
    return r.json();
  }

  async function loadMergedState() {
    const state = await fetchState();
    try {
      const files = await fetchFiles();
      state.suite_list = files.suite_list || state.suite_list || [];
      state.cursor = files.cursor != null ? files.cursor : state.cursor;
      state.total = files.total != null ? files.total : state.total;
    } catch (_) { /* state endpoint enough */ }
    return state;
  }

  async function api(action, body) {
    const paths = { reset: '/api/qa-lab/reset', select: '/api/qa-lab/select' };
    const path = paths[action] || `/api/qa-lab/${action}`;
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || r.statusText);
    return data;
  }

  function docRawUrl(corpus, rel) {
    return `/api/doc/raw?corpus=${encodeURIComponent(corpus)}&rel=${encodeURIComponent(rel)}`;
  }

  function focusDocPanel() {
    const panel = document.querySelector('.col-doc');
    if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  async function selectDocument(index) {
    lastDocKey = '';
    lastCursor = -1;
    lastAnswerAt = '';
    lastVerdictKey = '';
    lastListKey = '';
    const snap = await api('select', { index });
    if (snap.open_external) {
      fetch('/api/doc/open', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ absolute_path: snap.open_external }),
      }).catch(() => {});
    }
    const s = await loadMergedState();
    renderAll(s);
    focusDocPanel();
  }

  function renderList(state) {
    const key = listKey(state);
    if (key === lastListKey) return;
    lastListKey = key;

    const ul = document.getElementById('doc-list');
    const countEl = document.getElementById('list-count');
    const items = state.suite_list || [];
    countEl.textContent = String(items.length || state.total || 0);
    ul.innerHTML = '';
    if (!items.length) {
      const li = document.createElement('li');
      li.className = 'placeholder-item';
      li.textContent = 'Список пуст — нажмите «Сброс» или обновите страницу';
      li.style.cursor = 'default';
      li.style.color = '#888';
      ul.appendChild(li);
      return;
    }
    items.forEach((item) => {
      const li = document.createElement('li');
      li.setAttribute('role', 'button');
      li.tabIndex = 0;
      let cls = '';
      if (item.status === 'current') cls = 'current';
      else if (item.status === 'ok') cls = 'done-ok';
      else if (item.status === 'fail') cls = 'done-fail';
      else if (item.status === 'err') cls = 'done-err';
      if (cls) li.className = cls;

      const tag = document.createElement('span');
      tag.className = 'fmt-tag';
      tag.textContent = item.format || '?';

      const textWrap = document.createElement('div');
      textWrap.style.flex = '1';
      textWrap.style.minWidth = '0';

      const name = document.createElement('span');
      name.className = 'fname';
      name.textContent = item.file_name || item.id || '—';

      const path = document.createElement('span');
      path.className = 'fpath';
      path.textContent = item.absolute_path || item.document_relative_path || '';
      path.title = path.textContent;

      textWrap.appendChild(name);
      textWrap.appendChild(path);

      const open = () => {
        if (item.index === state.cursor) {
          focusDocPanel();
          return;
        }
        selectDocument(item.index).catch((e) => alert(e.message));
      };

      li.addEventListener('click', open);
      li.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          open();
        }
      });

      li.appendChild(tag);
      li.appendChild(textWrap);
      ul.appendChild(li);
    });
  }

  function renderDoc(state) {
    const key = docKey(state);
    if (key === lastDocKey) return;
    lastDocKey = key;

    const cur = state.current;
    const fmtEl = document.getElementById('fmt');
    const nameEl = document.getElementById('file-name');
    const pathEl = document.getElementById('full-path');
    const viewer = document.getElementById('viewer');
    const openBtn = document.getElementById('open-os');

    if (!cur) {
      fmtEl.textContent = '';
      nameEl.textContent = state.done ? 'Все форматы пройдены' : 'Нет задания';
      pathEl.textContent = '—';
      viewer.innerHTML = '<div class="placeholder">—</div>';
      openBtn.hidden = true;
      return;
    }

    fmtEl.textContent = cur.format || '?';
    nameEl.textContent = cur.file_name || '—';
    pathEl.textContent = cur.absolute_path || '(файл не найден на диске)';
    viewer.innerHTML = '';
    const corpus = state.corpus_id || 'skru-2';

    if (!cur.exists) {
      viewer.innerHTML = '<div class="placeholder">Файл не найден на диске</div>';
    } else if (cur.view_mode === 'embed' && cur.document_relative_path) {
      const url = docRawUrl(corpus, cur.document_relative_path);
      const ext = (cur.format || '').toLowerCase();
      if (ext === 'pdf') {
        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.title = cur.file_name || 'document';
        viewer.appendChild(iframe);
      } else {
        const img = document.createElement('img');
        img.src = url;
        img.alt = cur.file_name || '';
        viewer.appendChild(img);
      }
    } else {
      viewer.innerHTML = `<div class="placeholder">Формат .${cur.format} — нажмите «Открыть в приложении»</div>`;
    }

    if (cur.absolute_path) {
      openBtn.hidden = false;
      openBtn.onclick = async () => {
        await fetch('/api/doc/open', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ absolute_path: cur.absolute_path }),
        });
      };
    } else {
      openBtn.hidden = true;
    }
  }

  function renderQuestion(state) {
    const cur = state.current;
    const prog = document.getElementById('progress');
    const qEl = document.getElementById('question');
    const docLbl = document.getElementById('question-doc');
    const resultBlock = document.getElementById('qa-result-block');
    const refEl = document.getElementById('qa-result-ref');
    const modelEl = document.getElementById('qa-result-a');
    if (!cur) {
      prog.textContent = state.done ? 'готово' : '—';
      if (docLbl) docLbl.textContent = 'Выберите файл в колонке «Форматы»';
      if (resultBlock) resultBlock.hidden = true;
      return;
    }
    prog.textContent = `${state.cursor + 1}/${state.total}`;
    const qText = cur.lab_question || cur.question || '';
    if (docLbl) {
      docLbl.textContent = `Документ: ${cur.file_name || '—'} (.${cur.format || '?'})`;
    }
    if (lastCursor !== state.cursor) {
      lastCursor = state.cursor;
      lastAnswerAt = '';
      qEl.value = qText;
      if (refEl) refEl.value = cur.reference_answer || '';
      if (modelEl) modelEl.textContent = '—';
      if (resultBlock) resultBlock.hidden = false;
      document.getElementById('qa-result-q').textContent = '';
      document.getElementById('qa-result-citations').innerHTML = '';
    }
  }

  function updateVerdictButtons(state) {
    const hasAnswer = !!(state.current_answer && state.current_answer.asked_at);
    document.querySelectorAll('[data-v]').forEach((btn) => {
      btn.disabled = !hasAnswer;
    });
  }

  function renderQaResult(state) {
    const ans = state.current_answer;
    const block = document.getElementById('qa-result-block');
    const modelEl = document.getElementById('qa-result-a');
    if (!ans || !ans.asked_at) {
      if (state.current && block) block.hidden = false;
      return;
    }
    if (ans.asked_at === lastAnswerAt) return;
    lastAnswerAt = ans.asked_at;

    block.hidden = false;
    document.getElementById('qa-result-q').textContent = 'В: ' + (ans.question || '—');
    if (modelEl) modelEl.textContent = ans.answer || '(пусто)';
    const cit = document.getElementById('qa-result-citations');
    cit.innerHTML = '';
    (ans.citations || []).slice(0, 4).forEach((c) => {
      const d = document.createElement('div');
      d.textContent = (c.file_name || c.relative_path || '') +
        (c.snippet ? ': ' + c.snippet.slice(0, 100) : '');
      cit.appendChild(d);
    });
  }

  function renderVerdict(state) {
    const vk = verdictKey(state);
    const cur = state.current;

    const st = state.stats || {};
    document.getElementById('stats').textContent =
      `Верно: ${st.ok || 0} | Неверно: ${st.fail || 0} | С ошибкой: ${st.err || 0}`;

    const hdr = document.getElementById('header-status');
    if (hdr && state.total) {
      hdr.textContent = `Прогресс ${state.cursor}/${state.total}`;
    }

    renderQaResult(state);
    updateVerdictButtons(state);

    if (vk === lastVerdictKey) return;
    lastVerdictKey = vk;

    const log = document.getElementById('log');
    log.textContent = (state.verdicts || []).map((v) => {
      const q = v.question ? ` | «${v.question.slice(0, 40)}»` : '';
      return `[${v.format}] ${v.verdict}${v.note ? ' — ' + v.note : ''} — ${v.file_name || v.id}${q}`;
    }).join('\n') || '—';
  }

  function renderAll(state) {
    renderList(state);
    renderDoc(state);
    renderQuestion(state);
    renderVerdict(state);
  }

  function pollStatus(cb) {
    const tick = async () => {
      try { cb(await loadMergedState()); } catch (_) { /* ignore */ }
      setTimeout(tick, POLL_MS);
    };
    tick();
  }

  async function doAsk() {
    const btn = document.getElementById('ask');
    btn.disabled = true;
    try {
      await api('ask', {
        question: document.getElementById('question').value.trim(),
        llm: document.getElementById('llm').value,
      });
      const state = await loadMergedState();
      lastAnswerAt = '';
      renderAll(state);
    } catch (e) {
      alert(e.message);
    } finally {
      btn.disabled = false;
    }
  }

  function initVoice() {
    const voiceBtn = document.getElementById('voice');
    const questionEl = document.getElementById('question');
    const hintEl = document.getElementById('voice-hint');
    if (!voiceBtn) return;

    let mediaRecorder = null;
    let chunks = [];
    let stream = null;
    let recording = false;

    const canRecord = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
    if (!canRecord) {
      voiceBtn.disabled = true;
      voiceBtn.title = 'Голосовой ввод недоступен';
      return;
    }

    function setListening(on) {
      recording = on;
      voiceBtn.classList.toggle('listening', on);
      questionEl.classList.toggle('listening', on);
    }

    function pickMimeType() {
      const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg'];
      for (const t of candidates) {
        if (MediaRecorder.isTypeSupported(t)) return t;
      }
      return '';
    }

    async function sendAudio(blob) {
      if (!blob || blob.size === 0) {
        hintEl.textContent = 'Ничего не записано';
        return;
      }
      hintEl.textContent = 'Распознаю…';
      voiceBtn.disabled = true;
      try {
        const res = await fetch('/api/transcribe', {
          method: 'POST',
          headers: { 'Content-Type': blob.type || 'audio/webm' },
          body: blob,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.hint || data.error || res.statusText);
        const text = (data.text || '').trim();
        if (!text) {
          hintEl.textContent = 'Речь не распознана';
          return;
        }
        questionEl.value = text;
        hintEl.textContent = 'Распознано, отправляю…';
        await doAsk();
        hintEl.textContent = 'Готово';
      } catch (e) {
        hintEl.textContent = 'Ошибка: ' + e.message;
      } finally {
        voiceBtn.disabled = false;
      }
    }

    voiceBtn.addEventListener('click', async () => {
      if (recording) {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
        setListening(false);
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
        });
      } catch (_) {
        hintEl.textContent = 'Разрешите микрофон';
        return;
      }
      chunks = [];
      const mimeType = pickMimeType();
      try {
        mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      } catch (_) {
        mediaRecorder = new MediaRecorder(stream);
      }
      mediaRecorder.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) chunks.push(ev.data);
      };
      mediaRecorder.onstop = () => {
        if (stream) {
          stream.getTracks().forEach((t) => t.stop());
          stream = null;
        }
        sendAudio(new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' }));
      };
      mediaRecorder.start();
      setListening(true);
      hintEl.textContent = 'Слушаю… нажмите ещё раз для остановки';
    });
  }

  function init() {
    document.getElementById('ask').addEventListener('click', doAsk);
    document.getElementById('question').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        doAsk();
      }
    });

    document.getElementById('reset-lab').addEventListener('click', async () => {
      if (!confirm('Сбросить прогресс?')) return;
      lastCursor = -1;
      lastDocKey = '';
      lastAnswerAt = '';
      lastVerdictKey = '';
      lastListKey = '';
      await api('reset', {});
      const state = await loadMergedState();
      renderAll(state);
    });

    document.querySelectorAll('[data-v]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        try {
          await api('verdict', {
            verdict: btn.dataset.v,
            note: document.getElementById('err-note').value,
            reference_answer: (document.getElementById('qa-result-ref') || {}).value || '',
          });
          document.getElementById('err-note').value = '';
          lastAnswerAt = '';
          lastVerdictKey = '';
          lastListKey = '';
          const state = await loadMergedState();
          renderAll(state);
        } catch (e) {
          alert(e.message);
        } finally {
          btn.disabled = false;
        }
      });
    });

    initVoice();
    loadMergedState().then(renderAll).catch(() => {});
    pollStatus(renderAll);
  }

  return { init, api, fetchState, loadMergedState, pollStatus };
})();
