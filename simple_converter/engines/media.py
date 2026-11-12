import json
from pathlib import Path

from .. import tools
from ..util import ConvertError, out_path, parse_time, run

VIDEO_FMTS = {"mp4", "mkv", "mov", "avi", "webm"}
AUDIO_FMTS = {"mp3", "wav", "flac", "ogg", "m4a", "aac", "opus"}


def probe(src: Path) -> dict:
    ffprobe = tools.get("ffprobe")
    if not ffprobe:
        return {}
    try:
        out = run([ffprobe, "-v", "error", "-print_format", "json", "-show_streams",
                   "-show_format", src], timeout=60)
        return json.loads(out)
    except (ConvertError, ValueError):
        return {}


def _codecs(info):
    v = a = None
    for s in info.get("streams", []):
        if s.get("codec_type") == "video" and not v and s.get("disposition", {}).get("attached_pic") != 1:
            v = s.get("codec_name")
        if s.get("codec_type") == "audio" and not a:
            a = s.get("codec_name")
    return v, a


def duration(src: Path) -> float:
    try:
        return float(probe(src).get("format", {}).get("duration") or 0)
    except ValueError:
        return 0.0


def _ff(src: Path, dst: Path, out_args: list, opts: dict, in_args=()):
    ff = tools.need("ffmpeg")
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", *in_args]
    start, end = parse_time(opts.get("start")), parse_time(opts.get("end"))
    if start:
        cmd += ["-ss", start]
    if end:
        cmd += ["-to", end]
    cmd += ["-i", src, *out_args, dst]
    try:
        run(cmd)
    except ConvertError:
        if dst.exists():
            dst.unlink()
        raise
    if not dst.exists() or dst.stat().st_size == 0:
        raise ConvertError("FFmpeg produced no output")
    return [dst]


def _vfilters(opts, extra=None):
    vf = []
    h = opts.get("height")
    if h:
        vf.append(f"scale=-2:'min({int(h)},ih)'")
    if opts.get("fps"):
        vf.append(f"fps={float(opts['fps']):g}")
    if extra:
        vf.extend(extra)
    return ["-vf", ",".join(vf)] if vf else []


def _audio_args(to, opts):
    br = opts.get("audio_bitrate")
    a = []
    if to == "mp3":
        a = ["-c:a", "libmp3lame"] + (["-b:a", f"{br}k"] if br else ["-q:a", "2"])
    elif to == "wav":
        a = ["-c:a", "pcm_s16le"]
    elif to == "flac":
        a = ["-c:a", "flac"]
    elif to == "ogg":
        a = ["-c:a", "libvorbis"] + (["-b:a", f"{br}k"] if br else ["-q:a", "5"])
    elif to in ("m4a", "aac"):
        a = ["-c:a", "aac", "-b:a", f"{br or 192}k"]
    elif to == "opus":
        a = ["-c:a", "libopus", "-b:a", f"{br or 128}k"]
    if opts.get("sample_rate"):
        a += ["-ar", str(int(opts["sample_rate"]))]
    if opts.get("channels"):
        a += ["-ac", str(int(opts["channels"]))]
    af = []
    if opts.get("normalize"):
        af.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    if opts.get("volume") and float(opts["volume"]) != 100:
        af.append(f"volume={float(opts['volume']) / 100:g}")
    if af:
        a += ["-af", ",".join(af)]
    return a


def _video_args(to, opts, vcodec, acodec):
    crf = opts.get("crf")
    mute = opts.get("mute")
    reencode = any(opts.get(k) for k in ("height", "fps", "crf")) or opts.get("force_reencode")
    # Fast path: only the container changes -> copy streams, no quality loss.
    if (not reencode and to in ("mp4", "mkv", "mov") and vcodec in ("h264", "hevc")
            and acodec in (None, "aac", "mp3") and not opts.get("start") and not opts.get("end")):
        return ["-map", "0:v:0", "-map", "0:a?", "-c", "copy"] + (["-an"] if mute else []) + \
            (["-movflags", "+faststart"] if to in ("mp4", "mov") else []) + \
            (["-tag:v", "hvc1"] if vcodec == "hevc" and to in ("mp4", "mov") else [])
    vf = _vfilters(opts)
    if to in ("mp4", "mkv", "mov"):
        v = ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf or 23), "-pix_fmt", "yuv420p"]
        a = ["-c:a", "aac", "-b:a", f"{opts.get('audio_bitrate') or 160}k"]
        extra = ["-movflags", "+faststart"] if to != "mkv" else []
    elif to == "webm":
        v = ["-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p", "-crf", str(int(crf or 23) + 9), "-b:v", "0", "-row-mt", "1",
             "-deadline", "good", "-cpu-used", "4"]
        a = ["-c:a", "libopus", "-b:a", f"{opts.get('audio_bitrate') or 128}k"]
        extra = []
    elif to == "avi":
        v = ["-c:v", "mpeg4", "-q:v", "3", "-vtag", "xvid"]
        a = ["-c:a", "libmp3lame", "-b:a", f"{opts.get('audio_bitrate') or 192}k"]
        extra = []
    else:
        raise ConvertError(f"Unknown video format {to}")
    if vf:
        # make sure dimensions stay even for yuv420p
        vf[1] += ",scale=trunc(iw/2)*2:trunc(ih/2)*2"
    else:
        vf = ["-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2"]
    return ["-map", "0:v:0", "-map", "0:a?", *v, *vf, *(["-an"] if mute else a), *extra]


def to_video(src: Path, to: str, outdir=None, opts=None, suffix="") -> list[Path]:
    opts = opts or {}
    v, a = _codecs(probe(src))
    if src.suffix.lower() == ".gif":
        v, a = "gif", None
    dst = out_path(src, outdir, to, suffix)
    try:
        return _ff(src, dst, _video_args(to, opts, v, a), opts)
    except ConvertError:
        if "-c" in _video_args(to, opts, v, a):  # copy failed -> re-encode
            return _ff(src, dst, _video_args(to, {**opts, "force_reencode": True}, v, a), opts)
        raise


def to_gif(src: Path, outdir=None, opts=None) -> list[Path]:
    opts = opts or {}
    fps = opts.get("fps") or 12
    width = opts.get("gif_width") or 480
    dst = out_path(src, outdir, "gif")
    vf = (f"fps={fps},scale='min({int(width)},iw)':-1:flags=lanczos,split[s0][s1];"
          f"[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5")
    return _ff(src, dst, ["-vf", vf, "-loop", "0"], opts)


def to_audio(src: Path, to: str, outdir=None, opts=None, suffix="") -> list[Path]:
    opts = opts or {}
    dst = out_path(src, outdir, to, suffix)
    return _ff(src, dst, ["-vn", "-map", "0:a:0", *_audio_args(to, opts)], opts)


def compress_video(src: Path, outdir=None, opts=None) -> list[Path]:
    o = {"height": 720, "crf": 28, "audio_bitrate": 128, **(opts or {})}
    return to_video(src, "mp4", outdir, o, " (compressed)")


def mute(src: Path, outdir=None) -> list[Path]:
    ext = src.suffix.lower().lstrip(".")
    dst = out_path(src, outdir, ext, " (no audio)")
    try:
        return _ff(src, dst, ["-map", "0:v", "-c", "copy", "-an"], {})
    except ConvertError:
        return _ff(src, dst, ["-an"], {})


def frame(src: Path, outdir=None, opts=None) -> list[Path]:
    opts = opts or {}
    at = parse_time(opts.get("start"))
    if not at:
        d = duration(src)
        at = f"{d * 0.1:.2f}" if d else "0"
    dst = out_path(src, outdir, "png", " (frame)")
    return _ff(src, dst, ["-frames:v", "1", "-update", "1"], {}, in_args=["-ss", at])


def compress_audio(src: Path, outdir=None) -> list[Path]:
    return to_audio(src, "mp3", outdir, {"audio_bitrate": 128}, " (compressed)")


def normalize(src: Path, outdir=None) -> list[Path]:
    ext = src.suffix.lower().lstrip(".")
    if ext not in AUDIO_FMTS:
        ext = "mp3"
    return to_audio(src, ext, outdir, {"normalize": True}, " (normalized)")


def subtitle(src: Path, to: str, outdir=None) -> list[Path]:
    dst = out_path(src, outdir, to)
    return _ff(src, dst, [], {})


def same_format_media(src: Path, opts: dict, outdir=None) -> list[Path]:
    """Advanced dialog with the source's own format: trim / resize / re-encode."""
    ext = src.suffix.lower().lstrip(".")
    if ext in AUDIO_FMTS:
        return to_audio(src, ext, outdir, opts, " (edited)")
    to = ext if ext in VIDEO_FMTS else "mp4"
    return to_video(src, to, outdir, {**opts, "force_reencode": True}, " (edited)")
