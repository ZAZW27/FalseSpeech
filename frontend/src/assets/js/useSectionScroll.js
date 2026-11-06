import { onMounted, onUnmounted } from "vue";

export function useSectionScroll(
    selector = "section[id]",
    { duration = 700, minWidth = 1024, offset = 0, cooldown = 150 } = {}
) {
    const EPS = 2;
    let locked = false;
    let rafId = null;

    const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

    // Measured live so it stays correct after resizes / content changes
    function getSections() {
        return [...document.querySelectorAll(selector)].map((el) => {
            const r = el.getBoundingClientRect();
            return { top: r.top + window.scrollY - offset, bottom: r.bottom + window.scrollY };
        });
    }

    function goTo(target) {
        const startY = window.scrollY;
        const diff = Math.round(target) - startY;
        if (Math.abs(diff) < 1) return;
        const startTime = performance.now();
        locked = true;

        const step = (now) => {
            const p = Math.min((now - startTime) / duration, 1);
            // "instant" so a global `scroll-behavior: smooth` doesn't fight the animation
            window.scrollTo({ top: startY + diff * ease(p), behavior: "instant" });
            if (p < 1) rafId = requestAnimationFrame(step);
            else setTimeout(() => (locked = false), cooldown);
        };
        rafId = requestAnimationFrame(step);
    }

    /** Returns true if we handled it (caller must preventDefault). */
    function handle(dir, delta) {
        const secs = getSections();
        if (!secs.length) return false;

        const y = window.scrollY;
        const vh = window.innerHeight;

        let i = -1;
        secs.forEach((s, k) => {
            if (s.top <= y + EPS) i = k;
        });
        if (i < 0) return false; // above the first section

        const s = secs[i];

        if (dir > 0) {
            const remaining = s.bottom - (y + vh);
            if (remaining > EPS) {
                // Still content below inside this section: scroll natively,
                // but stop exactly at the section's bottom edge.
                if (delta > remaining) {
                    goTo(Math.max(s.bottom - vh, s.top));
                    return true;
                }
                return false;
            }
            if (i === secs.length - 1) return false; // last section: let footer scroll natively
            goTo(secs[i + 1].top);
            return true;
        }

        const above = y - s.top;
        if (above > EPS) {
            if (delta > above) {
                goTo(s.top);
                return true;
            }
            return false;
        }
        if (i === 0) return false;
        const p = secs[i - 1];
        // Land on the *bottom* of the previous section so tall ones scroll back up naturally
        goTo(Math.max(p.bottom - vh, p.top));
        return true;
    }

    const blocked = (e) =>
        window.innerWidth < minWidth ||
        document.body.style.overflow === "hidden" || // modal open (body scroll lock)
        e.target?.closest?.("[data-no-snap]");

    function onWheel(e) {
        if (blocked(e) || e.ctrlKey || e.deltaY === 0) return;
        if (locked) {
            e.preventDefault();
            return;
        }
        if (handle(e.deltaY > 0 ? 1 : -1, Math.abs(e.deltaY))) e.preventDefault();
    }

    function onKey(e) {
        if (blocked(e) || e.ctrlKey || e.metaKey || e.altKey) return;
        if (e.target.closest?.("input, textarea, select, [contenteditable='true']")) return;

        const vh = window.innerHeight;
        const map = {
            ArrowDown: [1, 100],
            PageDown: [1, vh * 0.9],
            " ": [e.shiftKey ? -1 : 1, vh * 0.9],
            ArrowUp: [-1, 100],
            PageUp: [-1, vh * 0.9],
        };
        const m = map[e.key];
        if (!m) return;
        if (locked) {
            e.preventDefault();
            return;
        }
        if (handle(m[0], m[1])) e.preventDefault();
    }

    onMounted(() => {
        window.addEventListener("wheel", onWheel, { passive: false });
        window.addEventListener("keydown", onKey);
    });

    onUnmounted(() => {
        window.removeEventListener("wheel", onWheel);
        window.removeEventListener("keydown", onKey);
        if (rafId) cancelAnimationFrame(rafId);
    });
}