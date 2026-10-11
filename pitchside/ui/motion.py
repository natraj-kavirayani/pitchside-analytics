"""
Movement: tab transitions, entrance animations and hover feedback.

The motion is declared as data (``KEYFRAMES``, ``ANIMATIONS``,
``TRANSITIONS``) and turned into CSS by ``motion_css()``. That keeps the
rules checkable: the unit tests assert every animation uses keyframes
that exist and finishes within ``MAX_SETTLE_MS``, and the e2e tests check
the animations actually run in a browser.

Two things switch all of it off:

- the viewer's OS "reduce motion" setting: every rule sits inside
  ``@media (prefers-reduced-motion: no-preference)``;
- the app's own "Reduce motion" toggle: ``motion_css()`` is then not
  injected at all.

Either way nothing is left half-animated: content starts visible and the
animations only ever play it in. Entrance animations use fill mode
"backwards": they hold their first frame during any delay, then hand the
element back to its own styles, which their last frame matches. That
leaves those properties free for transitions, such as the match
overview shrinking into its pill.

How tab transitions work: Streamlit 1.64 mounts a fresh tab panel
element each time a tab is selected, and a CSS animation runs whenever
its element is mounted, so the panel's entrance animation replays on
every switch with no JavaScript.
"""

from dataclasses import dataclass

import streamlit as st

from pitchside.ui.overview import CLOSED as OVERVIEW_CLOSED
from pitchside.ui.overview import MINIMIZE as OVERVIEW_MINIMIZE
from pitchside.ui.overview import OPEN as OVERVIEW_OPEN
from pitchside.ui.overview import PILL as OVERVIEW_PILL
from pitchside.ui.overview import STRIP as OVERVIEW_STRIP

EASE_OUT = "cubic-bezier(0.16, 1, 0.3, 1)"  # fast start, gentle settle
EASE_SPRING = "cubic-bezier(0.34, 1.56, 0.64, 1)"  # slight overshoot

# The longest any element may take (delay + duration) to finish moving.
# Past this, motion stops feeling like feedback and starts feeling slow.
MAX_SETTLE_MS = 1200

KEYFRAMES: dict[str, str] = {
    "ps-panel-in": "from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; }",
    "ps-rise": "from { opacity: 0; transform: translateY(14px) scale(0.985); } to { opacity: 1; transform: none; }",
    "ps-fade": "from { opacity: 0; } to { opacity: 1; }",
    "ps-slide-in": "from { opacity: 0; transform: translateX(-12px); } to { opacity: 1; transform: none; }",
    "ps-grow-x": "from { transform: scaleX(0); } to { transform: scaleX(1); }",
    "ps-grow-y": "from { transform: scaleY(0); } to { transform: scaleY(1); }",
    "ps-roll-in": "from { opacity: 0; transform: translateX(-24px) rotate(-180deg); } to { opacity: 1; transform: none; }",
}

# The open tab's panel. Lazy tabs also leave an empty, inert
# stTabPanel placeholder for every other tab; only the open one has the
# tabpanel role.
PANEL = '[data-testid="stTabPanel"][role="tabpanel"]'
# Each block inside a tab panel (chart, caption, table, ...).
PANEL_ITEM = f'{PANEL} > [data-testid="stVerticalBlock"] > *'
# Each block on the About page (its container has key "ps-about").
ABOUT_ITEM = ".st-key-ps-about > *"
STAGGERED_ITEMS = 6
STAGGER_STEP_MS = 60
# Buttons that look like buttons; text buttons only change colour.
SOLID_BUTTON = '.stButton > button:not([kind="tertiary"])'
TEXT_BUTTON = '.stButton > button[kind="tertiary"]'


@dataclass(frozen=True)
class Animation:
    """One entrance animation.

    ``stagger_ms`` delays each element by ``var(--i)`` steps, for markup
    that numbers its own items (``style="--i:2"``).
    """

    selector: str
    keyframes: str
    duration_ms: int
    delay_ms: int = 0
    stagger_ms: int = 0
    easing: str = EASE_OUT
    origin: str | None = None  # transform-origin, for the grow animations
    max_index: int = 0  # highest --i used, so the settle time can be checked

    @property
    def settle_ms(self) -> int:
        return self.delay_ms + self.stagger_ms * self.max_index + self.duration_ms

    def css(self) -> str:
        delay = f"{self.delay_ms}ms"
        if self.stagger_ms:
            delay = f"calc({self.delay_ms}ms + var(--i, 0) * {self.stagger_ms}ms)"
        rule = f"animation: {self.keyframes} {self.duration_ms}ms {self.easing} {delay} backwards;"
        if self.origin:
            rule += f" transform-origin: {self.origin}; transform-box: fill-box;"
        return f"{self.selector} {{ {rule} }}"


@dataclass(frozen=True)
class Transition:
    """How ``properties`` change on elements matching ``selector``.

    Each property eases over ``duration_ms``, unless ``timing`` gives it
    its own ``(property, duration_ms, delay_ms)``. Hover and focus
    feedback uses the plain form; the match overview staggers its
    properties so the box changes shape while its content fades.
    """

    selector: str
    properties: tuple[str, ...]
    duration_ms: int = 180
    timing: tuple[tuple[str, int, int], ...] = ()

    def _timing(self, prop: str) -> tuple[int, int]:
        return next(((d, delay) for p, d, delay in self.timing if p == prop), (self.duration_ms, 0))

    @property
    def settle_ms(self) -> int:
        return max(sum(self._timing(p)) for p in self.properties)

    def css(self) -> str:
        parts = []
        for prop in self.properties:
            duration, delay = self._timing(prop)
            parts.append(f"{prop} {duration}ms {EASE_OUT}" + (f" {delay}ms" if delay else ""))
        return f"{self.selector} {{ transition: {', '.join(parts)}; }}"


def staggered(item: str) -> tuple[Animation, ...]:
    """Blocks matching ``item`` rise in one after another, in page order.

    The first ``STAGGERED_ITEMS`` get increasing delays; any after that
    arrive together with the last of them.
    """
    first = tuple(
        Animation(f"{item}:nth-child({n})", "ps-rise", 420, delay_ms=60 + STAGGER_STEP_MS * (n - 1))
        for n in range(1, STAGGERED_ITEMS + 1)
    )
    rest = Animation(f"{item}:nth-child(n+{STAGGERED_ITEMS + 1})", "ps-rise", 420,
                     delay_ms=60 + STAGGER_STEP_MS * STAGGERED_ITEMS)
    return (*first, rest)


ANIMATIONS: tuple[Animation, ...] = (
    # Tab switches: the whole panel glides up, then its blocks follow in turn.
    Animation(PANEL, "ps-panel-in", 380),
    *staggered(PANEL_ITEM),
    # The About page's sections arrive the same way.
    *staggered(ABOUT_ITEM),
    # The selected tab's underline grows out from its centre.
    Animation('[data-testid="stTabs"] [role="tab"] .react-aria-SelectionIndicator', "ps-grow-x", 320,
              easing=EASE_SPRING, origin="center"),
    # Header: the ball rolls in, the logo's bars rise one after another.
    Animation(".ps-logo-ball", "ps-roll-in", 700, origin="center"),
    Animation(".ps-logo-bar", "ps-grow-y", 520, delay_ms=200, stagger_ms=110, max_index=2,
              easing=EASE_SPRING, origin="bottom"),
    Animation(".ps-title", "ps-slide-in", 520, delay_ms=120),
    # Match summary: each row rises, then its bars grow out from the middle.
    Animation(".ps-summary", "ps-fade", 300),
    Animation(".ps-stat", "ps-rise", 420, delay_ms=80, stagger_ms=70, max_index=4),
    Animation(".ps-bar-left", "ps-grow-x", 650, delay_ms=180, stagger_ms=70, max_index=4,
              origin="right"),
    Animation(".ps-bar-right", "ps-grow-x", 650, delay_ms=180, stagger_ms=70, max_index=4,
              origin="left"),
)

# How long the overview takes to change shape between strip and pill.
MORPH_MS = 520
# What the box itself animates while it changes shape.
_MORPH = ("width", "height", "padding", "border-radius", "border-color")


def _morph(selector: str, fade_ms: int, fade_delay_ms: int, hide_delay_ms: int) -> Transition:
    """The box changes shape over MORPH_MS while its opacity fades on its
    own schedule; visibility flips at ``hide_delay_ms``, so the hidden
    state can't be clicked or focused."""
    return Transition(selector, (*_MORPH, "opacity", "visibility"), MORPH_MS, timing=(
        ("opacity", fade_ms, fade_delay_ms), ("visibility", 0, hide_delay_ms)))


# Strip <-> pill. A rule's timing applies when entering its state.
# Closing: the content fades first, the box shrinks to the pill's size,
# and the pill appears in its place as it arrives. Opening runs the
# other way round. The content below moves with the box's height.
OVERVIEW_TRANSITIONS: tuple[Transition, ...] = (
    _morph(f"{OVERVIEW_OPEN} {OVERVIEW_STRIP}", fade_ms=160, fade_delay_ms=0, hide_delay_ms=0),
    _morph(f"{OVERVIEW_CLOSED} {OVERVIEW_STRIP}", fade_ms=160, fade_delay_ms=MORPH_MS - 160,
           hide_delay_ms=MORPH_MS),
    Transition(f"{OVERVIEW_OPEN} {OVERVIEW_STRIP} > *", ("opacity",), 260,
               timing=(("opacity", 260, 260),)),
    Transition(f"{OVERVIEW_CLOSED} {OVERVIEW_STRIP} > *", ("opacity",), 140),
    Transition(f"{OVERVIEW_OPEN} {OVERVIEW_PILL}", ("opacity", "visibility"), 120,
               timing=(("visibility", 0, 120),)),
    Transition(f"{OVERVIEW_CLOSED} {OVERVIEW_PILL}", ("opacity", "visibility"), 200,
               timing=(("opacity", 200, MORPH_MS - 200),)),
    Transition(f"{OVERVIEW_OPEN} {OVERVIEW_MINIMIZE}", ("opacity", "visibility"), 200,
               timing=(("opacity", 200, MORPH_MS - 200),)),
    Transition(f"{OVERVIEW_CLOSED} {OVERVIEW_MINIMIZE}", ("opacity", "visibility"), 120,
               timing=(("visibility", 0, 120),)),
)

TRANSITIONS: tuple[Transition, ...] = (
    *OVERVIEW_TRANSITIONS,
    Transition('[data-testid="stTabs"] [role="tab"]', ("color", "background-color")),
    Transition(SOLID_BUTTON, ("transform", "box-shadow", "background-color")),
    Transition(TEXT_BUTTON, ("color", "text-decoration-color")),
    Transition('div[data-baseweb="select"] > div', ("box-shadow", "border-color")),
    Transition('[data-testid="stImage"] img', ("transform", "box-shadow"), 240),
)

HOVER_CSS = """
[data-testid="stTabs"] [role="tab"]:hover { background-color: color-mix(in srgb, var(--ps-accent) 12%, transparent); }
.stButton > button:not([kind="tertiary"]):hover { transform: translateY(-1px); box-shadow: 0 8px 20px -10px #22c55e; }
.stButton > button:not([kind="tertiary"]):active { transform: translateY(0) scale(0.97); }
div[data-baseweb="select"] > div:hover { box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25); }
[data-testid="stImage"] img:hover { transform: translateY(-3px); box-shadow: 0 18px 40px -20px rgba(0, 0, 0, 0.9); }
""".strip()


def motion_css() -> str:
    """Every animation and transition, as one ``<style>`` block.

    Wrapped in ``prefers-reduced-motion: no-preference`` so viewers who
    have asked their OS for less motion get none of it.
    """
    keyframes = "\n".join(f"@keyframes {name} {{ {body} }}" for name, body in KEYFRAMES.items())
    rules = "\n".join(a.css() for a in ANIMATIONS)
    transitions = "\n".join(t.css() for t in TRANSITIONS)
    return (
        "<style>\n@media (prefers-reduced-motion: no-preference) {\n"
        # Lets height animate to and from "auto" (Chromium-based browsers;
        # elsewhere the height changes at once and the rest still animates).
        ":root { interpolate-size: allow-keywords; }\n"
        f"{keyframes}\n{rules}\n{transitions}\n{HOVER_CSS}\n"
        "}\n</style>"
    )


def apply_motion(enabled: bool = True) -> None:
    """Inject the motion CSS, or an empty stylesheet when motion is off.

    The empty one keeps the page's element count the same either way.
    Streamlit identifies elements by position, so removing one would
    shift everything after it, and the tabs would be rebuilt (briefly
    duplicated, with the open tab lost) whenever motion was toggled.
    """
    st.markdown(motion_css() if enabled else "<style></style>", unsafe_allow_html=True)
