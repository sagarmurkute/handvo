# UI & Accessibility Guidelines — HANDVO

## 1. Accessibility First
- **Zero Mouse/Keyboard Dependency**: Every screen action, tab switch, and text modification must be accessible via hand pointing / dwell / pinch triggers.
- **Large Target Footprint**: All touchable communication cards must have a minimum bounding size of `120x90px` to allow comfortable pointing margin of error.

## 2. Visual Hierarchy & Contrast
- **Dark Mode Palette**: Deep slate background (`#0f172a`, `#1e293b`) for maximum contrast and reduced eye fatigue.
- **Vibrant Categorization Accents**:
  - Common: Sky Blue (`#38bdf8`)
  - Needs: Cyan (`#06b6d4`)
  - Feelings: Pink (`#ec4899`)
  - Actions: Amber (`#f59e0b`)

## 3. Real-Time Dwell Feedback
- **Radial Progress Arc**: Circular 360-degree fill indicator giving clear timing perception (0% to 100% over 800ms).
- **Cooldown Flash**: Subtle amber/gray glow preventing repeated double triggers within 600ms cooldown window.
