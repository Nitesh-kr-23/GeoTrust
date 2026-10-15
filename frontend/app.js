const API_BASE = window.GEOTRUST_API_BASE || "http://127.0.0.1:8000";
document.getElementById("apiBaseLabel").textContent = API_BASE;

const latInput = document.getElementById("lat");
const lngInput = document.getElementById("lng");
const queryInput = document.getElementById("query");
const searchBtn = document.getElementById("searchBtn");
const useLocBtn = document.getElementById("useLocBtn");
const manualLocToggle = document.getElementById("manualLocToggle");
const manualLocFields = document.getElementById("manualLocFields");
const locStatusEl = document.getElementById("locStatus");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");

const bookingState = {};

// --- Location: auto-detect ---

function detectLocation({ silent = false } = {}) {
  if (!navigator.geolocation) {
    locStatusEl.textContent = "Geolocation isn't available — enter your location manually.";
    manualLocFields.hidden = false;
    return;
  }
  if (!silent) locStatusEl.textContent = "Detecting your location…";

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      latInput.value = pos.coords.latitude.toFixed(6);
      lngInput.value = pos.coords.longitude.toFixed(6);
      locStatusEl.textContent = "Location detected";
    },
    () => {
      locStatusEl.textContent = "Couldn't detect your location — enter it below.";
      manualLocFields.hidden = false;
    }
  );
}

detectLocation();

manualLocToggle.addEventListener("click", () => {
  manualLocFields.hidden = !manualLocFields.hidden;
});

useLocBtn.addEventListener("click", () => detectLocation());

searchBtn.addEventListener("click", runSearch);
queryInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") runSearch();
});

function setStatus(msg, isError = false) {
  statusEl.textContent = msg;
  statusEl.className = "status" + (isError ? " error" : "");
}

async function runSearch() {
  const lat = parseFloat(latInput.value);
  const lng = parseFloat(lngInput.value);
  const query = queryInput.value.trim();

  if (Number.isNaN(lat) || Number.isNaN(lng)) {
    setStatus("We need your location first — allow detection or enter it manually.", true);
    manualLocFields.hidden = false;
    return;
  }
  if (query.length < 2) {
    setStatus('Type what you\'re looking for — e.g. "electrician" or "AC repair".', true);
    return;
  }

  searchBtn.disabled = true;
  setStatus("Searching nearby shops, scoring trust, predicting price & ETA…");
  resultsEl.innerHTML = "";

  try {
    const resp = await fetch(`${API_BASE}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ latitude: lat, longitude: lng, query }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed (${resp.status})`);
    }

    const shops = await resp.json();
    renderResults(shops, query);
  } catch (e) {
    setStatus(e.message || "Something went wrong.", true);
  } finally {
    searchBtn.disabled = false;
  }
}

function renderResults(shops, query) {
  if (!shops.length) {
    setStatus("");
    resultsEl.innerHTML = `
      <div class="empty-state">
        No listings found for "${escapeHtml(query)}" nearby.
        <div class="hint">Try a broader term, or check your spelling.</div>
      </div>`;
    return;
  }

  setStatus("");
  const heading = `<p class="results-heading"><strong>${shops.length}</strong> nearby match${shops.length > 1 ? "es" : ""} for "${escapeHtml(query)}"</p>`;
  resultsEl.innerHTML = heading + shops.map(shopRowHtml).join("");

  shops.forEach((shop, index) => {
    const btn = document.getElementById(`call-${cssId(shop.place_id)}`);
    if (btn) btn.addEventListener("click", () => callShop(shop, query, index));
  });
}

function shopRowHtml(shop, index) {
  const pct = Math.round(shop.trust_score * 100);
  const circumference = 2 * Math.PI * 24;
  const offset = circumference * (1 - shop.trust_score);
  const priceLabel = shop.price_level != null ? "₹".repeat(shop.price_level + 1) : null;
  const priceRange = `₹${Math.round(shop.predicted_price_min)}–${Math.round(shop.predicted_price_max)}`;
  const eta = `~${Math.round(shop.predicted_eta_minutes)} min`;
  const hasPhone = Boolean(shop.phone_number);

  return `
    <div class="shop-row" id="card-${cssId(shop.place_id)}">
      <div class="rank-num">${index + 1}</div>
      <div class="trust-ring">
        <svg width="56" height="56" viewBox="0 0 56 56">
          <circle class="bg" cx="28" cy="28" r="24" stroke-width="5" fill="none"/>
          <circle class="fg" cx="28" cy="28" r="24" stroke-width="5" fill="none"
            stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"/>
        </svg>
        <div class="label">${pct}</div>
      </div>
      <div>
        <p class="shop-name">${escapeHtml(shop.name)}</p>
        <div class="shop-stats">
          <span class="stat">${shop.distance_km} km away</span>
          <span class="stat">★ ${shop.rating.toFixed(1)} (${shop.user_ratings_total})</span>
          ${priceLabel ? `<span class="stat">${priceLabel}</span>` : ""}
        </div>
        <div class="shop-stats">
          <span class="stat"><span class="price">${priceRange}</span></span>
          <span class="stat"><span class="eta">ETA ${eta}</span></span>
        </div>
        <div class="phone-line">
          ${hasPhone ? `<strong>${escapeHtml(shop.phone_number)}</strong>` : "No phone number on this listing"}
        </div>
      </div>
      <div class="call-col">
        <button class="call-btn" id="call-${cssId(shop.place_id)}" ${hasPhone ? "" : "disabled"}>
          📞 Call Shop
        </button>
      </div>
      <div class="lifecycle" id="lifecycle-${cssId(shop.place_id)}"></div>
    </div>`;
}

async function callShop(shop, query, index) {
  const lat = parseFloat(latInput.value);
  const lng = parseFloat(lngInput.value);
  const btn = document.getElementById(`call-${cssId(shop.place_id)}`);

  btn.disabled = true;
  btn.textContent = "Connecting…";

  try {
    // Record that the customer is contacting the shop
    const resp = await fetch(`${API_BASE}/api/bookings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        place_id: shop.place_id,
        category: query,
        customer_lat: lat,
        customer_lng: lng,
        predicted_price_min: shop.predicted_price_min,
        predicted_price_max: shop.predicted_price_max,
        predicted_eta_minutes: shop.predicted_eta_minutes,
      }),
    });
    if (!resp.ok) throw new Error("Couldn't start the call flow.");
    const booking = await resp.json();

    // Call acceptance signal
    const acceptResp = await fetch(`${API_BASE}/api/bookings/${booking.id}/accept`, { method: "POST" });
    if (!acceptResp.ok) throw new Error("Couldn't confirm the call.");

    // Open the phone dialer
    window.location.href = `tel:${shop.phone_number}`;

    bookingState[booking.id] = { status: "CALLED", shop };
    btn.textContent = "📞 Calling…";
    btn.classList.add("booked");

    renderLifecycle(shop.place_id, booking.id);
  } catch (e) {
    btn.disabled = false;
    btn.textContent = "📞 Call Shop";
    setStatus(e.message, true);
  }
}

function renderLifecycle(placeId, bookingId) {
  const state = bookingState[bookingId];
  const el = document.getElementById(`lifecycle-${cssId(placeId)}`);
  if (!el) return;

  if (state.status === "CALLED") {
    el.innerHTML = `
      <div class="lifecycle-row">
        <span class="status-pill pill-accepted">Called — job in progress</span>
        <button class="mini-btn" data-action="complete">Simulate: job completed</button>
      </div>
      <p class="sim-note">There's no shop-side app in this MVP to signal real job completion — this button stands in for that.</p>`;
    el.querySelector('[data-action="complete"]').addEventListener("click", () => transition(placeId, bookingId, "complete"));
  } else if (state.status === "COMPLETED") {
    el.innerHTML = `
      <div class="lifecycle-row">
        <span class="status-pill pill-completed">Completed</span>
      </div>
      <form class="review-form" id="review-${cssId(placeId)}">
        <label>Rate this shop</label>
        <div class="star-picker" data-value="0">
          ${[1, 2, 3, 4, 5].map((n) => `<span class="star" data-star="${n}">★</span>`).join("")}
        </div>
        <textarea placeholder="How did it go? (optional)" rows="2"></textarea>
        <button type="submit" class="mini-btn">Submit review</button>
      </form>`;
    wireReviewForm(placeId, bookingId);
  } else if (state.status === "REVIEWED") {
    el.innerHTML = `<div class="lifecycle-row"><span class="status-pill pill-reviewed">
      Review submitted — trust score updated (${state.oldTrust} → ${state.newTrust})</span></div>`;
  }
}

async function transition(placeId, bookingId, action) {
  try {
    const resp = await fetch(`${API_BASE}/api/bookings/${bookingId}/${action}`, { method: "POST" });
    if (!resp.ok) throw new Error(`Could not ${action} booking.`);
    const booking = await resp.json();
    // Backend status
    bookingState[bookingId].status = booking.status === "COMPLETED" ? "COMPLETED" : "CALLED";
    renderLifecycle(placeId, bookingId);
  } catch (e) {
    setStatus(e.message, true);
  }
}

function wireReviewForm(placeId, bookingId) {
  const form = document.getElementById(`review-${cssId(placeId)}`);
  const picker = form.querySelector(".star-picker");
  const stars = [...form.querySelectorAll(".star")];

  stars.forEach((star) => {
    star.addEventListener("click", () => {
      const val = parseInt(star.dataset.star, 10);
      picker.dataset.value = val;
      stars.forEach((s) => s.classList.toggle("filled", parseInt(s.dataset.star, 10) <= val));
    });
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const rating = parseInt(picker.dataset.value, 10);
    if (!rating) {
      setStatus("Pick a star rating before submitting.", true);
      return;
    }
    const text = form.querySelector("textarea").value;
    const shop = bookingState[bookingId].shop;
    const oldTrust = Math.round(shop.trust_score * 100);

    try {
      const resp = await fetch(`${API_BASE}/api/bookings/${bookingId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating, text: text || null }),
      });
      if (!resp.ok) throw new Error("Could not submit review.");

      // Fetch recomputed trust score
      const shopsResp = await fetch(`${API_BASE}/api/shops?category=${encodeURIComponent(shop.category)}`);
      const shops = await shopsResp.json();
      const updated = shops.find((s) => s.place_id === shop.place_id);
      const newTrust = updated ? Math.round(updated.trust_score * 100) : oldTrust;

      bookingState[bookingId].status = "REVIEWED";
      bookingState[bookingId].oldTrust = oldTrust;
      bookingState[bookingId].newTrust = newTrust;
      renderLifecycle(placeId, bookingId);
    } catch (err) {
      setStatus(err.message, true);
    }
  });
}

function cssId(placeId) {
  return placeId.replace(/[^a-zA-Z0-9]/g, "");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
