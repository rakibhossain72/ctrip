/* Admin UI helpers — small vanilla behaviors for the server-rendered admin pages.
 * Deliberately minimal: data is rendered server-side, JS only handles UI polish. */
(function () {
  "use strict";

  function toast(message, type) {
    type = type || "ok";
    var portal = document.getElementById("toasts-portal");
    if (!portal) return;

    var el = document.createElement("div");
    el.className =
      "toast-enter flex gap-3 items-start rounded-lg border p-4 shadow-md bg-white " +
      (type === "err" ? "border-red-200" : "border-emerald-200");

    var icon = document.createElement("span");
    icon.className =
      "h-5 w-5 flex-shrink-0 mt-0.5 " +
      (type === "err" ? "text-red-500" : "text-emerald-500");
    icon.textContent = type === "err" ? "\u26A0" : "\u2713";

    var body = document.createElement("div");
    body.className = "flex-1";
    var text = document.createElement("p");
    text.className = "text-xs font-semibold text-brand-text leading-tight";
    text.textContent = message;
    body.appendChild(text);

    var close = document.createElement("button");
    close.type = "button";
    close.className = "text-brand-dim hover:text-brand-text transition-colors cursor-pointer";
    close.textContent = "\u2715";
    close.addEventListener("click", function () { dismiss(); });

    el.appendChild(icon);
    el.appendChild(body);
    el.appendChild(close);
    portal.appendChild(el);

    function dismiss() {
      el.classList.remove("toast-enter");
      el.classList.add("toast-exit");
      window.setTimeout(function () { el.remove(); }, 220);
    }
    window.setTimeout(dismiss, 4500);
  }

  function openModal(id) {
    var m = document.getElementById(id);
    if (m) m.classList.remove("hidden");
  }

  function closeModal(id) {
    var m = document.getElementById(id);
    if (m) m.classList.add("hidden");
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    var ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) { /* noop */ }
    ta.remove();
    return Promise.resolve();
  }

  function formatTime(seconds) {
    var m = Math.floor(seconds / 60);
    var s = seconds % 60;
    return (m < 10 ? "0" + m : "" + m) + ":" + (s < 10 ? "0" + s : "" + s);
  }

  function countdown(expiresAtIso, labelId, barId, totalSeconds) {
    var label = document.getElementById(labelId);
    var bar = barId ? document.getElementById(barId) : null;
    if (!label) return;

    var exp = new Date(expiresAtIso).getTime();
    var tick = function () {
      var remaining = Math.max(0, Math.floor((exp - Date.now()) / 1000));
      label.textContent = formatTime(remaining);
      if (bar && totalSeconds) {
        bar.style.width = Math.min(100, (remaining / totalSeconds) * 100) + "%";
      }
      if (remaining > 0) window.setTimeout(tick, 1000);
    };
    tick();
  }

  function bindMobileDrawer() {
    var sidebar = document.getElementById("sidebar");
    var backdrop = document.getElementById("sidebar-backdrop");
    var openBtn = document.getElementById("menu-open");
    var closeBtn = document.getElementById("menu-close");
    if (!sidebar) return;

    function open() {
      sidebar.classList.add("translate-x-0");
      if (backdrop) backdrop.classList.remove("hidden");
    }
    function close() {
      sidebar.classList.remove("translate-x-0");
      if (backdrop) backdrop.classList.add("hidden");
    }
    if (openBtn) openBtn.addEventListener("click", open);
    if (closeBtn) closeBtn.addEventListener("click", close);
    if (backdrop) backdrop.addEventListener("click", close);
  }

  function handleFlash(flash) {
    if (!flash) return;
    if (flash.type === "raw_key") {
      var display = document.getElementById("rawKeyDisplay");
      if (display) {
        display.textContent = flash.message;
        openModal("rawKeyModal");
        return;
      }
    }
    toast(flash.message, flash.type === "err" ? "err" : "ok");
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindMobileDrawer();

    var boot = document.getElementById("admin-boot");
    var flash = null;
    if (boot && boot.dataset.flash) {
      try { flash = JSON.parse(boot.dataset.flash); } catch (e) { flash = null; }
    }
    handleFlash(flash);

    document.addEventListener("click", function (e) {
      var target = e.target.closest("[data-copy]");
      if (target) {
        copyText(target.getAttribute("data-copy")).then(function () {
          toast("Copied to clipboard", "ok");
        });
      }
      var cancel = e.target.closest("[data-close-modal]");
      if (cancel) closeModal(cancel.getAttribute("data-close-modal"));
      var overlay = e.target.closest("[data-modal-overlay]");
      if (overlay && e.target === overlay) closeModal(overlay.id);
    });
  });

  window.Admin = {
    toast: toast,
    openModal: openModal,
    closeModal: closeModal,
    copyText: copyText,
    countdown: countdown,
  };
})();
