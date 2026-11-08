"""The ``process-1`` sink of the host (PROCESS-PROFILE.md). Demo level, POSIX only.

The host runs a shell command that holds references. Each trusted reference is
replaced by a command substitution that reads a named pipe (FIFO). A thread of the
host opens the write end of each pipe; that open returns only when the command opens
the read end. Only then does the host resolve, all references of the command in one
step, and write each value into its pipe. So:

* the destination is the program name, never the command line (section 3);
* a command that the person refuses, or that never reads a value, costs no resolve
  request (section 4, rule 1);
* if one resolve fails, the host kills the command and gives it no value (section 4,
  rule 2), with exit status 97;
* the value goes through a pipe, not through the command line of the shell or the
  environment (section 4, rule 3). Where the reference stands in an argument, the
  program gets the value in its own argument list; a here-document or standard
  input avoids that;
* the host collects the whole output and masks every value that it released in the
  session before the model sees it, also after a failure, a signal or a timeout
  (section 5). If the masking fails, the host gives no output to the model.

What it does not cover (section 7): a program that prints the value in an encoding
that ``SessionMask`` does not know, writes it to a file or sends it to the network. A
reference must stand where the shell expands a command substitution (unquoted or in
double quotes). Inside single quotes it does not expand. Each occurrence of a
reference gets its own pipe, which gives the value once: a command that reads one
occurrence twice (a loop) waits until the timeout. There is no sandbox.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
import shlex
import shutil
import signal
import subprocess
import tempfile
import threading
from typing import Callable

from .output_guard import SessionMask
from .provenance import AmbiguousReference, ProvenanceStore, UnknownReference
from .reference import find_tokens
from .resolver import ResolutionError, Resolver, SinkContext
from .sink_profiles import SINK_TYPES, PROCESS

#: The exit status of a command that the host stopped because a resolve failed.
EXIT_RESOLVE_FAILED = 97
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*", re.S)


def supported() -> bool:
    """True where the host can give a value through a pipe and mask the output (rule 4 of section 1)."""
    return os.name == "posix" and hasattr(os, "mkfifo")


def program_name(command: str) -> str:
    """The destination of section 3: the first word after leading ``NAME=value`` assignments, its last
    path part. ``sh`` if the command holds only assignments. Never an argument or the command line."""
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        words = command.split()
    for word in words:
        if _ASSIGNMENT.fullmatch(word):
            continue
        name = word.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
        return name or "sh"
    return "sh"


@dataclass
class ProcessResult:
    """What the host gives back. ``model_output`` is masked; the other fields are counts and codes."""

    program: str
    exit_status: int | None = None
    model_output: str = ""
    references: int = 0
    references_withheld: int = 0
    resolve_requests: int = 0
    resolved: bool = False
    refused: bool = False
    timed_out: bool = False
    failure: str | None = None


class ProcessSink:
    """Run one command with the values of its trusted references (``process-1``)."""

    def __init__(self, provenance: ProvenanceStore, resolver: Resolver, *, mask: SessionMask,
                 principal: str = "resolver-token-subject", shell: str = "/bin/sh", timeout: float = 60.0) -> None:
        self._provenance = provenance
        self._resolver = resolver
        self._mask = mask
        self._principal = principal
        self._shell = shell
        self._timeout = timeout

    def _issuer(self, token: str) -> str | None:
        try:
            return self._provenance.issuer_for(token)
        except (UnknownReference, AmbiguousReference):
            return None

    def run(self, command: str, *, approve: Callable[[str, str], bool] = lambda program, command: True
            ) -> ProcessResult:
        """Run ``command``. ``approve(program, command)`` is the decision before the run; the command text
        holds references, never values. A refused command gets no resolve request."""
        program = program_name(command)
        result = ProcessResult(program=program)
        if find_tokens(program):
            result.failure = "the program name holds a reference"
            return result
        tokens = list(dict.fromkeys(ref.token for ref in find_tokens(command)))
        trusted = {t: self._issuer(t) for t in tokens}
        trusted = {t: issuer for t, issuer in trusted.items() if issuer is not None}
        # Reference-shaped text without a trusted observation stays ordinary text (section 2).
        result.references, result.references_withheld = len(trusted), len(tokens) - len(trusted)
        if not supported():
            result.failure = "this platform cannot mask command output"
            return result
        if not approve(program, command):
            result.refused = True
            result.failure = "the command was refused before it ran"
            return result
        workdir = tempfile.mkdtemp(prefix="sref-process-")
        try:
            return self._run(command, program, trusted, workdir, result)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _run(self, command: str, program: str, trusted: dict[str, str], workdir: str,
             result: ProcessResult) -> ProcessResult:
        # One pipe per occurrence: each pipe gives its value once, to the one reader that opens it.
        pipes: list[tuple[str, str]] = []
        pattern = re.compile("|".join(re.escape(t) for t in trusted)) if trusted else None

        def substitute(match: re.Match) -> str:
            path = os.path.join(workdir, f"v{len(pipes)}")
            os.mkfifo(path, 0o600)
            pipes.append((match.group(0), path))
            return f"$(cat {shlex.quote(path)})"

        script = pattern.sub(substitute, command) if pattern else command
        state: dict = {"values": None, "error": None, "done": False}
        lock = threading.Lock()
        process = subprocess.Popen([self._shell, "-c", script], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)

        def resolve_all() -> None:
            # Every reference of the command before any value (section 4, rule 2).
            by_issuer: dict[str, list[str]] = {}
            for token, issuer in trusted.items():
                by_issuer.setdefault(issuer, []).append(token)
            values: dict[str, str] = {}
            context = SinkContext(SINK_TYPES[PROCESS], program, self._principal)
            try:
                for issuer, refs in by_issuer.items():
                    result.resolve_requests += 1
                    values.update(self._resolver.resolve(issuer, refs, context))
                if set(values) != set(trusted):
                    raise ResolutionError("incomplete")
            except ResolutionError as error:
                state["error"] = getattr(error, "code", "resolution_failed")
                _kill(process)
                return
            self._mask.release(values)
            state["values"] = values

        def serve(token: str, path: str) -> None:
            try:
                fd = os.open(path, os.O_WRONLY)          # returns when the command opens the read end
            except OSError:
                return
            try:
                with lock:
                    if state["done"]:
                        return
                    if state["values"] is None and state["error"] is None:
                        resolve_all()
                    value = (state["values"] or {}).get(token)
                if value is not None:
                    os.write(fd, value.encode())
            except OSError:
                pass
            finally:
                os.close(fd)

        threads = [threading.Thread(target=serve, args=item, daemon=True) for item in pipes]
        for thread in threads:
            thread.start()
        try:
            out, err = process.communicate(timeout=self._timeout)
        except subprocess.TimeoutExpired:
            result.timed_out = True
            _kill(process)
            out, err = process.communicate()
        with lock:
            state["done"] = True
        readers = []
        for _, path in pipes:                            # release a writer that waits for a reader
            try:
                readers.append(os.open(path, os.O_RDONLY | os.O_NONBLOCK))
            except OSError:
                pass
        for thread in threads:
            thread.join(2)
        for fd in readers:
            os.close(fd)
        result.resolved = state["values"] is not None
        if state["error"] is not None:
            result.failure = f"resolution failed: {state['error']}"
            result.exit_status = EXIT_RESOLVE_FAILED
        else:
            result.exit_status = process.returncode
        try:
            text = out.decode("utf-8", "replace") + err.decode("utf-8", "replace")
            result.model_output = self._mask.mask(text)
        except Exception:  # noqa: BLE001 — section 5, rule 2: no masking, no output
            result.model_output = ""
            result.failure = result.failure or "the output could not be masked"
        return result


def _kill(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
