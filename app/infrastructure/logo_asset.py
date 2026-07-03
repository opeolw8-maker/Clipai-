"""
Provides the path to the watermark logo image, if one exists.

Simplified for manual deployment: returns a path that doesn't exist,
which video_editor_service.py already handles gracefully (it skips
the watermark step entirely and ships the clip without one). To add
a real watermark later, drop a PNG file somewhere in your deployment
and point `path()` at it.
"""


class LogoAsset:
    def path(self) -> str:
        return "/tmp/clipai_logo_not_configured.png"
