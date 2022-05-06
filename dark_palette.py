# dark palette

from PyQt6.QtGui import QPalette, QColor

_palette_dark = QPalette()

_palette_dark.setColor(QPalette.ColorRole.Window, QColor(25, 25, 25))
_palette_dark.setColor(QPalette.ColorRole.WindowText, QColor(255,255,255))
_palette_dark.setColor(QPalette.ColorRole.Base, QColor(5, 5, 5))
_palette_dark.setColor(QPalette.ColorRole.AlternateBase, QColor(50, 50, 50))
_palette_dark.setColor(QPalette.ColorRole.ToolTipBase, QColor(0,0,0))
_palette_dark.setColor(QPalette.ColorRole.ToolTipText, QColor(255,255,255))
_palette_dark.setColor(QPalette.ColorRole.Text, QColor(255,255,255))
_palette_dark.setColor(QPalette.ColorRole.Button, QColor(20, 20, 20))
_palette_dark.setColor(QPalette.ColorRole.ButtonText, QColor(255,255,255))
_palette_dark.setColor(QPalette.ColorRole.BrightText, QColor(255,250,250))
_palette_dark.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
_palette_dark.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
_palette_dark.setColor(QPalette.ColorRole.HighlightedText, QColor(255,255,255))
if hasattr(QPalette.ColorRole, "Foreground"):
    _palette_dark.setColor(QPalette.ColorRole.Foreground,  QColor(25, 25, 25))
if hasattr(QPalette.ColorRole, "PlaceholderText"):
    _palette_dark.setColor(QPalette.ColorRole.PlaceholderText, QColor(180,180,180))

_palette_dark.setColor(QPalette.ColorRole.Light, QColor(25, 25, 25))
_palette_dark.setColor(QPalette.ColorRole.Midlight, QColor("#3f4042"))
_palette_dark.setColor(QPalette.ColorRole.Dark, QColor("#e4e7eb"))
_palette_dark.setColor(QPalette.ColorRole.Mid, QColor("#3f4042"))
_palette_dark.setColor(QPalette.ColorRole.Shadow, QColor("#3f4042"))

_palette_dark.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#697177"))
_palette_dark.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#697177"))
_palette_dark.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#3f4042"))
_palette_dark.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor("#53575b"))
_palette_dark.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor("#697177"))
_palette_dark.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Link, QColor("#697177"))
_palette_dark.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.LinkVisited, QColor("#697177"))

_palette_dark.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight, QColor("#393d41"))

PALETTE_DARK = _palette_dark