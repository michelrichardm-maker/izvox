"""Tests pour src/audio_process_capture.py — stub Tier 3."""

import platform

import pytest

from src.audio_process_capture import (
    ProcessLoopbackNotSupported,
    ProcessLoopbackStream,
    find_target_process_pid,
    find_teams_pid,
    is_process_loopback_supported,
    process_loopback_capture,
)


def test_is_process_loopback_supported_returns_false_for_now():
    """Le stub annonce explicitement qu'il n'est pas opérationnel."""
    assert is_process_loopback_supported() is False


def test_process_loopback_capture_raises_on_non_windows():
    if platform.system() == "Windows":
        pytest.skip("Test pour les OS non-Windows")
    with pytest.raises(ProcessLoopbackNotSupported):
        process_loopback_capture(pid=1234)


def test_stream_raises_on_read():
    s = ProcessLoopbackStream()
    with pytest.raises(ProcessLoopbackNotSupported):
        s.read(1024)


def test_stream_close_is_noop():
    s = ProcessLoopbackStream()
    s.close()  # ne doit pas crasher


def test_find_target_process_pid_returns_none_for_unknown():
    """Un process qui n'existe pas doit retourner None, pas planter."""
    pid = find_target_process_pid(["definitely-not-a-real-process-xyz123"])
    assert pid is None


def test_find_teams_pid_does_not_crash():
    """find_teams_pid doit retourner None ou un int, jamais lever."""
    result = find_teams_pid()
    assert result is None or isinstance(result, int)
