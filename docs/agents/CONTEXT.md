# Design System — Premium Glassmorphism (Dark Tech)

Adopted 2026-07-01 after UI prototype Variant A confirmation.

## CSS Custom Properties

Defined on `:root` in `frontend/src/App.vue`:

### Backgrounds

| Token              | Value                       | Usage                      |
| ------------------ | --------------------------- | -------------------------- |
| `--bg-primary`     | `hsl(240, 18%, 6%)`         | Page body                  |
| `--bg-surface`     | `hsla(240, 14%, 14%, 0.65)` | Subtle surface hover       |
| `--bg-sidebar`     | `hsla(240, 16%, 10%, 0.92)` | Left sidebar               |
| `--bg-glass`       | `hsla(240, 14%, 16%, 0.55)` | Default card/panel surface |
| `--bg-glass-hover` | `hsla(240, 14%, 20%, 0.65)` | Card hover state           |

### Glassmorphism

| Token                  | Value                             | Usage                         |
| ---------------------- | --------------------------------- | ----------------------------- |
| `--glass-border`       | `hsla(0, 0%, 100%, 0.07)`         | Card / panel borders          |
| `--glass-border-hover` | `hsla(0, 0%, 100%, 0.14)`         | Card border on hover          |
| `--glass-shadow`       | `0 8px 32px hsla(0, 0%, 0%, 0.4)` | Card box-shadow               |
| `--glass-blur`         | `20px`                            | `backdrop-filter` blur radius |

### Accent colors

| Token             | Value                | Usage                                 |
| ----------------- | -------------------- | ------------------------------------- |
| `--accent-green`  | `hsl(142, 76%, 45%)` | Bullish / completed / positive        |
| `--accent-red`    | `hsl(0, 76%, 52%)`   | Bearish / error / negative            |
| `--accent-blue`   | `hsl(211, 90%, 52%)` | Interactive / links / primary buttons |
| `--accent-gold`   | `hsl(42, 96%, 52%)`  | Thinking state / highlights           |
| `--accent-purple` | `hsl(262, 70%, 58%)` | Report chunks / special markers       |

### Text

| Token              | Value                     | Usage                   |
| ------------------ | ------------------------- | ----------------------- |
| `--text-primary`   | `hsl(0, 0%, 90%)`         | Primary body / headings |
| `--text-secondary` | `hsla(0, 0%, 100%, 0.6)`  | Secondary / meta text   |
| `--text-muted`     | `hsla(0, 0%, 100%, 0.35)` | Labels / placeholders   |

## Typography

- **Font stack**: `"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", sans-serif`
- **Body**: 15px, `--text-primary`
- **Code/monospace**: `"SF Mono", "Menlo", Consolas, monospace`
- **Headings**: Font-weight 600–700, letter-spacing `0.01em`

## Layout

- **Home page**: Full-width flex layout (sidebar + main). No `max-width` constraint.
- **Sidebar**: 260px, sticky to viewport top, full viewport height.
- **Content**: Flexible main area with padding `20px 24px 40px`.
- **Other pages**: Centered `max-width: 1200px` under the classic app header.

## Glass card pattern

Every card surface follows this pattern:

```css
.card-glass {
  background: var(--bg-glass);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: 14px;
  box-shadow: var(--glass-shadow);
}
```

Interactive cards add `transition: border-color 0.3s, background 0.3s` and `:hover` state using `--bg-glass-hover` / `--glass-border-hover`.

## Button system

| Variant   | Style                                                                | Usage                  |
| --------- | -------------------------------------------------------------------- | ---------------------- |
| Primary   | `linear-gradient(135deg, hsl(211,90%,52%), hsl(230,70%,48%))`        | Main CTA (开始分析)    |
| Secondary | `background: var(--bg-glass); border: 1px solid var(--glass-border)` | Secondary actions      |
| Small     | `padding: 5px 12px; font-size: 12px`                                 | Inline action (export) |

## Modal system

Two modal surfaces exist:

1. **Analysis Modal** — Centered glass overlay (`backdrop-filter: blur(8px)` overlay + `blur(32px)` modal), SSE streaming events with colored left borders per event type.
2. **Backtest Form Modal** — Same glass overlay pattern, form inputs with `--bg-glass` backgrounds.

## Chart

- K-line chart background: transparent (inherits from `--bg-primary` through the glass card)
- Up candles: `--accent-green`
- Down candles: `--accent-red`
- MA lines: golden (MA5), blue (MA10), purple (MA20), green (MA60)
- Bollinger bands: `#78909c`
- **Null data fix**: `leadingNull()` utility replaces leading-zero values with `null`; `connectNulls: false` prevents line stretching across empty periods.

## Z-index layers

| Layer                         | Value |
| ----------------------------- | ----- |
| App header                    | 100   |
| Backtest modal                | 200   |
| Analysis modal                | 1000  |
| Watchlist search overlay      | 2000  |
| Prototype switcher (dev only) | 9999  |

## To add a new component

1. Use `var(--...)` tokens — never hardcode hex colors.
2. Apply `.card-glass` pattern for any surface panel.
3. Use `backdrop-filter: blur(x)` for frosted-glass effect.
4. Follow the button system for interactive elements.
