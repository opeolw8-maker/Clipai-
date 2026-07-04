"""
Translates raw request.form data into a typed ClipRequest.
"""
from werkzeug.datastructures import ImmutableMultiDict

from app.domain.models import ClipRequest


def parse_clip_request(form: ImmutableMultiDict) -> ClipRequest:
    return ClipRequest(
        num_clips=int(form.get("num_clips", 5)),
        clip_length=int(form.get("clip_length", 60)),
        topic=form.get("topic", "general"),
        cp_level=form.get("cp_level", "none"),
        add_captions=form.get("captions", "1") == "1",
        caption_style=form.get("caption_style", "classic"),
        do_reframe=form.get("reframe", "1") == "1",
        do_mirror=form.get("mirror", "0") == "1",
        do_colorgrade=form.get("colorgrade", "0") == "1",
        do_speed=form.get("speed", "0") == "1",
        do_pitch=form.get("pitch", "0") == "1",
        add_music=form.get("music", "0") == "1",
                      )
