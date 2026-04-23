(function () {
    "use strict";

    var KEY = "ux_visitor_id";
    var visitorId = "";
    var sentMilestones = {};
    var milestones = [25, 50, 75, 100];

    function makeVisitorId() {
        return "v_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 12);
    }

    function loadVisitorId() {
        try {
            visitorId = localStorage.getItem(KEY) || "";
            if (!visitorId) {
                visitorId = makeVisitorId();
                localStorage.setItem(KEY, visitorId);
            }
        } catch (err) {
            visitorId = makeVisitorId();
        }
    }

    function sendJson(url, payload, useBeacon) {
        if (useBeacon && navigator.sendBeacon) {
            var blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
            navigator.sendBeacon(url, blob);
            return;
        }

        fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            keepalive: true,
        }).catch(function () {
            // Tracking should never block page behavior.
        });
    }

    function pagePayload() {
        return {
            visitor_id: visitorId,
            page_path: window.location.pathname || "/",
            referrer: document.referrer || "",
        };
    }

    function trackPageView() {
        sendJson("/api/traffic/page-view", pagePayload(), false);
    }

    function getScrollPercent() {
        var doc = document.documentElement;
        var body = document.body;
        var scrollTop = window.pageYOffset || doc.scrollTop || body.scrollTop || 0;
        var scrollHeight = Math.max(body.scrollHeight, doc.scrollHeight, body.offsetHeight, doc.offsetHeight);
        var viewport = window.innerHeight || doc.clientHeight || 1;
        var maxScrollable = Math.max(scrollHeight - viewport, 1);
        return Math.max(0, Math.min(100, Math.round((scrollTop / maxScrollable) * 100)));
    }

    function maybeTrackScroll() {
        var percent = getScrollPercent();
        for (var i = 0; i < milestones.length; i += 1) {
            var threshold = milestones[i];
            if (percent >= threshold && !sentMilestones[threshold]) {
                sentMilestones[threshold] = true;
                sendJson("/api/traffic/scroll", {
                    visitor_id: visitorId,
                    page_path: window.location.pathname || "/",
                    referrer: document.referrer || "",
                    scroll_percent: threshold,
                }, false);
            }
        }
    }

    function throttle(fn, wait) {
        var last = 0;
        return function () {
            var now = Date.now();
            if (now - last >= wait) {
                last = now;
                fn();
            }
        };
    }

    function bindEvents() {
        window.addEventListener("scroll", throttle(maybeTrackScroll, 400), { passive: true });
        window.addEventListener("beforeunload", function () {
            sendJson("/api/traffic/page-view", pagePayload(), true);
        });
    }

    loadVisitorId();
    trackPageView();
    bindEvents();
})();
