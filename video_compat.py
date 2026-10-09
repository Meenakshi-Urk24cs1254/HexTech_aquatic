"""Optional browser-compatible H.264 encoding through PyAV."""
from __future__ import annotations

from pathlib import Path


def transcode_h264_pyav(src: Path, dst: Path, max_height: int | None = None) -> bool:
    """Encode a silent H.264/yuv420p MP4; return False when PyAV or its encoder is unavailable."""
    src, dst = Path(src), Path(dst)
    tmp = dst.with_name(f"{dst.stem}.partial{dst.suffix}")
    try:
        import av

        dst.parent.mkdir(parents=True, exist_ok=True)
        with av.open(str(src)) as inp:
            video_stream = next((stream for stream in inp.streams if stream.type == "video"), None)
            if video_stream is None:
                return False
            width = int(video_stream.codec_context.width)
            height = int(video_stream.codec_context.height)
            scale = min(1.0, max_height / height) if max_height and height else 1.0
            width = max(2, int(width * scale) // 2 * 2)
            height = max(2, int(height * scale) // 2 * 2)
            with av.open(str(tmp), "w", format="mp4", options={"movflags": "+faststart"}) as out:
                output_stream = out.add_stream("libx264", rate=video_stream.average_rate or 30)
                output_stream.width = width
                output_stream.height = height
                output_stream.pix_fmt = "yuv420p"
                output_stream.options = {"preset": "ultrafast", "crf": "26"}
                for frame in inp.decode(video_stream):
                    frame = frame.reformat(width=width, height=height, format="yuv420p")
                    for packet in output_stream.encode(frame):
                        out.mux(packet)
                for packet in output_stream.encode():
                    out.mux(packet)
        if not tmp.is_file() or tmp.stat().st_size == 0:
            return False
        tmp.replace(dst)
        return True
    except Exception:
        return False
    finally:
        tmp.unlink(missing_ok=True)