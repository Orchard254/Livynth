#!/usr/bin/env python3
"""LIVYNTH Studio — local character, narration and portrait-video production.

Run on Windows: double-click Start_LIVYNTH_Studio.bat or use
  python livynth_studio.py --mode preview --text 'Hello from Livynth.'

No uploads, subscriptions or web service. Blender + MPFB and Windows built-in
System.Speech are needed for automatic character and speech generation.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
import wave

ROOT = Path(__file__).resolve().parent
BLENDER = 'blender'
DEFAULT_TEXT = (
    'Welcome to Livynth. We create digital humans who can speak and bring '
    'stories to life. This is our first working studio demonstration.'
)


@dataclass(frozen=True)
class Task:
    title: str
    argv: tuple[str, ...]
    artifact: Path
    kind: str


def find_blender(explicit='') -> str:
    if explicit:
        candidate = Path(explicit)
        if candidate.is_file():
            return str(candidate.resolve())
        found = shutil.which(explicit)
        if found:
            return found
        raise ValueError(f'Blender not found: {explicit}')
    found = shutil.which('blender')
    if found:
        return found
    if os.name == 'nt':
        for env in ('ProgramFiles', 'ProgramW6432', 'ProgramFiles(x86)'):
            base = os.environ.get(env)
            if base:
                matches = sorted(Path(base).glob('Blender Foundation/Blender */blender.exe'), reverse=True)
                if matches:
                    return str(matches[0])
    raise ValueError('Blender is not installed. Install Blender 4.5 LTS and MPFB, then try again.')


def make_plan(*, text: str, mode: str, output_dir: Path, blender: str,
              glb: Path | None = None, audio: Path | None = None) -> list[Task]:
    if mode not in ('preview', 'smoke', 'video'):
        raise ValueError('Mode must be preview, smoke or video')
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Please enter the words the character should say')
    if len(text) > 2000:
        raise ValueError('Maximum script length is 2,000 characters')
    out = output_dir.resolve()
    blender_path = str(blender)
    character = glb.resolve() if glb else out / 'neutral_character.glb'
    speech = audio.resolve() if audio else out / 'narration.wav'
    tasks: list[Task] = []
    if glb is None:
        tasks.append(Task('Generate rigged neutral 3D character',
            (blender_path, '--background', '--python', str(ROOT/'tools/mpfb_headless_probe.py'), '--',
             '--out', str(character), '--json', str(out/'character_report.json')),
            character, 'glb'))
    elif not glb.is_file():
        raise ValueError(f'GLB character does not exist: {glb}')
    if audio is None:
        if os.name != 'nt':
            raise ValueError('Automatic test speech requires Windows. Provide a PCM WAV with --audio.')
        tasks.append(Task('Generate local narration',
            ('powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
             str(ROOT/'tools/studio_voice.ps1'), '-VoiceText', text, '-OutputWav', str(speech)),
            speech, 'wav'))
    elif not audio.is_file():
        raise ValueError(f'Voice WAV does not exist: {audio}')
    command = [sys.executable, str(ROOT/'video/build_video.py'), '--glb', str(character),
               '--audio', str(speech), '--text', text, '--blender', blender_path,
               '--out', str(out / ('livynth_preview.mp4' if mode == 'preview'
                                   else 'livynth_smoke.mp4' if mode == 'smoke'
                                   else 'livynth_video.mp4'))]
    if mode == 'preview':
        command.append('--preview')
        artifact = out / 'livynth_preview.png'
        kind = 'png'
    elif mode == 'smoke':
        command.extend(['--max-frames', '30'])
        artifact = out / 'livynth_smoke.mp4'
        kind = 'mp4'
    else:
        artifact = out / 'livynth_video.mp4'
        kind = 'mp4'
    tasks.append(Task('Render studio ' + mode, tuple(command), artifact, kind))
    return tasks


def check_output(task: Task):
    p = task.artifact
    if not p.is_file() or p.stat().st_size < (32 if task.kind == 'wav' else 100):
        raise RuntimeError(f'{task.title} did not create expected output: {p}')
    if task.kind == 'glb':
        if p.read_bytes()[:4] != b'glTF':
            raise RuntimeError(f'Expected binary GLB, got: {p}')
        report_path = p.with_name('character_report.json')
        if not report_path.is_file():
            raise RuntimeError('Missing Blender character audit')
        report = json.loads(report_path.read_text(encoding='utf-8'))
        if not report.get('assertions_passed') or report.get('errors'):
            raise RuntimeError('Blender rejected the character export')
        audit = report.get('glb_audit', {})
        if audit.get('joint_count') != 163 or audit.get('morph_targets_in_exported_glb') != 67:
            raise RuntimeError('Neutral character lost required joints/morphs')
    elif task.kind == 'wav':
        with wave.open(str(p), 'rb') as f:
            if f.getnframes() < 100 or f.getframerate() <= 0:
                raise RuntimeError('Speech file is empty')
    elif task.kind == 'png':
        with p.open('rb') as f:
            if f.read(8) != b'\x89PNG\r\n\x1a\n':
                raise RuntimeError('Preview file is not a PNG')
    elif task.kind == 'mp4':
        with p.open('rb') as f:
            f.seek(4)
            if f.read(4) != b'ftyp':
                raise RuntimeError('Video file is not an MP4 container')


def execute(tasks: list[Task], *, output_dir: Path, log, stop=None):
    """Run the plan, validate artifacts, save a truthful JSON report.

    `stop` is an optional threading.Event. Does not claim audio stream quality
    or likeness verified from a file-header check.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {'schema': 'livynth.studio.run.v1', 'steps': [],
              'status': 'RUNNING', 'identity_likeness': 'UNVERIFIED',
              'video_audio_stream': 'UNVERIFIED_REQUIRES_PLAYBACK'}
    final_path = output_dir / 'studio_run.json'
    try:
        for task in tasks:
            if stop is not None and stop.is_set():
                raise InterruptedError('Studio task canceled before starting')
            log(f'\n[LIVYNTH] {task.title}\n')
            proc = subprocess.Popen(task.argv, cwd=str(ROOT), stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, errors='replace',
                                    bufsize=1)
            # Reader thread keeps the GUI alive; stdout may remain silent while
            # Blender is rendering, but cancel can still interrupt the process.
            lines: queue.Queue[str] = queue.Queue()
            def reader():
                try:
                    for line in proc.stdout:
                        lines.put(line)
                finally:
                    lines.put(None)
            thread = threading.Thread(target=reader, daemon=True)
            thread.start()
            ended = False
            while not ended or proc.poll() is None:
                try:
                    line = lines.get(timeout=0.10)
                    if line is None:
                        ended = True
                    else:
                        log(line)
                except queue.Empty:
                    pass
                if stop is not None and stop.is_set():
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                                       capture_output=True, check=False)
                    else:
                        proc.terminate()
                    proc.wait()
                    raise InterruptedError('Studio task canceled')
            rc = proc.wait()
            thread.join(timeout=1)
            if proc.stdout is not None:
                proc.stdout.close()
            if rc:
                raise RuntimeError(f'{task.title} failed (exit code {rc}). See the Studio log.')
            check_output(task)
            report['steps'].append({'name': task.title, 'status': 'PASS_ARTIFACT',
                                    'output': str(task.artifact)})
            log(f'[LIVYNTH] Saved: {task.artifact}\n')
        report['status'] = 'PASS_ARTIFACTS_NOT_IDENTITY'
        return report
    except Exception as exc:
        report['status'] = 'CANCELED' if isinstance(exc, InterruptedError) else 'FAILED'
        report['error'] = str(exc)
        raise
    finally:
        final_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def new_run_dir():
    base = ROOT / 'output' / 'studio'
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    return base / stamp


def run_cli(args):
    blender = find_blender(args.blender)
    out = Path(args.out).resolve() if args.out else new_run_dir()
    tasks = make_plan(text=args.text, mode=args.mode, output_dir=out,
                      blender=blender, glb=Path(args.glb) if args.glb else None,
                      audio=Path(args.audio) if args.audio else None)
    print(f'LIVYNTH Studio: {len(tasks)} production stages; output folder: {out}', flush=True)
    result = execute(tasks, output_dir=out, log=lambda msg: print(msg, end='', flush=True))
    print('Run result:', result['status'], flush=True)
    return 0


def launch_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk

    root = tk.Tk()
    root.title('LIVYNTH Studio 0.1 | Give Imagination Life')
    root.minsize(780, 640)
    root.configure(bg='#121925')
    main = ttk.Frame(root, padding=20)
    main.pack(expand=True, fill='both')
    ttk.Label(main, text='LIVYNTH STUDIO', font=('Segoe UI', 22, 'bold')).pack(anchor='w')
    ttk.Label(main, text='Create a neutral 3D presenter, add spoken words, preview and export video.').pack(anchor='w', pady=(0, 14))
    ttk.Label(main, text='What should your character say?').pack(anchor='w')
    transcript = tk.Text(main, height=4, wrap='word')
    transcript.insert('1.0', DEFAULT_TEXT)
    transcript.pack(fill='x', pady=(2, 12))
    vars = {'glb': tk.StringVar(), 'audio': tk.StringVar(), 'blender': tk.StringVar(), 'out': tk.StringVar()}
    def path_field(key, label, filetypes=None):
        row = ttk.Frame(main)
        row.pack(fill='x', pady=3)
        ttk.Label(row, text=label, width=22).pack(side='left')
        ttk.Entry(row, textvariable=vars[key]).pack(side='left', fill='x', expand=True)
        def browse():
            path = filedialog.askdirectory() if key == 'out' else filedialog.askopenfilename(filetypes=filetypes or [('All files', '*.*')])
            if path: vars[key].set(path)
        ttk.Button(row, text='Browse…', command=browse).pack(side='left', padx=(8, 0))
    path_field('glb', 'Character GLB (optional)', [('3D character', '*.glb')])
    path_field('audio', 'Voice WAV (optional)', [('PCM WAV', '*.wav')])
    path_field('blender', 'Blender executable', [('Blender', 'blender.exe'), ('All files', '*.*')])
    path_field('out', 'Output folder (optional)')
    ttk.Label(main, text='Leave the GLB blank to build a neutral rigged character; leave WAV blank for Windows test speech.').pack(anchor='w', pady=(8,12))

    updates = queue.Queue()
    cancel_event = threading.Event()
    controls = ttk.Frame(main)
    controls.pack(fill='x', pady=(4, 10))
    buttons = []
    status = tk.StringVar(value='Ready')
    run_folder = {'path': None}
    def start(mode):
        if status.get().startswith('Working'):
            return
        try:
            blender = find_blender(vars['blender'].get().strip())
            out = Path(vars['out'].get()).resolve() if vars['out'].get().strip() else new_run_dir()
            txt = transcript.get('1.0', 'end').strip()
            tasks = make_plan(text=txt, mode=mode, output_dir=out, blender=blender,
                              glb=Path(vars['glb'].get()) if vars['glb'].get().strip() else None,
                              audio=Path(vars['audio'].get()) if vars['audio'].get().strip() else None)
        except (ValueError, OSError) as e:
            messagebox.showerror('Cannot start', str(e))
            return
        run_folder['path'] = out
        cancel_event.clear()
        for b in buttons: b.configure(state='disabled')
        cancel_btn.configure(state='normal')
        status.set('Working — ' + mode)
        log_view.insert('end', f'\n=== {mode.upper()} / {out} ===\n')
        def worker():
            try:
                result = execute(tasks, output_dir=out, stop=cancel_event,
                                 log=lambda line: updates.put(('log', line)))
                updates.put(('done', result['status']))
            except Exception as exc:
                updates.put(('error', str(exc)))
        threading.Thread(target=worker, daemon=True).start()
    for label, mode in [('1. Preview portrait', 'preview'), ('2. Test 1-sec video', 'smoke'), ('3. Export full MP4', 'video')]:
        b = ttk.Button(controls, text=label, command=lambda m=mode: start(m))
        b.pack(side='left', padx=(0,8))
        buttons.append(b)
    cancel_btn = ttk.Button(controls, text='Cancel', command=cancel_event.set, state='disabled')
    cancel_btn.pack(side='left')
    ttk.Label(main, textvariable=status, font=('Segoe UI', 10, 'bold')).pack(anchor='w')
    log_view = scrolledtext.ScrolledText(main, height=14, state='normal', font=('Consolas', 9))
    log_view.pack(fill='both', expand=True, pady=(8, 10))
    def open_folder():
        folder = run_folder['path'] or ROOT/'output'/'studio'
        if folder.exists():
            os.startfile(str(folder)) if os.name == 'nt' else subprocess.Popen(['xdg-open', str(folder)])
    ttk.Button(main, text='Open output folder', command=open_folder).pack(anchor='w')
    def poll():
        try:
            while True:
                kind, value = updates.get_nowait()
                if kind == 'log':
                    log_view.insert('end', value)
                    log_view.see('end')
                else:
                    status.set('Finished — ' + value if kind == 'done' else 'Failed: ' + value)
                    for b in buttons: b.configure(state='normal')
                    cancel_btn.configure(state='disabled')
                    if kind == 'error': messagebox.showerror('LIVYNTH Studio', value)
        except queue.Empty:
            pass
        root.after(120, poll)
    def on_close():
        cancel_event.set()
        root.destroy()
    root.protocol('WM_DELETE_WINDOW', on_close)
    root.after(120, poll)
    root.mainloop()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('preview','smoke','video'), default='preview')
    parser.add_argument('--text', default=DEFAULT_TEXT)
    parser.add_argument('--glb', help='Existing character GLB; omitted = MPFB neutral character')
    parser.add_argument('--audio', help='Existing PCM WAV; omitted = Windows local speech')
    parser.add_argument('--blender', default='', help='Blender binary path, auto-detected on Windows')
    parser.add_argument('--out', help='Output folder; default is timestamped output/studio folder')
    parser.add_argument('--cli', action='store_true', help='Use console mode instead of window')
    args = parser.parse_args(argv)
    if args.cli:
        try:
            return run_cli(args)
        except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
            print('LIVYNTH STUDIO FAILED:', exc, file=sys.stderr)
            return 2
    launch_gui()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())