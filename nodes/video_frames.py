"""
Video frame extraction nodes.

PyAV backend with optional NVDEC (CUDA) hardware decode, ported from Ruby's
standalone extract_frames script:

  - Video Frame Extract     decode a video into an IMAGE batch, optionally
                            writing the frames to disk on the way through.
  - Video Frames To Disk    bulk-extract one file or a whole folder straight
                            to disk with a threaded writer pool.
  - Video Endpoint Frames   grab the first and last frame of a video.

Needs PyAV: pip install av
"""
import secrets
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from threading import Thread

import numpy as np
from PIL import Image

from .utils import safe_filename

try:
    import folder_paths as comfy_paths
    _HAS_COMFY_PATHS = True
except Exception:
    comfy_paths = None
    _HAS_COMFY_PATHS = False

try:
    from comfy.utils import ProgressBar
except Exception:
    ProgressBar = None

try:
    from comfy import model_management
except Exception:
    model_management = None


DEFAULT_EXTENSIONS = ".mp4,.webm,.gif,.avi,.mkv,.mov"
IMAGE_FORMATS = ["png", "jpg", "webp"]
HWACCEL_CODECS = ("h264", "hevc")


def _require_av():
    """Import PyAV lazily so a missing dep doesn't break the whole node pack."""
    try:
        import av
    except ImportError as exc:
        raise RuntimeError(
            "PyAV is not installed. Install it into ComfyUI's python: pip install av"
        ) from exc
    return av


def _hwaccel_class():
    try:
        from av.codec.hwaccel import HWAccel
        return HWAccel
    except ImportError:
        return None


def _open_with_hwaccel(av, video_path):
    """Try a CUDA-accelerated open, fall back to CPU. Returns (container, status)."""
    hwaccel_cls = _hwaccel_class()
    if hwaccel_cls is not None:
        try:
            hwaccel = hwaccel_cls(device_type="cuda", allow_software_fallback=False)
            container = av.open(video_path, hwaccel=hwaccel)
            stream = container.streams.video[0]
            next(container.decode(stream))  # fail fast if CUDA is unusable
            container.seek(0)
            return container, "NVDEC"
        except Exception:
            pass
    return av.open(video_path), "CPU"


def _resolve_source(path_text):
    """Absolute paths win; relative ones are tried against Comfy's input dir first."""
    text = str(path_text or "").strip().strip('"').strip("'")
    if not text:
        raise ValueError("No path given.")
    src = Path(text).expanduser()
    if src.is_absolute():
        return src
    if _HAS_COMFY_PATHS:
        candidate = Path(comfy_paths.get_input_directory()) / src
        if candidate.exists():
            return candidate.resolve()
    return (Path.cwd() / src).resolve()


def _resolve_output_base(dir_text, fallback="extracted_frames"):
    """Relative output dirs land under Comfy's output folder."""
    text = str(dir_text or "").strip().strip('"').strip("'") or fallback
    out = Path(text).expanduser()
    if out.is_absolute():
        return out
    base = Path(comfy_paths.get_output_directory()) if _HAS_COMFY_PATHS else Path.cwd()
    return base / out


def _save_kwargs(image_format, quality):
    if image_format == "jpg":
        return {"quality": int(quality), "subsampling": 0}
    if image_format == "webp":
        return {"quality": int(quality), "method": 4}
    return {"optimize": False}


def _file_stamp(path_text):
    """Cache key that changes when the source file changes on disk."""
    try:
        stat = _resolve_source(path_text).stat()
        return f"{stat.st_mtime_ns}:{stat.st_size}"
    except Exception:
        return str(path_text)


@dataclass
class FrameTask:
    frame_rgb: np.ndarray
    output_path: Path
    save_kwargs: dict = field(default_factory=dict)


def _frame_writer_worker(task_queue, done_sentinel):
    """Worker thread for async disk writes."""
    while True:
        task = task_queue.get()
        if task is done_sentinel:
            task_queue.task_done()
            break
        try:
            Image.fromarray(task.frame_rgb).save(task.output_path, **task.save_kwargs)
        except Exception as exc:
            print(f"  [RubyTools] write failed for {task.output_path.name}: {exc}")
        task_queue.task_done()


def probe_video(video_path):
    """Read stream metadata without decoding the whole file."""
    av = _require_av()
    container = av.open(str(video_path))
    try:
        stream = container.streams.video[0]
        fps = float(stream.average_rate) if stream.average_rate else 0.0
        total_frames = stream.frames or 0
        if total_frames == 0:
            duration = float(container.duration) / av.time_base if container.duration else 0.0
            total_frames = int(duration * fps) if fps > 0 else 0
        return {
            "frames": total_frames,
            "fps": fps,
            "codec": stream.codec_context.name,
            "width": stream.codec_context.width,
            "height": stream.codec_context.height,
        }
    finally:
        container.close()


def _stack_images(frames):
    """uint8 HWC frames -> ComfyUI IMAGE tensor (B, H, W, C) float32 0-1."""
    import torch
    if not frames:
        raise RuntimeError(
            "No frames were extracted. Check start_frame/step against the video length."
        )
    shapes = {f.shape for f in frames}
    if len(shapes) > 1:
        raise RuntimeError(
            f"Video has variable frame sizes {sorted(shapes)}; cannot build one IMAGE batch. "
            "Extract to disk instead, or load a resized copy."
        )
    batch = np.stack(frames)
    return torch.from_numpy(batch).float().div_(255.0)


def extract_frames(
    video_path,
    step=1,
    start_frame=0,
    max_frames=0,
    use_hwaccel=True,
    collect_images=False,
    output_dir=None,
    prefix="",
    image_format="png",
    quality=95,
    skip_existing=True,
    writer_threads=8,
    verbose=True,
):
    """
    Decode a video, keeping every Nth frame.

    Returns (frames, extracted, info) where `frames` is a list of uint8 RGB
    arrays when collect_images is set, otherwise None.
    """
    av = _require_av()
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Source not found: {video_path}")

    step = max(1, int(step))
    start_frame = max(0, int(start_frame))
    max_frames = max(0, int(max_frames))
    writer_threads = max(1, int(writer_threads))

    info = probe_video(video_path)
    total_frames = info["frames"]
    fps = info["fps"]
    codec_name = info["codec"]

    if use_hwaccel and codec_name in HWACCEL_CODECS:
        container, hwaccel_status = _open_with_hwaccel(av, str(video_path))
    else:
        container = av.open(str(video_path))
        hwaccel_status = "CPU"

    stream = container.streams.video[0]
    stream.thread_type = "AUTO"

    if total_frames:
        remaining = max(0, total_frames - start_frame)
        expected = (remaining + step - 1) // step
        if max_frames:
            expected = min(expected, max_frames)
    else:
        expected = max_frames  # unknown length; 0 means "no idea"
    pad_width = max(4, len(str(total_frames or 0)))
    ext = image_format if image_format in IMAGE_FORMATS else "png"
    save_kwargs = _save_kwargs(ext, quality)

    if verbose:
        print(f"[{video_path.name}] ~{total_frames} frames @ {fps:.2f}fps")
        print(f"  Codec: {codec_name} | HW: {hwaccel_status} | Step: {step} "
              f"(~{expected or '?'} output frames)")

    writers = []
    writer_queue = None
    done_sentinel = object()
    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        writer_queue = Queue(maxsize=writer_threads * 4)
        for _ in range(writer_threads):
            thread = Thread(target=_frame_writer_worker, args=(writer_queue, done_sentinel))
            thread.daemon = True
            thread.start()
            writers.append(thread)

    pbar = ProgressBar(expected) if (ProgressBar is not None and expected) else None
    frames = [] if collect_images else None
    frame_idx = 0
    extracted = 0
    skipped = 0

    try:
        for frame in container.decode(video=0):
            if model_management is not None:
                model_management.throw_exception_if_processing_interrupted()

            if frame_idx < start_frame or (frame_idx - start_frame) % step != 0:
                frame_idx += 1
                continue

            out_path = None
            if output_dir is not None:
                out_path = output_dir / f"{prefix}{frame_idx:0{pad_width}d}.{ext}"
                if skip_existing and out_path.exists():
                    if not collect_images:
                        skipped += 1
                        frame_idx += 1
                        continue
                    out_path = None

            frame_rgb = frame.to_ndarray(format="rgb24")

            if collect_images:
                frames.append(frame_rgb)
            if out_path is not None:
                writer_queue.put(FrameTask(frame_rgb, out_path, save_kwargs))

            extracted += 1
            frame_idx += 1
            if pbar is not None:
                pbar.update(1)

            if verbose and extracted % 100 == 0:
                print(f"  ... extracted {extracted} (frame {frame_idx}/{total_frames or '?'})")

            if max_frames and extracted >= max_frames:
                break
    finally:
        container.close()
        if writer_queue is not None:
            for _ in writers:
                writer_queue.put(done_sentinel)
            writer_queue.join()

    if verbose:
        note = f" ({skipped} already on disk)" if skipped else ""
        print(f"  [ok] {extracted} frames{note}")

    info["extracted"] = extracted
    info["skipped"] = skipped
    info["hwaccel"] = hwaccel_status
    return frames, extracted, info


def extract_endpoints(video_path):
    """Decode the first and last frame. Returns (first_rgb, last_rgb, info)."""
    av = _require_av()
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Source not found: {video_path}")

    info = probe_video(video_path)
    container = av.open(str(video_path))
    try:
        first = next(container.decode(video=0), None)
        first_rgb = first.to_ndarray(format="rgb24") if first is not None else None

        # Seek to the last keyframe, decode forward, keep the final frame
        if container.duration:
            container.seek(container.duration - 1, backward=True)
        last = None
        for frame in container.decode(video=0):
            last = frame
        if last is None:
            # Seek overshot (short or odd files) - full decode fallback
            container.seek(0)
            for frame in container.decode(video=0):
                last = frame
        last_rgb = last.to_ndarray(format="rgb24") if last is not None else None
    finally:
        container.close()

    if first_rgb is None:
        raise RuntimeError(f"No decodable video frames in {video_path.name}")
    if last_rgb is None:
        last_rgb = first_rgb
    return first_rgb, last_rgb, info


def _make_output_dir(base, video_path, randomize):
    """Script behaviour: a random hex subfolder that also prefixes the filenames."""
    if randomize:
        prefix = secrets.token_hex(4)
    else:
        prefix = safe_filename(video_path.stem)
    return Path(base) / prefix, prefix


def _list_videos(source_dir, extensions_text):
    exts = tuple(
        e.strip().lower() if e.strip().startswith(".") else "." + e.strip().lower()
        for e in str(extensions_text or DEFAULT_EXTENSIONS).split(",")
        if e.strip()
    )
    return sorted(f for f in Path(source_dir).iterdir() if f.suffix.lower() in exts)


class VideoFrameExtract:
    """Decode a video file into an IMAGE batch, with optional NVDEC and disk output."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_path": ("STRING", {
                    "default": "",
                    "tooltip": "Video file. Absolute path, or relative to ComfyUI's input folder",
                }),
                "step": ("INT", {
                    "default": 1, "min": 1, "max": 100000,
                    "tooltip": "Keep every Nth frame (30 = ~1/sec on 30fps footage)",
                }),
                "start_frame": ("INT", {
                    "default": 0, "min": 0, "max": 0xFFFFFFF,
                    "tooltip": "Frame index to start from; earlier frames are decoded and dropped",
                }),
                "max_frames": ("INT", {
                    "default": 64, "min": 0, "max": 0xFFFFFFF,
                    "tooltip": "Cap on returned frames; 0 = no cap (the whole batch lives in RAM)",
                }),
            },
            "optional": {
                "use_hwaccel": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Try NVDEC for h264/hevc, fall back to CPU decode",
                }),
                "save_to_disk": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Also write each frame out as an image file",
                }),
                "output_dir": ("STRING", {
                    "default": "extracted_frames",
                    "tooltip": "Save folder; relative paths land under ComfyUI's output folder",
                }),
                "randomize_subfolder": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "On: random hex subfolder + filename prefix. Off: use the video's name",
                }),
                "image_format": (IMAGE_FORMATS, {"default": "png", "tooltip": "Saved image format"}),
                "quality": ("INT", {
                    "default": 95, "min": 1, "max": 100,
                    "tooltip": "Quality for jpg/webp; ignored for png",
                }),
                "skip_existing": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Don't rewrite frames that are already on disk",
                }),
                "writer_threads": ("INT", {
                    "default": 8, "min": 1, "max": 64,
                    "tooltip": "Background threads used for disk writes",
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "INT", "FLOAT", "STRING")
    RETURN_NAMES = ("images", "frame_count", "fps", "output_dir")
    FUNCTION = "extract"
    CATEGORY = "Ruby's Nodes/Video"

    @classmethod
    def IS_CHANGED(cls, video_path="", **kwargs):
        return _file_stamp(video_path)

    def extract(self, video_path, step=1, start_frame=0, max_frames=64,
                use_hwaccel=True, save_to_disk=False, output_dir="extracted_frames",
                randomize_subfolder=True, image_format="png", quality=95,
                skip_existing=True, writer_threads=8):
        source = _resolve_source(video_path)

        target_dir = None
        prefix = ""
        if save_to_disk:
            base = _resolve_output_base(output_dir)
            target_dir, prefix = _make_output_dir(base, source, randomize_subfolder)

        frames, extracted, info = extract_frames(
            source,
            step=step,
            start_frame=start_frame,
            max_frames=max_frames,
            use_hwaccel=use_hwaccel,
            collect_images=True,
            output_dir=target_dir,
            prefix=prefix,
            image_format=image_format,
            quality=quality,
            skip_existing=skip_existing,
            writer_threads=writer_threads,
        )

        images = _stack_images(frames)
        return (images, extracted, float(info["fps"]), str(target_dir) if target_dir else "")


class VideoFramesToDisk:
    """Bulk-extract frames from a file or a whole folder of videos straight to disk."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_path": ("STRING", {
                    "default": "",
                    "tooltip": "Video file or folder of videos; relative paths use ComfyUI's input folder",
                }),
                "output_dir": ("STRING", {
                    "default": "extracted_frames",
                    "tooltip": "Save folder; relative paths land under ComfyUI's output folder",
                }),
                "step": ("INT", {
                    "default": 1, "min": 1, "max": 100000,
                    "tooltip": "Keep every Nth frame (30 = ~1/sec on 30fps footage)",
                }),
            },
            "optional": {
                "extensions": ("STRING", {
                    "default": DEFAULT_EXTENSIONS,
                    "tooltip": "Comma separated extensions used when source_path is a folder",
                }),
                "start_frame": ("INT", {
                    "default": 0, "min": 0, "max": 0xFFFFFFF,
                    "tooltip": "Frame index to start from in each video",
                }),
                "max_frames_per_video": ("INT", {
                    "default": 0, "min": 0, "max": 0xFFFFFFF,
                    "tooltip": "Cap per video; 0 = extract everything",
                }),
                "use_hwaccel": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Try NVDEC for h264/hevc, fall back to CPU decode",
                }),
                "randomize_subfolder": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "On: random hex subfolder + filename prefix. Off: use the video's name",
                }),
                "image_format": (IMAGE_FORMATS, {"default": "png", "tooltip": "Saved image format"}),
                "quality": ("INT", {
                    "default": 95, "min": 1, "max": 100,
                    "tooltip": "Quality for jpg/webp; ignored for png",
                }),
                "skip_existing": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Don't rewrite frames that are already on disk",
                }),
                "writer_threads": ("INT", {
                    "default": 8, "min": 1, "max": 64,
                    "tooltip": "Background threads used for disk writes",
                }),
                "parallel_videos": ("INT", {
                    "default": 1, "min": 1, "max": 16,
                    "tooltip": "How many videos to decode at once when source_path is a folder",
                }),
            },
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("summary", "total_frames", "output_dir")
    FUNCTION = "extract"
    OUTPUT_NODE = True
    CATEGORY = "Ruby's Nodes/Video"

    @classmethod
    def IS_CHANGED(cls, source_path="", **kwargs):
        return _file_stamp(source_path)

    def extract(self, source_path, output_dir="extracted_frames", step=1,
                extensions=DEFAULT_EXTENSIONS, start_frame=0, max_frames_per_video=0,
                use_hwaccel=True, randomize_subfolder=True, image_format="png",
                quality=95, skip_existing=True, writer_threads=8, parallel_videos=1):
        source = _resolve_source(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source}")

        base = _resolve_output_base(output_dir)
        videos = _list_videos(source, extensions) if source.is_dir() else [source]
        if not videos:
            return (f"No matching videos in {source}", 0, str(base))

        print(f"[RubyTools] extracting from {len(videos)} file(s), step {step}")

        def process_one(video):
            target_dir, prefix = _make_output_dir(base, video, randomize_subfolder)
            _, count, _info = extract_frames(
                video,
                step=step,
                start_frame=start_frame,
                max_frames=max_frames_per_video,
                use_hwaccel=use_hwaccel,
                collect_images=False,
                output_dir=target_dir,
                prefix=prefix,
                image_format=image_format,
                quality=quality,
                skip_existing=skip_existing,
                writer_threads=writer_threads,
            )
            return video.name, count

        results = {}
        if parallel_videos > 1 and len(videos) > 1:
            with ThreadPoolExecutor(max_workers=int(parallel_videos)) as pool:
                futures = [(v, pool.submit(process_one, v)) for v in videos]
                for video, future in futures:
                    try:
                        name, count = future.result()
                        results[name] = count
                    except Exception as exc:
                        print(f"  [fail] {video.name}: {exc}")
                        results[video.name] = -1
        else:
            for video in videos:
                try:
                    name, count = process_one(video)
                    results[name] = count
                except Exception as exc:
                    print(f"  [fail] {video.name}: {exc}")
                    results[video.name] = -1

        succeeded = sum(1 for v in results.values() if v >= 0)
        total = sum(v for v in results.values() if v >= 0)
        lines = [f"{name}: {count if count >= 0 else 'failed'}" for name, count in results.items()]
        summary = f"{succeeded}/{len(results)} videos, {total} frames\n" + "\n".join(lines)
        print(f"[RubyTools] {succeeded}/{len(results)} videos, {total} frames -> {base}")
        return (summary, total, str(base))


class VideoEndpointFrames:
    """Grab the first and last frame of a video."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_path": ("STRING", {
                    "default": "",
                    "tooltip": "Video file. Absolute path, or relative to ComfyUI's input folder",
                }),
            },
            "optional": {
                "save_to_disk": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Write the endpoint frame(s) out as image files",
                }),
                "save_which": (["both", "first", "last"], {
                    "default": "both",
                    "tooltip": "Which endpoint(s) to write when saving; both are always output",
                }),
                "output_dir": ("STRING", {
                    "default": "endpoint_frames",
                    "tooltip": "Save folder; relative paths land under ComfyUI's output folder",
                }),
                "image_format": (IMAGE_FORMATS, {"default": "png", "tooltip": "Saved image format"}),
                "quality": ("INT", {
                    "default": 95, "min": 1, "max": 100,
                    "tooltip": "Quality for jpg/webp; ignored for png",
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "FLOAT", "INT", "STRING")
    RETURN_NAMES = ("first_frame", "last_frame", "fps", "frame_count", "output_dir")
    FUNCTION = "grab"
    CATEGORY = "Ruby's Nodes/Video"

    @classmethod
    def IS_CHANGED(cls, video_path="", **kwargs):
        return _file_stamp(video_path)

    def grab(self, video_path, save_to_disk=False, save_which="both",
             output_dir="endpoint_frames", image_format="png", quality=95):
        source = _resolve_source(video_path)
        first_rgb, last_rgb, info = extract_endpoints(source)

        saved_dir = ""
        if save_to_disk:
            target = _resolve_output_base(output_dir, fallback="endpoint_frames")
            target.mkdir(parents=True, exist_ok=True)
            ext = image_format if image_format in IMAGE_FORMATS else "png"
            kwargs = _save_kwargs(ext, quality)
            stem = safe_filename(source.stem)
            if save_which in ("first", "both"):
                Image.fromarray(first_rgb).save(target / f"{stem}_first.{ext}", **kwargs)
            if save_which in ("last", "both"):
                Image.fromarray(last_rgb).save(target / f"{stem}_last.{ext}", **kwargs)
            saved_dir = str(target)
            print(f"[{source.name}] wrote endpoint frame(s) -> {target}")

        first = _stack_images([first_rgb])
        last = _stack_images([last_rgb])
        return (first, last, float(info["fps"]), int(info["frames"]), saved_dir)


NODE_CLASS_MAPPINGS = {
    "RubyVideoFrameExtract": VideoFrameExtract,
    "RubyVideoFramesToDisk": VideoFramesToDisk,
    "RubyVideoEndpointFrames": VideoEndpointFrames,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyVideoFrameExtract": "Video Frame Extract",
    "RubyVideoFramesToDisk": "Video Frames To Disk",
    "RubyVideoEndpointFrames": "Video Endpoint Frames",
}
