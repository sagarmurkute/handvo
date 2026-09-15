"""Theme and stylesheet management for HANDVO.

Provides themes for Dark Mode, Light Mode, and High-Contrast Accessibility.
"""

from typing import Dict


class ThemeManager:
    """Generates application and component stylesheets according to user preferences."""

    THEMES: Dict[str, Dict[str, str]] = {
        "dark": {
            "bg_main": "#0f172a",
            "bg_surface": "#1e293b",
            "bg_card": "#111827",
            "border": "#334155",
            "text_primary": "#f8fafc",
            "text_secondary": "#94a3b8",
            "accent": "#38bdf8",
            "accent_hover": "#0284c7",
        },
        "light": {
            "bg_main": "#f8fafc",
            "bg_surface": "#ffffff",
            "bg_card": "#f1f5f9",
            "border": "#cbd5e1",
            "text_primary": "#0f172a",
            "text_secondary": "#475569",
            "accent": "#0284c7",
            "accent_hover": "#0369a1",
        },
        "high_contrast": {
            "bg_main": "#000000",
            "bg_surface": "#000000",
            "bg_card": "#050505",
            "border": "#ffff00",
            "text_primary": "#ffffff",
            "text_secondary": "#ffff00",
            "accent": "#00ffff",
            "accent_hover": "#ffff00",
        },
    }

    @classmethod
    def get_stylesheet(cls, theme: str = "dark", button_size: str = "medium", high_contrast: bool = False) -> str:
        """Generate complete stylesheet with theme and button size scaling."""
        base_css = cls.get_main_stylesheet(theme=theme, high_contrast=high_contrast)
        size_styles = {
            "small": "QPushButton { min-height: 60px; font-size: 12px; }",
            "medium": "QPushButton { min-height: 80px; font-size: 14px; }",
            "large": "QPushButton { min-height: 100px; font-size: 16px; }",
        }
        btn_override = size_styles.get(button_size, size_styles["medium"])
        return f"{base_css}\n{btn_override}"

    @classmethod
    def get_main_stylesheet(cls, theme: str = "dark", high_contrast: bool = False) -> str:
        active_theme_key = "high_contrast" if high_contrast else theme
        t = cls.THEMES.get(active_theme_key, cls.THEMES["dark"])

        if active_theme_key == "high_contrast":
            return f"""
                QMainWindow {{ background-color: #000000; }}
                QLabel#title {{ color: #00ffff; font-size: 24px; font-weight: 900; }}
                QLabel#subtitle {{ color: #ffff00; font-size: 14px; font-weight: bold; }}
                QLabel#preview {{
                    background-color: #000000;
                    border: 3px solid #ffff00;
                    border-radius: 4px;
                    color: #ffffff;
                    font-size: 16px;
                }}
                QPushButton {{
                    font-size: 14px;
                    font-weight: 900;
                    padding: 10px 18px;
                    border-radius: 4px;
                    border: 2px solid #ffff00;
                    color: #ffffff;
                    background-color: #000000;
                }}
                QPushButton:hover {{ background-color: #ffff00; color: #000000; }}
                QPushButton#btnStart {{ background-color: #000000; border-color: #00ffff; color: #00ffff; }}
                QPushButton#btnStart:hover {{ background-color: #00ffff; color: #000000; }}
                QPushButton#btnStop {{ background-color: #000000; border-color: #ff0055; color: #ff0055; }}
                QPushButton#btnStop:hover {{ background-color: #ff0055; color: #ffffff; }}
                QPushButton#btnEmergencyTab {{ background-color: #ff0000; color: #ffffff; border: 3px solid #ffff00; }}
                QPushButton#btnEmergencyTab:hover {{ background-color: #ffff00; color: #000000; }}
                QPushButton#btnTabActive {{ background-color: #00ffff; color: #000000; border: 2px solid #ffffff; }}
                QPushButton#btnTabInactive {{ background-color: #000000; color: #ffff00; border: 2px solid #ffff00; }}
            """

        if active_theme_key == "light":
            return f"""
                QMainWindow {{ background-color: {t['bg_main']}; }}
                QLabel#title {{ color: {t['accent']}; font-size: 22px; font-weight: bold; }}
                QLabel#subtitle {{ color: {t['text_secondary']}; font-size: 13px; }}
                QLabel#preview {{
                    background-color: {t['bg_surface']};
                    border: 2px solid {t['border']};
                    border-radius: 8px;
                    color: {t['text_secondary']};
                    font-size: 14px;
                }}
                QPushButton {{
                    font-size: 13px;
                    font-weight: 600;
                    padding: 8px 16px;
                    border-radius: 6px;
                    border: none;
                }}
                QPushButton#btnStart {{ background-color: #0284c7; color: #ffffff; }}
                QPushButton#btnStart:hover {{ background-color: #0369a1; }}
                QPushButton#btnStart:disabled {{ background-color: #cbd5e1; color: #94a3b8; }}
                QPushButton#btnStop {{ background-color: #ef4444; color: #ffffff; }}
                QPushButton#btnStop:hover {{ background-color: #dc2626; }}
                QPushButton#btnStop:disabled {{ background-color: #cbd5e1; color: #94a3b8; }}
                QPushButton#btnCalibrate {{ background-color: #6366f1; color: #ffffff; }}
                QPushButton#btnCalibrate:hover {{ background-color: #4f46e5; }}
                QPushButton#btnCalibrate:disabled {{ background-color: #cbd5e1; color: #94a3b8; }}
                QPushButton#btnToggle {{ background-color: #e2e8f0; color: #1e293b; font-size: 12px; }}
                QPushButton#btnToggle:hover {{ background-color: #cbd5e1; }}
                QPushButton#btnTabActive {{ background-color: #0284c7; color: #ffffff; }}
                QPushButton#btnTabInactive {{ background-color: #e2e8f0; color: #475569; border: 1px solid #cbd5e1; }}
                QPushButton#btnEmergencyTab {{ background-color: #dc2626; color: #ffffff; font-weight: bold; }}
                QPushButton#btnEmergencyTab:hover {{ background-color: #ef4444; }}
            """

        # Default Dark Theme
        return f"""
            QMainWindow {{ background-color: {t['bg_main']}; }}
            QLabel#title {{ color: {t['accent']}; font-size: 22px; font-weight: bold; }}
            QLabel#subtitle {{ color: {t['text_secondary']}; font-size: 13px; }}
            QLabel#preview {{
                background-color: {t['bg_surface']};
                border: 2px solid {t['border']};
                border-radius: 8px;
                color: {t['text_secondary']};
                font-size: 14px;
            }}
            QPushButton {{
                font-size: 13px;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
            }}
            QPushButton#btnStart {{ background-color: #0284c7; color: #ffffff; }}
            QPushButton#btnStart:hover {{ background-color: #0369a1; }}
            QPushButton#btnStart:disabled {{ background-color: #334155; color: #64748b; }}
            QPushButton#btnStop {{ background-color: #ef4444; color: #ffffff; }}
            QPushButton#btnStop:hover {{ background-color: #dc2626; }}
            QPushButton#btnStop:disabled {{ background-color: #334155; color: #64748b; }}
            QPushButton#btnCalibrate {{ background-color: #6366f1; color: #ffffff; }}
            QPushButton#btnCalibrate:hover {{ background-color: #4f46e5; }}
            QPushButton#btnCalibrate:disabled {{ background-color: #334155; color: #64748b; }}
            QPushButton#btnToggle {{ background-color: #334155; color: #e2e8f0; font-size: 12px; }}
            QPushButton#btnToggle:hover {{ background-color: #475569; }}
            QPushButton#btnTabActive {{ background-color: #0284c7; color: #ffffff; }}
            QPushButton#btnTabInactive {{ background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; }}
            QPushButton#btnEmergencyTab {{ background-color: #dc2626; color: #ffffff; font-weight: bold; }}
            QPushButton#btnEmergencyTab:hover {{ background-color: #ef4444; }}
        """
