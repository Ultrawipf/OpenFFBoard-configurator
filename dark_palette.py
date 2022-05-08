# dark palette
# related document: https://www.riverbankcomputing.com/static/Docs/PyQt6/api/qtgui/qpalette.html

from PyQt6.QtGui import QPalette, QColor

_palette_dark = QPalette()

whiteColor = QColor("#fefefe")  # 255 will become black due to bug in PyQt6>=6.2.3

subtleBlueColor = QColor(
    "#8ab4f7"
)  # add little blue highlight, make button clear it's clickable

_palette_dark.setColor(QPalette.ColorRole.Window, QColor(25, 25, 25))
_palette_dark.setColor(QPalette.ColorRole.WindowText, whiteColor)
_palette_dark.setColor(QPalette.ColorRole.Base, QColor(5, 5, 5))
_palette_dark.setColor(QPalette.ColorRole.AlternateBase, QColor(10, 10, 10))
_palette_dark.setColor(QPalette.ColorRole.ToolTipBase, QColor(0, 0, 0))
_palette_dark.setColor(QPalette.ColorRole.ToolTipText, whiteColor)
_palette_dark.setColor(QPalette.ColorRole.Text, whiteColor)
_palette_dark.setColor(QPalette.ColorRole.Button, QColor(20, 20, 20))
_palette_dark.setColor(QPalette.ColorRole.ButtonText, subtleBlueColor)
_palette_dark.setColor(QPalette.ColorRole.BrightText, whiteColor)
_palette_dark.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
_palette_dark.setColor(QPalette.ColorRole.Highlight, subtleBlueColor)
_palette_dark.setColor(QPalette.ColorRole.HighlightedText, whiteColor)
if hasattr(QPalette.ColorRole, "Foreground"):
    _palette_dark.setColor(QPalette.ColorRole.Foreground, QColor(25, 25, 25))
if hasattr(QPalette.ColorRole, "PlaceholderText"):
    _palette_dark.setColor(QPalette.ColorRole.PlaceholderText, QColor(180, 180, 180))

_palette_dark.setColor(
    QPalette.ColorRole.Light, QColor(25, 25, 25)
)  # lighter than button color
_palette_dark.setColor(
    QPalette.ColorRole.Midlight, QColor(30, 30, 30)
)  # Between Button and Light
_palette_dark.setColor(
    QPalette.ColorRole.Dark, QColor(228, 228, 228)
)  # Darker than Button
_palette_dark.setColor(
    QPalette.ColorRole.Mid, QColor(63, 63, 63)
)  # Between Button and Dark
_palette_dark.setColor(
    QPalette.ColorRole.Shadow, QColor(63, 63, 63)
)  # A very dark color. By default, the shadow color is Qt::black.

_palette_dark.setColor(
    QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#697177")
)
_palette_dark.setColor(
    QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#697177")
)
_palette_dark.setColor(
    QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#3f4042")
)
_palette_dark.setColor(
    QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor("#53575b")
)
_palette_dark.setColor(
    QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor("#697177")
)
_palette_dark.setColor(
    QPalette.ColorGroup.Disabled, QPalette.ColorRole.Link, QColor("#697177")
)
_palette_dark.setColor(
    QPalette.ColorGroup.Disabled, QPalette.ColorRole.LinkVisited, QColor("#697177")
)

_palette_dark.setColor(
    QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight, QColor("#393d41")
)

PALETTE_DARK = _palette_dark
