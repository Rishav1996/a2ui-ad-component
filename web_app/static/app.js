/**
 * A2UI Continuous AI Chat & Sponsored Analytics Platform — Frontend Logic
 * Multi-Turn Context Retention with Real-Time SSE Token Streaming
 */

let currentSessionId = generateSessionId();
let isStreaming = false;
let turnCounter = 0;

function generateSessionId() {
  return `sess_${Math.random().toString(36).substring(2, 10)}`;
}

/**
 * Dynamically resolves the API base URL.
 * In unified hosting (Vercel or local), both UI and API run on the same origin,
 * so relative paths ("") work seamlessly with zero CORS overhead.
 */
function getApiBaseUrl() {
  return "";
}

// Initial setup on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  updateSessionDisplay();
  fetchAnalyticsData();
  const textarea = document.getElementById("chat-textarea");
  if (textarea) {
    textarea.focus();
    autoResizeTextarea(textarea);
  }
});

function updateSessionDisplay() {
  const badge = document.getElementById("session-badge");
  if (badge) {
    badge.textContent = `Session: #${currentSessionId.slice(-6)}`;
  }
}

// ==============================================================================
// Tab Navigation
// ==============================================================================
function switchTab(tab) {
  const chatTabBtn = document.getElementById("tab-chat-btn");
  const analyticsTabBtn = document.getElementById("tab-analytics-btn");
  const chatView = document.getElementById("chat-view");
  const analyticsView = document.getElementById("analytics-view");

  if (tab === "chat") {
    chatTabBtn.classList.add("active");
    analyticsTabBtn.classList.remove("active");
    chatView.classList.remove("hidden");
    analyticsView.classList.add("hidden");
  } else {
    analyticsTabBtn.classList.add("active");
    chatTabBtn.classList.remove("active");
    analyticsView.classList.remove("hidden");
    chatView.classList.add("hidden");
    fetchAnalyticsData();
  }
}

// ==============================================================================
// Conversation Thread & Multi-Turn Chat
// ==============================================================================
function handleNewChat() {
  if (isStreaming) return;
  currentSessionId = generateSessionId();
  turnCounter = 0;
  updateSessionDisplay();

  const messagesList = document.getElementById("chat-messages-list");
  if (messagesList) {
    messagesList.innerHTML = "";
  }

  const starter = document.getElementById("chat-starter");
  if (starter) {
    starter.classList.remove("hidden");
  }

  const textarea = document.getElementById("chat-textarea");
  if (textarea) {
    textarea.value = "";
    textarea.focus();
  }
}

function runChipPrompt(prompt) {
  if (isStreaming) return;
  const textarea = document.getElementById("chat-textarea");
  if (textarea) {
    textarea.value = prompt;
  }
  submitMessage(prompt);
}

function handleTextareaKeyDown(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    handleChatSubmit(event);
  }
}

function autoResizeTextarea(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
}

function handleChatSubmit(event) {
  if (event) event.preventDefault();
  if (isStreaming) return;

  const textarea = document.getElementById("chat-textarea");
  const query = (textarea.value || "").trim();
  if (!query) return;

  textarea.value = "";
  textarea.style.height = "auto";
  submitMessage(query);
}

function scrollToBottom() {
  const scrollContainer = document.getElementById("chat-scroll-container");
  if (scrollContainer) {
    scrollContainer.scrollTop = scrollContainer.scrollHeight;
  }
}

// ==============================================================================
// Real-Time SSE Token Streaming
// ==============================================================================
async function submitMessage(query) {
  if (isStreaming) return;
  isStreaming = true;
  turnCounter++;
  const turnId = turnCounter;

  // Hide empty starter state
  const starter = document.getElementById("chat-starter");
  if (starter) {
    starter.classList.add("hidden");
  }

  const messagesList = document.getElementById("chat-messages-list");
  const sendBtn = document.getElementById("chat-send-btn");
  if (sendBtn) sendBtn.disabled = true;

  // Append new turn group (User message + Assistant placeholder)
  const turnGroup = document.createElement("div");
  turnGroup.className = "chat-turn-group";
  turnGroup.id = `turn-${turnId}`;

  turnGroup.innerHTML = `
    <!-- User Bubble -->
    <div class="chat-msg-user">
      <div class="user-bubble">${escapeHtml(query)}</div>
      <div class="user-avatar">You</div>
    </div>

    <!-- Assistant Turn Container -->
    <div class="chat-msg-assistant" id="assistant-${turnId}">
      <div class="assistant-avatar">AI</div>
      <div class="assistant-bubble-wrap">
        <div class="assistant-header">
          <div class="assistant-title-group">
            <span class="assistant-name">A2UI AI Research</span>
            <span class="msg-status-pill" id="status-${turnId}">
              <span class="status-dot"></span>
              <span class="status-text" id="status-text-${turnId}">Researching & coordinating agents...</span>
            </span>
          </div>
          <span class="intent-pill cat-general hidden" id="intent-${turnId}">General</span>
        </div>

        <!-- Real-Time Streaming Markdown Content -->
        <div class="organic-response-body" id="body-${turnId}">
          <span class="streaming-cursor" id="cursor-${turnId}"></span>
        </div>

        <!-- Key Highlights Card -->
        <div class="highlights-card hidden" id="highlights-${turnId}">
          <div class="highlights-card-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
            Key Architectural Highlights
          </div>
          <ul id="highlights-list-${turnId}"></ul>
        </div>

        <!-- Inline A2UI v0.9 Sponsored Section (only revealed if cards > 0) -->
        <div class="turn-sponsored-container hidden" id="sponsored-${turnId}">
          <div class="turn-sponsored-header">
            <div class="sponsored-header-left">
              <span class="pill-badge sponsored-badge">A2UI v0.9 Verified Sponsors</span>
              <h4 class="turn-sponsored-title">Sponsored Recommendations</h4>
            </div>
            <div class="sponsored-view-toggle" id="view-toggle-${turnId}">
              <button class="view-toggle-btn active" data-mode="all" onclick="setComponentView('${turnId}', 'all')">All</button>
              <button class="view-toggle-btn" data-mode="banner" onclick="setComponentView('${turnId}', 'banner')">📢 AdBanner</button>
              <button class="view-toggle-btn" data-mode="cards" onclick="setComponentView('${turnId}', 'cards')">🃏 Cards</button>
            </div>
            <span class="sponsored-meta" id="sponsored-meta-${turnId}"></span>
          </div>
          <!-- Hero A2UI AdBanner Component -->
          <div class="ad-banner-slot" id="banner-slot-${turnId}"></div>
          <div class="cards-grid" id="cards-grid-${turnId}"></div>
        </div>

      </div>
    </div>
  `;

  messagesList.appendChild(turnGroup);
  scrollToBottom();

  let accumulatedText = "";
  const bodyEl = document.getElementById(`body-${turnId}`);
  const cursorEl = document.getElementById(`cursor-${turnId}`);
  const statusPill = document.getElementById(`status-${turnId}`);
  const statusText = document.getElementById(`status-text-${turnId}`);
  const intentPill = document.getElementById(`intent-${turnId}`);
  const highlightsCard = document.getElementById(`highlights-${turnId}`);
  const highlightsList = document.getElementById(`highlights-list-${turnId}`);
  const sponsoredContainer = document.getElementById(`sponsored-${turnId}`);
  const sponsoredMeta = document.getElementById(`sponsored-meta-${turnId}`);
  const cardsGrid = document.getElementById(`cards-grid-${turnId}`);
  const gatingCard = document.getElementById(`gating-${turnId}`);

  try {
    const streamUrl = `${getApiBaseUrl()}/api/chat/stream?query=${encodeURIComponent(query)}&session_id=${encodeURIComponent(currentSessionId)}`;
    const response = await fetch(streamUrl);

    if (!response.ok) {
      throw new Error(`Server returned status ${response.status}: ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // Keep incomplete chunk in buffer

      for (const line of lines) {
        if (!line.trim() || !line.startsWith("data: ")) continue;
        const jsonStr = line.slice(6).trim();
        try {
          const evt = JSON.parse(jsonStr);

          // 1. Status Progress Event
          if (evt.type === "status") {
            if (statusText) statusText.textContent = evt.message || "Synthesizing...";
          }

          // 2. Incremental Streaming Token Delta
          else if (evt.type === "text_delta") {
            accumulatedText += evt.delta || "";
            if (bodyEl) {
              bodyEl.innerHTML = renderMarkdown(accumulatedText) + `<span class="streaming-cursor" id="cursor-${turnId}"></span>`;
            }
            scrollToBottom();
          }

          // 3. Final Turn Completion Event (with A2UI Cards & Highlights)
          else if (evt.type === "turn_complete") {
            if (statusPill) statusPill.classList.add("hidden");

            // Final render of organic text (remove cursor)
            const summaryText = evt.organic_summary || accumulatedText;
            if (bodyEl) {
              bodyEl.innerHTML = renderMarkdown(summaryText);
            }

            // Highlights
            if (evt.highlights && evt.highlights.length > 0) {
              highlightsCard.classList.remove("hidden");
              highlightsList.innerHTML = evt.highlights.map(h => `<li>${escapeHtml(h)}</li>`).join("");
            }

            // Intent category pill
            if (intentPill && evt.intent_category) {
              intentPill.textContent = formatCategoryName(evt.intent_category);
              intentPill.className = `intent-pill ${getCategoryClass(evt.intent_category)}`;
              intentPill.classList.remove("hidden");
            }

            // A2UI v0.9 Sponsored Section (only shown when actual ads are present)
            if (evt.cards && evt.cards.length > 0) {
              sponsoredContainer.classList.remove("hidden");
              cardsGrid.classList.remove("hidden");
              sponsoredMeta.textContent = `${evt.cards.length} Verified Sponsors • Google Ads & Shopping`;

              // Render Hero A2UI AdBanner
              const bannerData = evt.ad_banner || evt.cards[0];
              const bannerSlot = document.getElementById(`banner-slot-${turnId}`);
              if (bannerData && bannerSlot) {
                const bannerLogo = bannerData.media_url || `https://www.google.com/s2/favicons?domain=${encodeURIComponent(bannerData.sponsor_name)}.com&sz=128`;
                const bannerTarget = bannerData.target_url || "#";
                const bannerCampId = bannerData.campaign_id || `camp_banner_${turnId}`;

                bannerSlot.innerHTML = `
                  <div class="a2ui-ad-banner" role="region" aria-label="A2UI Sponsored Banner from ${escapeHtml(bannerData.sponsor_name || 'Verified Sponsor')}">
                    <div class="ad-banner-content">
                      <div class="ad-banner-header">
                        <div class="ad-banner-brand">
                          <img class="ad-banner-favicon" src="${escapeHtml(bannerLogo)}" alt="Logo" onerror="this.src='https://www.google.com/s2/favicons?domain=google.com&sz=128'">
                          <span class="ad-banner-sponsor">${escapeHtml(bannerData.sponsor_name || "Verified Sponsor")}</span>
                        </div>
                        <div class="ad-banner-badges">
                          <span class="ad-banner-disclosure">Sponsored</span>
                          <span class="clearing-price-badge">₹${Number(bannerData.clearing_price_inr || 350).toFixed(0)} CPM</span>
                        </div>
                      </div>
                      <h3 class="ad-banner-headline">${escapeHtml(bannerData.headline || "Featured Promotional Solution")}</h3>
                      <p class="ad-banner-body">${escapeHtml(bannerData.body || "")}</p>
                    </div>
                    <div class="ad-banner-action">
                      <a class="ad-banner-cta-btn" href="${escapeHtml(bannerTarget)}" target="_blank" rel="noopener noreferrer" onclick="handleCardClick(event, '${currentSessionId}', '${bannerCampId}', '${escapeHtml(bannerTarget)}')">
                        <span>${escapeHtml(bannerData.cta_label || "Learn More")}</span>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                      </a>
                    </div>
                  </div>
                `;
              }

              cardsGrid.innerHTML = "";
              evt.cards.forEach((card, idx) => {
                const cardEl = document.createElement("div");
                cardEl.className = "sponsored-card";

                const logoUrl = card.media_url || `https://www.google.com/s2/favicons?domain=${encodeURIComponent(card.sponsor_name)}.com&sz=128`;
                const badgeText = card.badge || "Sponsored";
                const campaignId = card.campaign_id || `camp_${idx}`;
                const targetUrl = card.target_url || "#";

                cardEl.innerHTML = `
                  <div class="card-top-row">
                    <div class="sponsor-brand">
                      <img class="sponsor-logo" src="${escapeHtml(logoUrl)}" alt="Logo" onerror="this.src='https://www.google.com/s2/favicons?domain=google.com&sz=128'">
                      <span class="sponsor-name">${escapeHtml(card.sponsor_name || "Verified Sponsor")}</span>
                    </div>
                    <span class="disclosure-pill">Sponsored</span>
                  </div>
                  <h4 class="card-headline">${escapeHtml(card.headline || "Promoted Offer")}</h4>
                  <p class="card-body-text">${escapeHtml(card.body || "")}</p>
                  <div class="card-action-row">
                    <span class="card-badge-pill">${escapeHtml(badgeText)}</span>
                    <a class="card-cta-btn" href="${escapeHtml(targetUrl)}" target="_blank" rel="noopener noreferrer" onclick="handleCardClick(event, '${currentSessionId}', '${campaignId}', '${escapeHtml(targetUrl)}')">
                      <span>${escapeHtml(card.cta_label || "View Deal")}</span>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                    </a>
                  </div>
                `;
                cardsGrid.appendChild(cardEl);
              });
            } else {
              // Completely hide the entire sponsored container if there are no ads
              sponsoredContainer.classList.add("hidden");
            }

            // Refresh Stream Log table in background
            fetchAnalyticsData();
            scrollToBottom();
          }

          // 4. Error Event
          else if (evt.type === "error") {
            if (statusPill) statusPill.classList.add("hidden");
            if (bodyEl) {
              bodyEl.innerHTML = `<p style="color: var(--danger); font-weight: 600;">⚠️ Pipeline Error: ${escapeHtml(evt.message)}</p>`;
            }
          }
        } catch (err) {
          console.error("Error parsing SSE event chunk:", err, line);
        }
      }
    }
  } catch (err) {
    console.error("Stream communication error:", err);
    if (statusPill) statusPill.classList.add("hidden");
    if (bodyEl) {
      bodyEl.innerHTML = `<p style="color: var(--danger); font-weight: 600;">⚠️ Network Connection Error: ${escapeHtml(err.message)}</p>`;
    }
  } finally {
    isStreaming = false;
    if (sendBtn) sendBtn.disabled = false;
    const textarea = document.getElementById("chat-textarea");
    if (textarea) textarea.focus();
    scrollToBottom();
  }
}

// ==============================================================================
// Lightweight Markdown Formatter
// ==============================================================================
function renderMarkdown(raw) {
  if (!raw) return "";

  let text = escapeHtml(raw);

  // Bold **text**
  text = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  // Italic *text*
  text = text.replace(/\*(.*?)\*/g, "<em>$1</em>");

  // Inline code `code`
  text = text.replace(/`([^`]+)`/g, "<code style='background: var(--bg-subtle); padding: 2px 5px; border-radius: 4px; font-size: 13px;'>$1</code>");

  // Split lines to detect bullet points and paragraphs
  const lines = text.split("\n");
  const formattedLines = [];
  let inList = false;

  for (let line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ") || trimmed.startsWith("• ")) {
      if (!inList) {
        formattedLines.push("<ul style='padding-left: 20px; margin: 8px 0;'>");
        inList = true;
      }
      formattedLines.push(`<li style='margin-bottom: 4px;'>${trimmed.substring(2)}</li>`);
    } else {
      if (inList) {
        formattedLines.push("</ul>");
        inList = false;
      }
      if (trimmed) {
        formattedLines.push(`<p style='margin-bottom: 10px;'>${trimmed}</p>`);
      }
    }
  }

  if (inList) {
    formattedLines.push("</ul>");
  }

  return formattedLines.join("");
}

// ==============================================================================
// Click Telemetry
// ==============================================================================
async function handleCardClick(event, sessionId, campaignId, targetUrl) {
  try {
    fetch(`${getApiBaseUrl()}/api/click`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        campaign_id: campaignId,
      }),
    });
  } catch (e) {
    console.error("Click logging error:", e);
  }
}

// ==============================================================================
// Search & Ad Stream Log Logic
// ==============================================================================
async function fetchAnalyticsData() {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/analytics`);
    if (!response.ok) return;

    const data = await response.json();
    const auditLog = data.audit_log || [];

    // Update Quota & Free Tier Health Cards
    if (data.quota_health) {
      updateQuotaUI(data.quota_health);
    }

    const tableBody = document.getElementById("audit-table-body");
    if (!tableBody) return;

    if (!auditLog || auditLog.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="4" class="empty-state">No search queries logged yet. Start a conversation above!</td></tr>`;
      return;
    }

    tableBody.innerHTML = auditLog.map(audit => {
      const timeFormatted = new Date(audit.timestamp * 1000).toLocaleTimeString();
      const catClass = getCategoryClass(audit.intent_category);
      const catLabel = formatCategoryName(audit.intent_category);

      let adsHtml = "";
      if (audit.ads_summary && audit.ads_summary.length > 0) {
        adsHtml = `<div class="ads-summary-container">` + audit.ads_summary.map(ad => `
          <span class="ad-summary-pill" title="${escapeHtml(ad.headline)}">
            <strong>${escapeHtml(ad.sponsor_name)}</strong> ${ad.badge ? `• ${escapeHtml(ad.badge)}` : ''}
          </span>
        `).join("") + `</div>`;
      } else {
        adsHtml = `<span class="ad-summary-pill" style="color: #059669; background: #ecfdf5;">🌿 0 Ads (Educational Gating)</span>`;
      }

      return `
        <tr>
          <td><code style="font-size: 11px;">${timeFormatted}</code></td>
          <td><strong>${escapeHtml(audit.query_text)}</strong></td>
          <td><span class="category-badge ${catClass}">${catLabel}</span></td>
          <td>${adsHtml}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to fetch stream log:", err);
  }
}

function updateQuotaUI(quotaHealth) {
  const isServerDown = quotaHealth.is_server_down;
  const serpapi = quotaHealth.serpapi || {};
  const llm = quotaHealth.llm || {};

  // 1. SerpApi Quota Card
  const serpPlan = document.getElementById("serpapi-plan-name");
  const serpBadge = document.getElementById("serpapi-status-badge");
  const serpLeft = document.getElementById("serpapi-searches-left");
  const serpFill = document.getElementById("serpapi-progress-fill");
  const serpFooter = document.getElementById("serpapi-footer-text");

  const totalSerp = serpapi.total_searches || 250;
  const leftSerp = serpapi.searches_left !== undefined ? serpapi.searches_left : 205;
  const usedSerp = serpapi.searches_used !== undefined ? serpapi.searches_used : Math.max(0, totalSerp - leftSerp);

  if (serpPlan) serpPlan.textContent = `${serpapi.plan || "Free Plan"} (${totalSerp}/mo)`;
  if (serpLeft) serpLeft.textContent = `${leftSerp} / ${totalSerp}`;

  if (serpBadge) {
    if (serpapi.is_exhausted || leftSerp <= 0) {
      serpBadge.textContent = "Exhausted (0 Left)";
      serpBadge.className = "quota-status-badge exhausted";
    } else {
      serpBadge.textContent = `Active (${leftSerp} Left)`;
      serpBadge.className = "quota-status-badge active";
    }
  }

  if (serpFill) {
    const pctLeft = Math.max(0, Math.min(100, (leftSerp / totalSerp) * 100));
    serpFill.style.width = `${pctLeft}%`;
    if (pctLeft < 15) {
      serpFill.className = "quota-progress-fill danger";
    } else if (pctLeft < 35) {
      serpFill.className = "quota-progress-fill warning";
    } else {
      serpFill.className = "quota-progress-fill";
    }
  }

  if (serpFooter) {
    if (serpapi.is_exhausted || leftSerp <= 0) {
      serpFooter.innerHTML = `<span style="color: var(--danger); font-weight: 700;">Free quota complete. Wait for next month.</span>`;
    } else {
      serpFooter.textContent = `${usedSerp} searches used of ${totalSerp} monthly allowance • Resets monthly`;
    }
  }

  // 2. Google Gemini LLM Card
  const llmModel = document.getElementById("llm-model-name");
  const llmBadge = document.getElementById("llm-status-badge");
  const llmStatus = document.getElementById("llm-quota-status");
  const llmFill = document.getElementById("llm-progress-fill");
  const llmFooter = document.getElementById("llm-footer-text");

  const dailyLimit = llm.daily_limit || 1500;
  const leftLlm = llm.requests_left_today !== undefined ? llm.requests_left_today : 1500;
  const usedToday = llm.requests_used_today || 0;
  const tokensToday = llm.tokens_used_today || 0;
  const rpmLimit = llm.rpm_limit || 30;

  if (llmModel) llmModel.textContent = `${llm.model || "gemini-flash-lite"} (${dailyLimit.toLocaleString()} RPD)`;
  if (llmStatus) {
    llmStatus.textContent = `${leftLlm.toLocaleString()} / ${dailyLimit.toLocaleString()}`;
  }

  if (llmBadge) {
    if (llm.is_exhausted || leftLlm <= 0) {
      llmBadge.textContent = "Exhausted (0 Left)";
      llmBadge.className = "quota-status-badge exhausted";
    } else {
      llmBadge.textContent = `Active (${leftLlm.toLocaleString()} Left)`;
      llmBadge.className = "quota-status-badge active";
    }
  }

  if (llmFill) {
    const pctLeft = Math.max(0, Math.min(100, (leftLlm / dailyLimit) * 100));
    llmFill.style.width = `${pctLeft}%`;
    if (pctLeft < 15) {
      llmFill.className = "quota-progress-fill danger";
    } else if (pctLeft < 35) {
      llmFill.className = "quota-progress-fill warning";
    } else {
      llmFill.className = "quota-progress-fill llm-fill";
    }
  }

  if (llmFooter) {
    if (llm.is_exhausted || leftLlm <= 0) {
      llmFooter.innerHTML = `<span style="color: var(--danger); font-weight: 700;">Free quota complete. Wait for next month / daily reset.</span>`;
    } else {
      const tokensStr = tokensToday > 0 ? ` • ${tokensToday.toLocaleString()} tokens used` : "";
      llmFooter.textContent = `${usedToday} requests used today • Rate limit: ${rpmLimit} RPM • Free Tier${tokensStr}`;
    }
  }

  // 3. Global Server Down Banners & Input Gating
  const chatBanner = document.getElementById("chat-server-down-banner");
  const analyticsBanner = document.getElementById("analytics-server-down-banner");
  const sessionBadge = document.getElementById("session-badge");
  const statusIndicator = document.querySelector(".status-indicator");
  const chatInputBox = document.querySelector(".chat-input-box");
  const chatTextarea = document.getElementById("chat-textarea");
  const chatSendBtn = document.getElementById("chat-send-btn");

  if (isServerDown) {
    if (chatBanner) chatBanner.classList.remove("hidden");
    if (analyticsBanner) analyticsBanner.classList.remove("hidden");
    if (sessionBadge) sessionBadge.textContent = "Server Down (Quota Complete)";
    if (statusIndicator) statusIndicator.classList.add("down");
    if (chatInputBox) chatInputBox.classList.add("disabled");
    if (chatTextarea) {
      chatTextarea.disabled = true;
      chatTextarea.placeholder = "Free quota is complete and this server is down. Please wait for next month.";
    }
    if (chatSendBtn) chatSendBtn.disabled = true;
  } else {
    if (chatBanner) chatBanner.classList.add("hidden");
    if (analyticsBanner) analyticsBanner.classList.add("hidden");
    if (statusIndicator) statusIndicator.classList.remove("down");
    if (chatInputBox) chatInputBox.classList.remove("disabled");
    if (chatTextarea && !isStreaming) {
      chatTextarea.disabled = false;
      chatTextarea.placeholder = "Ask a question or follow up on previous answers...";
    }
    if (chatSendBtn && !isStreaming) chatSendBtn.disabled = false;
  }
}

async function handleResetAnalytics() {
  if (confirm("Are you sure you want to clear the query search log?")) {
    try {
      await fetch(`${getApiBaseUrl()}/api/analytics/reset`, { method: "POST" });
      fetchAnalyticsData();
    } catch (e) {
      console.error("Failed to reset stream log:", e);
    }
  }
}

// ==============================================================================
// Utilities
// ==============================================================================
function getCategoryClass(category) {
  if (!category) return "cat-general";
  if (category.includes("gpu")) return "cat-gpu";
  if (category.includes("saas")) return "cat-saas";
  if (category.includes("travel")) return "cat-travel";
  if (category.includes("finance") || category.includes("insurance")) return "cat-finance";
  if (category.includes("edu") || category.includes("educational")) return "cat-edu";
  return "cat-general";
}

function formatCategoryName(category) {
  if (!category) return "General";
  return category
    .replace(/_/g, " ")
    .replace(/\b\w/g, l => l.toUpperCase());
}

function escapeHtml(text) {
  if (!text) return "";
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}
// ==============================================================================
// A2UI Component View Switcher (All vs AdBanner vs SponsoredCards)
// ==============================================================================
function setComponentView(turnId, mode) {
  const container = document.getElementById(`sponsored-${turnId}`);
  if (!container) return;
  const bannerSlot = document.getElementById(`banner-slot-${turnId}`);
  const cardsGrid = document.getElementById(`cards-grid-${turnId}`);
  const toggleBtns = container.querySelectorAll('.view-toggle-btn');

  toggleBtns.forEach(btn => {
    if (btn.getAttribute('data-mode') === mode) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  if (mode === 'all') {
    if (bannerSlot) bannerSlot.style.display = 'block';
    if (cardsGrid) cardsGrid.style.display = 'grid';
  } else if (mode === 'banner') {
    if (bannerSlot) bannerSlot.style.display = 'block';
    if (cardsGrid) cardsGrid.style.display = 'none';
  } else if (mode === 'cards') {
    if (bannerSlot) bannerSlot.style.display = 'none';
    if (cardsGrid) cardsGrid.style.display = 'grid';
  }
}
