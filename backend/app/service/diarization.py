import logging
import numpy as np
import torch
import torchaudio

logger = logging.getLogger(__name__)

_silero_model = None
_silero_utils = None
_silero_failed = False


def _get_silero_vad():
    """Lazily loads Silero VAD via torch.hub (tiny ~2MB model). Falls back cleanly if offline."""
    global _silero_model, _silero_utils, _silero_failed
    if _silero_failed:
        return None, None
    if _silero_model is not None:
        return _silero_model, _silero_utils
    try:
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
            trust_repo=True,
        )
        model.eval()
        _silero_model = model
        _silero_utils = utils
        logger.info("Silero VAD loaded successfully")
        return _silero_model, _silero_utils
    except Exception as e:
        _silero_failed = True
        logger.warning(f"Silero VAD unavailable, using adaptive energy VAD fallback: {e}")
        return None, None


def _energy_vad(wav_1d: np.ndarray, sr: int = 16000) -> list[tuple[float, float]]:
    """Fast adaptive RMS energy VAD fallback when Silero hub is unreachable."""
    frame_len = int(0.03 * sr)
    hop_len = int(0.015 * sr)
    if len(wav_1d) < frame_len:
        return [(0.0, len(wav_1d) / float(sr))]

    n_frames = 1 + (len(wav_1d) - frame_len) // hop_len
    rms = np.empty(n_frames, dtype=np.float32)
    for i in range(n_frames):
        seg = wav_1d[i * hop_len : i * hop_len + frame_len]
        rms[i] = float(np.sqrt(np.mean(seg * seg) + 1e-12))

    noise_floor = float(np.percentile(rms, 15))
    peak_level = float(np.percentile(rms, 95))
    thresh = max(noise_floor * 1.6, peak_level * 0.045, 0.006)
    speech = rms >= thresh

    segments: list[tuple[float, float]] = []
    in_seg = False
    start_idx = 0
    for i, is_sp in enumerate(speech):
        if is_sp and not in_seg:
            in_seg = True
            start_idx = i
        elif not is_sp and in_seg:
            in_seg = False
            s = start_idx * hop_len / float(sr)
            e = (i * hop_len + frame_len) / float(sr)
            if e - s >= 0.35:
                segments.append((s, e))
    if in_seg:
        s = start_idx * hop_len / float(sr)
        e = len(wav_1d) / float(sr)
        if e - s >= 0.35:
            segments.append((s, e))

    # Merge tiny intra-word pauses (< 0.25s) while keeping speaker pauses distinct
    merged: list[tuple[float, float]] = []
    for s, e in segments:
        if merged and (s - merged[-1][1]) < 0.25:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


def _detect_speech_turns(wav_1d: torch.Tensor, sr: int = 16000) -> list[tuple[float, float]]:
    """Detects speech timestamp intervals using Silero VAD (or energy fallback)."""
    model, utils = _get_silero_vad()
    if model is not None and utils is not None:
        try:
            get_speech_timestamps = utils[0]
            ts = get_speech_timestamps(
                wav_1d.cpu(),
                model,
                sampling_rate=sr,
                threshold=0.45,
                min_speech_duration_ms=450,
                min_silence_duration_ms=350,
            )
            turns = [(t["start"] / float(sr), t["end"] / float(sr)) for t in ts]
            if turns:
                return turns
        except Exception as e:
            logger.warning(f"Silero VAD inference failed, falling back to energy VAD: {e}")

    return _energy_vad(wav_1d.cpu().numpy(), sr=sr)


def _extract_speaker_embedding(seg_1d: torch.Tensor, sr: int, mfcc_transform) -> np.ndarray:
    """Extracts vocal-tract MFCC (dropping c0 energy) + delta mean/std raw speaker vector."""
    with torch.no_grad():
        mfcc = mfcc_transform(seg_1d.unsqueeze(0)).squeeze(0)  # [n_mfcc, T]
        mfcc = mfcc[1:, :]  # drop c0 energy so volume doesn't dominate speaker identity
        if mfcc.shape[-1] < 3:
            mean = mfcc.mean(dim=-1)
            std = torch.zeros_like(mean)
            d_mean = torch.zeros_like(mean)
        else:
            mean = mfcc.mean(dim=-1)
            std = mfcc.std(dim=-1)
            delta = mfcc[:, 1:] - mfcc[:, :-1]
            d_mean = delta.abs().mean(dim=-1)
        vec = torch.cat([mean, std, d_mean], dim=0).cpu().numpy().astype(np.float32)
    return vec


def _cosine_agglomerative_cluster(
    raw_embeddings: np.ndarray,
    max_speakers: int = 4,
    distance_threshold: float = 1.12,
) -> list[int]:
    """
    Centers embeddings by recording mean (CMN-style speaker contrast) before L2-normalizing,
    then runs average-linkage cosine clustering so distinct voices separate cleanly.
    """
    n = len(raw_embeddings)
    if n <= 1:
        return [0] * n

    # Check if recording actually has meaningful vocal variance across windows
    centered = raw_embeddings - np.mean(raw_embeddings, axis=0, keepdims=True)
    norms = np.linalg.norm(centered, axis=1, keepdims=True)
    if float(np.median(norms)) < 1.5:
        return [0] * n

    embeddings = centered / (norms + 1e-8)
    sim = np.clip(embeddings @ embeddings.T, -1.0, 1.0)
    dist_mat = 1.0 - sim

    clusters: list[list[int]] = [[i] for i in range(n)]

    while len(clusters) > 1:
        best_pair = None
        best_dist = float("inf")
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                d = float(np.mean(dist_mat[np.ix_(clusters[i], clusters[j])]))
                if d < best_dist:
                    best_dist = d
                    best_pair = (i, j)

        if best_pair is None:
            break
        if len(clusters) <= max_speakers and best_dist > distance_threshold:
            break

        i, j = best_pair
        clusters[i] = clusters[i] + clusters[j]
        clusters.pop(j)

    # Sort speaker IDs by first appearance order so Speaker 1 is always who speaks first
    clusters.sort(key=lambda members: min(members))
    labels = [0] * n
    for spk_idx, members in enumerate(clusters):
        for m in members:
            labels[m] = spk_idx
    return labels


def diarize_audio_tensor(
    wav_tensor: torch.Tensor,
    sr: int = 16000,
    max_speakers: int = 4,
) -> list[dict]:
    """
    Runs sequential VAD + speaker embedding clustering on a mono audio tensor [1, N].
    Returns chronological speaker turns: [{ label, start_s, end_s }].
    """
    wav_1d = wav_tensor.squeeze(0).detach().cpu().float()
    total_dur = len(wav_1d) / float(sr)
    if total_dur < 0.5:
        return []

    raw_turns = _detect_speech_turns(wav_1d, sr=sr)
    if not raw_turns:
        return [{"label": "Speaker 1", "start_s": 0.0, "end_s": round(total_dur, 2)}]

    # Sub-slice speech turns (> 2.5s) into ~2.0s windows so fast back-and-forth conversations split accurately
    windows: list[tuple[float, float]] = []
    for s, e in raw_turns:
        if e - s <= 2.5:
            windows.append((s, e))
        else:
            cur = s
            while cur < e:
                nxt = min(e, cur + 2.0)
                if nxt - cur >= 0.7:
                    windows.append((cur, nxt))
                elif windows:
                    windows[-1] = (windows[-1][0], nxt)
                cur = nxt

    if not windows:
        return [{"label": "Speaker 1", "start_s": 0.0, "end_s": round(total_dur, 2)}]

    mfcc_transform = torchaudio.transforms.MFCC(
        sample_rate=sr,
        n_mfcc=24,
        melkwargs={"n_fft": 512, "hop_length": 160, "n_mels": 40},
    )

    embs = []
    valid_windows = []
    for s, e in windows:
        si = int(round(s * sr))
        ei = min(len(wav_1d), int(round(e * sr)))
        if ei - si < int(0.4 * sr):
            continue
        embs.append(_extract_speaker_embedding(wav_1d[si:ei], sr, mfcc_transform))
        valid_windows.append((s, e))

    if not valid_windows:
        return [{"label": "Speaker 1", "start_s": 0.0, "end_s": round(total_dur, 2)}]

    labels = _cosine_agglomerative_cluster(
        np.stack(embs, axis=0),
        max_speakers=max(1, min(6, max_speakers)),
    )

    # Merge adjacent windows assigned to the same speaker (gap <= 1.2s)
    merged: list[dict] = []
    for (s, e), spk in zip(valid_windows, labels):
        spk_label = f"Speaker {spk + 1}"
        if merged and merged[-1]["label"] == spk_label and (s - merged[-1]["end_s"]) <= 1.2:
            merged[-1]["end_s"] = round(e, 2)
        else:
            merged.append({"label": spk_label, "start_s": round(s, 2), "end_s": round(e, 2)})

    return merged
