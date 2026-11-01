"""Sequential, recoverable download queue independent from Tk and its main thread."""
from dataclasses import asdict, dataclass, field
import logging
from pathlib import Path
from queue import Queue, Empty
import threading
import time
from urllib.parse import urlparse, parse_qs
from uuid import uuid4

from config.settings import QUEUE_FILE
from core.downloader import DownloadEngine, DownloadCancelled, clean_ansi
from core.storage import JsonStore
from core.validator import SecurityValidator

FINISHED = {"completed", "failed", "cancelled"}
ACTIVE = {"downloading", "converting"}


@dataclass
class DownloadJob:
    url: str
    format_type: str
    quality: str
    destination: str
    embed_thumbnail: bool = True
    title: str = ""
    id: str = field(default_factory=lambda: uuid4().hex)
    status: str = "pending"
    error: str = ""
    filepath: str = ""
    created: float = field(default_factory=time.time)
    playlist_id: str = ""


class DownloadManager:
    def __init__(self, emit, store=None, engine_factory=DownloadEngine, resolver=None, autostart=True):
        self.emit = emit
        self.store = store or JsonStore(QUEUE_FILE)
        self.engine_factory = engine_factory
        self.resolver = resolver or DownloadEngine.extract_playlist_urls
        self._condition = threading.Condition(threading.RLock())
        self._closed = False
        self.paused = True  # Recovered downloads wait for the user.
        self._engine = None
        self._active_id = None
        self._progress_value = 0.0
        self._revision = 0
        self._resolutions = Queue()
        self.jobs = []
        self._playlists = {}
        saved = self.store.read([])
        if isinstance(saved, dict) and saved.get("schema") == 2:
            groups = saved.get("playlists", {})
            if isinstance(groups, dict):
                for pid, group in groups.items():
                    if not isinstance(pid, str) or not isinstance(group, dict):
                        continue
                    total = group.get("total")
                    retired = group.get("retired", {})
                    if (total is None or type(total) is int and 0 <= total <= 2000) and isinstance(retired, dict):
                        self._playlists[pid] = {"total": total, "retired": {
                            s: min(2000, max(0, retired.get(s, 0))) if type(retired.get(s)) is int else 0 for s in FINISHED}}
            saved = saved.get("jobs", [])
        if isinstance(saved, list):
            # Capacity is 2000 pending jobs plus up to 100 history records.
            for data in saved[-2100:]:
                try:
                    job = DownloadJob(**data)
                    if not SecurityValidator.is_valid_youtube_url(job.url):
                        continue
                    if job.status not in FINISHED:
                        job.status = "pending"
                    if not isinstance(job.playlist_id, str):
                        job.playlist_id = ""
                    if self.is_playlist(job.url):
                        self._ensure_playlist(job)
                    self.jobs.append(job)
                except (TypeError, ValueError):
                    continue
        self._worker = threading.Thread(target=self._run, daemon=True, name="download-queue")
        self._resolver = threading.Thread(target=self._resolve_loop, daemon=True, name="playlist-resolver")
        if autostart:
            self._worker.start()
            self._resolver.start()

    def snapshot(self):
        with self._condition:
            return [asdict(job) for job in self.jobs]

    def _ensure_playlist(self, job):
        job.playlist_id = job.playlist_id or job.id
        self._playlists.setdefault(job.playlist_id, {"total": None, "retired": dict.fromkeys(FINISHED, 0)})

    def _playlist_progress(self):
        """Equal weight per file, including the active file's partial progress.

        Completed groups remain separate from singles and other playlists.
        Retired counters survive history trimming, clearing and application restarts.
        """
        context = self._find(self._active_id) if self._active_id else None
        if context is None:
            context = next((j for j in self.jobs if j.status not in FINISHED), None)
        if context is None and self.jobs:
            context = self.jobs[-1]
        if not context or not context.playlist_id:
            return None
        group = self._playlists.get(context.playlist_id)
        if not group:
            return None
        members = [j for j in self.jobs if j.playlist_id == context.playlist_id]
        counts = {s: group["retired"][s] + sum(j.status == s for j in members) for s in FINISHED}
        total = group["total"]
        done = sum(counts.values())
        partial = (0.97 if context.status == "converting" else self._progress_value) if context.status in ACTIVE else 0
        return {"id": context.playlist_id, "total": total or 0, "done": done,
            **counts, "reading": total is None and context.status not in FINISHED,
            "value": min(1, (done + partial) / total) if total else 0}

    def queue_state(self, jobs=None):
        with self._condition:
            return {"jobs": self.snapshot() if jobs is None else jobs, "paused": self.paused, "playlist": self._playlist_progress(),
                "revision": self._revision, "current_progress": self._progress_value}

    def _retire(self, jobs):
        for job in jobs:
            group = self._playlists.get(job.playlist_id)
            if group and job.status in FINISHED:
                group["retired"][job.status] += 1

    def _changed(self):
        # Caller holds the condition lock. No Tk code is ever called here.
        finished = [job for job in self.jobs if job.status in FINISHED]
        if len(finished) > 100:
            self._retire(finished[:-100])
            discard = {job.id for job in finished[:-100]}
            self.jobs = [job for job in self.jobs if job.id not in discard]
        referenced = {job.playlist_id for job in self.jobs}
        self._playlists = {pid: group for pid, group in self._playlists.items() if pid in referenced}
        snapshot = self.snapshot()
        try:
            self.store.write({"schema": 2, "jobs": snapshot, "playlists": self._playlists})
        except OSError:
            logging.getLogger(__name__).exception("No se pudo guardar la cola")
            self.emit("log", "[!] No se pudo guardar la cola. Comprueba el espacio disponible.")
        self._revision += 1
        self.emit("queue", self.queue_state(snapshot))
        self._condition.notify_all()

    @staticmethod
    def is_playlist(url):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        playlist = query.get("list", [""])[0]
        return parsed.path.rstrip("/") == "/playlist" or bool(playlist and not playlist.startswith("RD"))

    def submit(self, url, format_type, quality, destination, embed_thumbnail=True, title="", start=True):
        if not SecurityValidator.is_valid_youtube_url(url):
            raise ValueError("Pega un enlace de video o playlist de YouTube.")
        with self._condition:
            if self._closed:
                raise RuntimeError("La aplicación se está cerrando.")
            if len([j for j in self.jobs if j.status not in FINISHED]) >= 2000:
                raise ValueError("La cola tiene 2000 elementos. Espera a que termine antes de añadir más.")
            duplicate = next((j for j in self.jobs if j.status not in FINISHED and
                              (j.url, j.format_type, j.quality, j.destination, j.embed_thumbnail) ==
                              (url, format_type, quality, str(destination), embed_thumbnail)), None)
            if duplicate:
                if start:
                    self.paused = False
                    self._changed()
                self.emit("log", "[i] Este enlace ya está en la cola con la misma calidad.")
                return duplicate.id
            job = DownloadJob(url, format_type, quality, str(destination), embed_thumbnail, title or url)
            if self.is_playlist(url):
                self._ensure_playlist(job)
                job.status = "resolving"
                job.title = title or "Leyendo playlist…"
            self.jobs.append(job)
            if start:
                self.paused = False
            self._changed()
            if job.status == "resolving":
                self._resolutions.put(job.id)
            return job.id

    def _find(self, job_id):
        return next((j for j in self.jobs if j.id == job_id), None)

    def _resolve_loop(self):
        while not self._closed:
            try:
                job_id = self._resolutions.get(timeout=0.3)
            except Empty:
                continue
            with self._condition:
                job = self._find(job_id)
                if not job or job.status != "resolving":
                    continue
            try:
                urls = self.resolver(job.url)
                urls = list(dict.fromkeys(u for u in urls if SecurityValidator.is_valid_youtube_url(u)))
                if not urls:
                    raise ValueError("La playlist está vacía, es privada o no se pudo leer.")
                with self._condition:
                    if job.status != "resolving" or self._closed:
                        continue
                    available = 2000 - len([j for j in self.jobs if j.status not in FINISHED]) + 1
                    if len(urls) > available:
                        raise ValueError("La playlist supera la capacidad disponible de 2000 elementos. Usa una lista más pequeña.")
                    position = self.jobs.index(job)
                    existing = {(j.url, j.format_type, j.quality, j.destination, j.embed_thumbnail)
                                for j in self.jobs if j.status not in FINISHED and j.id != job.id}
                    expanded = []
                    for index, url in enumerate(urls, 1):
                        key = (url, job.format_type, job.quality, job.destination, job.embed_thumbnail)
                        if key not in existing:
                            expanded.append(DownloadJob(url, job.format_type, job.quality, job.destination,
                                                        job.embed_thumbnail, f"Video {index} de la playlist", playlist_id=job.playlist_id))
                            existing.add(key)
                    self.jobs[position:position + 1] = expanded
                    self._playlists[job.playlist_id]["total"] = len(expanded)
                    self.emit("log", f"[+] Playlist preparada: {len(expanded)} videos añadidos.")
                    self._changed()
            except Exception as error:
                with self._condition:
                    if not self._closed and job.status == "resolving":
                        job.status, job.error = "failed", clean_ansi(str(error))
                        self._changed()

    def resume(self):
        with self._condition:
            self.paused = False
            self._changed()

    def pause(self):
        with self._condition:
            self.paused = True
            self._changed()

    def cancel(self, job_id):
        with self._condition:
            job = self._find(job_id)
            if not job or job.status in FINISHED:
                return
            job.status = "cancelled"
            if self._active_id == job_id and self._engine:
                self._engine.cancel()
            self._changed()

    def retry(self, job_id):
        with self._condition:
            job = self._find(job_id)
            if not job or job.status not in {"failed", "cancelled"} or job_id == self._active_id:
                return
            job.status = "resolving" if self.is_playlist(job.url) else "pending"
            job.error = ""
            self.paused = False
            self._changed()
            if job.status == "resolving":
                self._resolutions.put(job.id)

    def clear_finished(self):
        with self._condition:
            self._retire([job for job in self.jobs if job.status in FINISHED and job.id != self._active_id])
            self.jobs = [job for job in self.jobs if job.status not in FINISHED or job.id == self._active_id]
            self._changed()

    def _progress(self, job, value, percent, speed, eta):
        with self._condition:
            if job.status != "downloading" or self._active_id != job.id:
                return
            self._progress_value = min(0.94, max(self._progress_value, value * 0.94))
            self._revision += 1
            self.emit("progress", {"id": job.id, "value": self._progress_value, "speed": speed, "eta": eta,
                "playlist": self._playlist_progress(), "revision": self._revision})

    def _status(self, job, code, label):
        with self._condition:
            if job.status not in ACTIVE:
                return
            if code == "title":
                if job.title == label:
                    return
                job.title = label
            elif code == "converting":
                if job.status == "converting":
                    return
                job.status = "converting"
            else:
                return
            self._changed()

    def _run(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._closed or (not self.paused and any(j.status == "pending" for j in self.jobs)))
                if self._closed:
                    return
                job = next(j for j in self.jobs if j.status == "pending")
                # A recovered playlist must be expanded again rather than bypassing the queue.
                if self.is_playlist(job.url):
                    self._ensure_playlist(job)
                    job.status = "resolving"
                    self._resolutions.put(job.id)
                    self._changed()
                    continue
                job.status = "downloading"
                self._progress_value = 0.0
                self._active_id = job.id
                engine = self.engine_factory(
                    on_progress=lambda *args: self._progress(job, *args),
                    on_log=lambda message: self.emit("log", message),
                    on_status=lambda code, label: self._status(job, code, label),
                )
                self._engine = engine
                self._changed()
            try:
                result = engine.execute_download(job.url, job.format_type, job.quality,
                                                 Path(job.destination), job.embed_thumbnail)
                with self._condition:
                    if job.status != "cancelled" and not self._closed:
                        job.status = "completed"
                        job.filepath = (result or {}).get("filepath", "")
                        job.title = (result or {}).get("title") or job.title
                        self.emit("log", f"[✓] Guardado: {job.title}")
            except Exception as error:
                with self._condition:
                    if job.status == "cancelled":
                        pass
                    elif self._closed or isinstance(error, DownloadCancelled):
                        job.status = "pending" if self._closed else "cancelled"
                    else:
                        job.status, job.error = "failed", clean_ansi(str(error))
                        logging.getLogger(__name__).exception("Falló %s", job.url)
                        self.emit("log", f"[ERROR] {job.title}: {job.error}")
            finally:
                with self._condition:
                    self._engine = None
                    self._active_id = None
                    if not any(j.status in {"pending", "resolving"} for j in self.jobs):
                        self.paused = True
                    self._changed()
                    if self._closed:
                        return
                # Gentle spacing; the condition wait remains interruptible on close.
                with self._condition:
                    self._condition.wait(timeout=1.0)

    def close(self):
        with self._condition:
            self._closed = True
            self.paused = True
            if self._engine:
                self._engine.cancel()
            for job in self.jobs:
                if job.status in ACTIVE:
                    job.status = "pending"
            self._changed()
