/**
 * Mormon Time Capsule — App
 * Low-latency timeline explorer for General Conference talks.
 */

/* ─── Prophet Data ─── */
const PROPHETS = [
    { name: "Joseph Smith",      start: 1830, end: 1844, order: 1,  emoji: "📜" },
    { name: "Brigham Young",     start: 1847, end: 1877, order: 2,  emoji: "🧭" },
    { name: "John Taylor",       start: 1880, end: 1887, order: 3,  emoji: "📖" },
    { name: "Wilford Woodruff",  start: 1889, end: 1898, order: 4,  emoji: "📋" },
    { name: "Lorenzo Snow",      start: 1898, end: 1901, order: 5,  emoji: "❄️"  },
    { name: "Joseph F. Smith",   start: 1901, end: 1918, order: 6,  emoji: "📘" },
    { name: "Heber J. Grant",    start: 1918, end: 1945, order: 7,  emoji: "🏦" },
    { name: "George Albert Smith", start: 1945, end: 1951, order: 8,  emoji: "🕊️" },
    { name: "David O. McKay",    start: 1951, end: 1970, order: 9,  emoji: "🌍" },
    { name: "Joseph Fielding Smith", start: 1970, end: 1972, order: 10, emoji: "📚" },
    { name: "Harold B. Lee",     start: 1972, end: 1973, order: 11, emoji: "⚡" },
    { name: "Spencer W. Kimball", start: 1973, end: 1985, order: 12, emoji: "🔥" },
    { name: "Ezra Taft Benson",  start: 1985, end: 1994, order: 13, emoji: "🏛️" },
    { name: "Howard W. Hunter",  start: 1994, end: 1995, order: 14, emoji: "🕯️" },
    { name: "Gordon B. Hinckley", start: 1995, end: 2008, order: 15, emoji: "😊" },
    { name: "Thomas S. Monson",  start: 2008, end: 2018, order: 16, emoji: "🗣️" },
    { name: "Russell M. Nelson", start: 2018, end: 2025, order: 17, emoji: "❤️"  },
    { name: "Dallin H. Oaks",   start: 2025, end: 2026, order: 18, emoji: "⚖️" },
];

/* ─── Corpus Index ─── */
let corpusIndex = {};
let talkData = {};

/* ─── DOM References ─── */
const $ = (s) => document.querySelector(s);
const yearSlider = $('#year-slider');
const yearDisplay = $('#year-display');
const prophetName = $('#prophet-name');
const prophetTenure = $('#prophet-tenure');
const prophetOrder = $('#prophet-order');
const prophetPortrait = $('#prophet-portrait');
const gapNotice = $('#gap-notice');
const talkCount = $('#talk-count');
const speakerCount = $('#speaker-count');
const eraRange = $('#era-range');
const chatMessages = $('#chat-messages');
const chatInput = $('#chat-input');
const chatSend = $('#chat-send');
const chatYearLabel = $('#chat-year-label');
const talkDetailOverlay = $('#talk-detail-overlay');
const talkDetailTitle = $('#talk-detail-title');
const talkDetailSpeaker = $('#talk-detail-speaker');
const talkDetailMeta = $('#talk-detail-meta');
const talkDetailBody = $('#talk-detail-body');

/* ─── Helpers ─── */
function getProphet(year) {
    for (const p of PROPHETS) {
        if (year >= p.start && year <= p.end) return p;
    }
    return null;
}

function getInitials(name) {
    return name.split(' ').map(w => w[0]).join('').slice(0, 3);
}

function hasTalks(year) {
    return year >= 1897; // earliest covered year
}

function inGap(year) {
    return year >= 1881 && year <= 1896;
}

/* ─── Data Loading ─── */
async function loadYearTalks(year) {
    if (talkData[year]) return talkData[year];
    if (!hasTalks(year)) return [];

    const sessions = ['a', 'sa'];
    let allTalks = [];

    for (const session of sessions) {
        const fname = `conferencereport${year}${session}.json`;
        const url = `data/unified/${fname}`;
        try {
            const resp = await fetch(url);
            if (!resp.ok) continue;
            const talks = await resp.json();
            if (Array.isArray(talks) && talks.length > 0) {
                talks.forEach(t => t._session = session === 'a' ? 'April' : 'October');
                allTalks = allTalks.concat(talks);
            }
        } catch (e) {
            // file not available
        }
    }

    if (allTalks.length > 0) {
        allTalks.sort((a, b) => (a._session > b._session ? -1 : 0));
        // Compute unique speakers
        const speakers = new Set(allTalks.map(t => t.speaker).filter(Boolean));
        corpusIndex[year] = {
            talks: allTalks.length,
            speakers: speakers.size,
        };
    }

    talkData[year] = allTalks;
    return allTalks;
}

/* ─── Display Update ─── */
async function updateForYear(year) {
    // Update year display
    yearDisplay.textContent = year;
    chatYearLabel.textContent = `— ${year}`;

    // Prophet
    const prophet = getProphet(year);
    if (prophet) {
        prophetName.textContent = prophet.name;
        prophetOrder.textContent = `${prophet.order}${ordinal(prophet.order)} President`;
        prophetTenure.textContent = `${prophet.start} – ${prophet.end}`;
        prophetPortrait.style.display = 'flex';
        prophetPortrait.style.alignItems = 'center';
        prophetPortrait.style.justifyContent = 'center';
        
        // Try to load prophet image — try multiple extensions
        const slug = prophet.name.toLowerCase().replace(/\./g, '').replace(/\s+/g, '-');
        const exts = ['jpg', 'png', 'jpeg'];
        let attemptIdx = 0;
        
        function tryProphetImage() {
            if (attemptIdx >= exts.length) {
                // Fallback: initials + gradient
                prophetPortrait.innerHTML = getInitials(prophet.name);
                prophetPortrait.style.background =
                    `linear-gradient(135deg, hsl(${prophet.order * 21}, 60%, 40%), hsl(${prophet.order * 21 + 40}, 50%, 30%))`;
                return;
            }
            const img = new Image();
            img.onload = () => {
                prophetPortrait.innerHTML = '';
                prophetPortrait.style.background = 'none';
                img.className = 'prophet-portrait';
                prophetPortrait.appendChild(img);
            };
            img.onerror = tryProphetImage;
            img.src = `images/prophets/${slug}.${exts[attemptIdx]}`;
            attemptIdx++;
        }
        tryProphetImage();
        
        // Try to load SLC decade photo as backdrop
        const decade = Math.floor(year / 10) * 10;
        const slcExts = ['jpg', 'jpeg', 'png'];
        let slcAttempt = 0;
        
        function trySlcImage() {
            if (slcAttempt >= slcExts.length) {
                document.getElementById('prophet-card').style.background = '#fff';
                document.getElementById('prophet-card').classList.remove('has-backdrop');
                return;
            }
            const card = document.getElementById('prophet-card');
            const ext = slcExts[slcAttempt];
            const img = new Image();
            img.onload = () => {
                card.style.background = `#fff url('images/slc/${decade}s.${ext}') center/cover no-repeat`;
                card.style.backgroundBlendMode = 'overlay';
                card.classList.add('has-backdrop');
            };
            img.onerror = trySlcImage;
            img.src = `images/slc/${decade}s.${ext}`;
            slcAttempt++;
        }
        trySlcImage();
    } else {
        prophetName.textContent = '—';
        prophetOrder.textContent = '—';
        prophetTenure.textContent = '';
        prophetPortrait.textContent = '?';
    }

    // Gap / coverage
    const indexEntry = corpusIndex[year];
    const yearHasData = !!(indexEntry && indexEntry.talks > 0);

    gapNotice.style.display = (!yearHasData && (hasTalks(year) || inGap(year) || year < 1897)) ? 'block' : 'none';
    gapNotice.innerHTML = inGap(year)
        ? '<strong>Data Gap</strong> — No conference reports exist for <strong>' + year +
          '</strong> (1881–1896). Alternative sources are being researched.'
        : year < 1897 && !inGap(year)
        ? '<strong>Pre-Conference Report Era</strong> — Conference Reports as we know them started in 1897. ' +
          'Talks from <strong>' + year +
          '</strong> were published in newspapers (Deseret News, Millennial Star). Sourcing in progress.'
        : 'No talk data loaded for <strong>' + year +
          '</strong> yet. Move the slider to a year with data, or add files to <code>time-capsule/data/unified/</code>.';
    // Keep gap visible if inGap or no data loaded for a year we should have

    // Stats — load talk data in background
    const existing = corpusIndex[year];
    if (existing) {
        talkCount.textContent = existing.talks;
        speakerCount.textContent = existing.speakers;
    } else {
        talkCount.textContent = hasTalks(year) ? '⟳' : '—';
        speakerCount.textContent = '—';
    }

    if (year >= 1897 && year <= 1970) {
        eraRange.textContent = '📄 OCR';
    } else if (year >= 1971 && year <= 2026) {
        eraRange.textContent = '🌐 Web text';
    } else if (inGap(year)) {
        eraRange.textContent = '⏳ Gap';
    } else {
        eraRange.textContent = '🔍 Researching';
    }

    // Load actual data in background (don't await — let it fill in)
    if (hasTalks(year)) {
        loadYearTalks(year).then(talks => {
            if (!talks || talks.length === 0) return;
            const entry = corpusIndex[year] || { talks: 0, speakers: 0 };
            talkCount.textContent = entry.talks || talks.length;
            const sp = new Set(talks.map(t => t.speaker).filter(Boolean));
            speakerCount.textContent = sp.size;
        }).catch(() => {
            if (talkCount.textContent === '⟳') talkCount.textContent = '—';
        });
    }
}

function ordinal(n) {
    const s = ['th', 'st', 'nd', 'rd'];
    const v = n % 100;
    return s[(v - 20) % 10] || s[v] || s[0];
}

/* ─── Chat / Search ─── */
function addMessage(type, html) {
    const div = document.createElement('div');
    div.className = `chat-message ${type}-message`;
    div.innerHTML = html;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function clearChat() {
    chatMessages.innerHTML = '';
}

function showTalks(talks, year) {
    if (!talks || talks.length === 0) {
        addMessage('system', `
            <div class="message-label">🔍 Time Capsule</div>
            <div class="message-text">No talks found for ${year}. ${inGap(year) ? 'This is a data gap period.' : ''}</div>
        `);
        return;
    }

    addMessage('system', `
        <div class="message-label">📚 Found ${talks.length} talks from ${year}</div>
    `);

    // Show first 15
    const count = Math.min(talks.length, 15);
    for (let i = 0; i < count; i++) {
        const t = talks[i];
        const excerpt = t.body && t.body[0] ? t.body[0].slice(0, 120) + '...' : '';
        addMessage('talk', `
            <div class="message-text talk-result" data-year="${year}" data-index="${i}">
                <div class="talk-title">${t.title || '(untitled)'}</div>
                <div class="talk-speaker">${t.speaker} <span class="talk-badge">${t._session || ''}</span></div>
                <div class="talk-excerpt">${excerpt}</div>
            </div>
        `);
    }

    if (talks.length > 15) {
        addMessage('system', `<div class="message-text">... and ${talks.length - 15} more talks</div>`);
    }

    // Attach click handlers
    document.querySelectorAll('.talk-result').forEach(el => {
        el.addEventListener('click', () => {
            const year = parseInt(el.dataset.year);
            const idx = parseInt(el.dataset.index);
            showTalkDetail(year, idx);
        });
    });
}

function searchTalks(year, query) {
    const talks = talkData[year] || [];
    if (!query.trim()) return talks;

    const q = query.toLowerCase();
    return talks.filter(t => {
        const haystack = (t.speaker + ' ' + (t.title || '') + ' ' + (t.body || []).join(' ')).toLowerCase();
        return haystack.includes(q);
    });
}

async function handleChat(year) {
    const query = chatInput.value.trim();
    if (!query) return;

    addMessage('user', `
        <div class="message-label">You</div>
        <div class="message-text">${escapeHtml(query)}</div>
    `);
    chatInput.value = '';
    chatSend.disabled = true;

    // Ensure data is loaded
    let talks = talkData[year];
    if (!talks && hasTalks(year)) {
        talks = await loadYearTalks(year);
    }

    if (!talks || talks.length === 0) {
        addMessage('system', `
            <div class="message-label">🔍 Time Capsule</div>
            <div class="message-text">No talk data available for ${year}.</div>
        `);
        chatSend.disabled = false;
        return;
    }

    const results = searchTalks(year, query);
    if (results.length === 0) {
        addMessage('system', `
            <div class="message-label">🔍 Time Capsule</div>
            <div class="message-text">No talks matching <em>"${escapeHtml(query)}"</em> in ${year}. Try a different search.</div>
        `);
    } else {
        addMessage('system', `
            <div class="message-label">📚 ${results.length} talk${results.length > 1 ? 's' : ''} matching <em>"${escapeHtml(query)}"</em></div>
        `);
        const count = Math.min(results.length, 15);
        for (let i = 0; i < count; i++) {
            const t = results[i];
            const excerpt = t.body && t.body[0] ? t.body[0].slice(0, 140) + '...' : '';
            const origIdx = (talkData[year] || []).indexOf(t);
            addMessage('talk', `
                <div class="message-text talk-result" data-year="${year}" data-index="${origIdx}">
                    <div class="talk-title">${t.title || '(untitled)'}</div>
                    <div class="talk-speaker">${t.speaker} <span class="talk-badge">${t._session || ''}</span></div>
                    <div class="talk-excerpt">${excerpt}</div>
                </div>
            `);
        }
        if (results.length > 15) {
            addMessage('system', `<div class="message-text">... and ${results.length - 15} more matches</div>`);
        }
        // Re-bind click handlers
        document.querySelectorAll('.talk-result').forEach(el => {
            el.addEventListener('click', () => {
                const y = parseInt(el.dataset.year);
                const idx = parseInt(el.dataset.index);
                showTalkDetail(y, idx);
            });
        });
    }

    chatSend.disabled = false;
}

/* ─── Talk Detail Modal ─── */
function showTalkDetail(year, idx) {
    const talks = talkData[year];
    if (!talks || !talks[idx]) return;

    const t = talks[idx];
    talkDetailTitle.textContent = t.title || '(untitled)';
    talkDetailSpeaker.textContent = t.speaker;
    talkDetailMeta.textContent = `${t.source === 'web' ? '🌐 Web text' : '📄 OCR'} · ${t._session || ''} ${year}`;

    if (t.body && t.body.length > 0) {
        talkDetailBody.innerHTML = t.body.map(p => `<p>${escapeHtml(p)}</p>`).join('');
    } else {
        talkDetailBody.innerHTML = '<p><em>No body text available.</em></p>';
    }

    talkDetailOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeTalkDetail() {
    talkDetailOverlay.classList.remove('active');
    document.body.style.overflow = '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/* ─── Event Listeners ─── */
let currentYear = 1900;
let sliderTimeout = null;

yearSlider.addEventListener('input', () => {
    const year = parseInt(yearSlider.value);
    currentYear = year;
    yearDisplay.textContent = year;
    yearDisplay.classList.add('highlight');
    clearTimeout(sliderTimeout);
    sliderTimeout = setTimeout(() => {
        yearDisplay.classList.remove('highlight');
        updateForYear(year);
    }, 80);
});

chatSend.addEventListener('click', () => handleChat(currentYear));
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleChat(currentYear);
});

talkDetailOverlay.addEventListener('click', (e) => {
    if (e.target === talkDetailOverlay) closeTalkDetail();
});
$('#talk-detail-close').addEventListener('click', closeTalkDetail);

// Keyboard shortcut: Escape closes detail
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeTalkDetail();
});

/* ─── Init ─── */
async function init() {
    // Load corpus index first
    try {
        const resp = await fetch('data/unified/index.json');
        if (resp.ok) {
            corpusIndex = await resp.json();
        }
    } catch (e) {
        // Index not available, will load per-year individually
    }
    updateForYear(1900);
}
init();
