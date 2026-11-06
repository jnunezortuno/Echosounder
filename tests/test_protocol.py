from dataclasses import replace
import struct
import threading

import numpy as np
import pytest

from echosounder.device import Cancelled, ProtocolError, SerialDevice
from echosounder.model import SAMPLES, Settings


class FirmwareSerial:
    """Byte-stream firmware peer: short writes and fragmented reads are deliberate."""
    def __init__(self, wrong_ack=None, silent=False, **kwargs):
        self.kwargs = kwargs
        self.pending = bytearray()
        self.receive = bytearray()
        self.packets = []
        self.closed = False
        self.wrong_ack = wrong_ack
        self.silent = silent

    def reset_input_buffer(self):
        self.receive.clear()

    def write(self, data):
        chunk = data[:3]
        self.pending.extend(chunk)
        if len(self.pending) == 5:
            packet = bytes(self.pending)
            self.pending.clear()
            self.packets.append(packet)
            command, value = struct.unpack("<Bi", packet)
            if self.silent:
                return len(chunk)
            if command == 1:
                self.receive.extend(np.arange(SAMPLES, dtype="<i4").tobytes())
            elif command == 5:
                self.receive.extend(b"\x05\x00\x01\x02\x03")
            else:
                ack = 255 if command == self.wrong_ack else command
                self.receive.extend(struct.pack("<Bi", ack, value))
        return len(chunk)

    def read(self, count):
        count = min(count, 37)
        chunk = bytes(self.receive[:count])
        del self.receive[:count]
        return chunk

    def close(self):
        self.closed = True


def make_device(peer, **settings):
    return SerialDevice(Settings(port="TEST", **settings), threading.Event(),
                        serial_factory=lambda **kwargs: peer)


def test_handshake_configuration_and_fragmented_trace():
    peer = FirmwareSerial()
    device = make_device(peer)
    confirmed, version = device.open()
    assert version == "v1.2.3"
    assert confirmed == Settings(port="TEST")
    assert peer.packets == [struct.pack("<Bi", cmd, val) for cmd, val in
                            [(0, 0), (5, 0), (3, 50), (4, 3), (2, 1), (6, 0x90)]]
    np.testing.assert_array_equal(device.acquire(), np.arange(SAMPLES))
    assert peer.packets[-1] == b"\x01\x00\x00\x00\x00"
    device.close()
    assert peer.closed


def test_serial_line_options_are_actually_applied():
    peers = []
    def factory(**kwargs):
        peers.append(FirmwareSerial(**kwargs))
        return peers[-1]
    device = SerialDevice(Settings(port="TEST", stopbits=2), threading.Event(), factory)
    device.open()
    assert peers[0].kwargs["stopbits"] == 2
    assert peers[0].kwargs["baudrate"] == 921600
    assert peers[0].kwargs["timeout"] == 0.05
    device.close()


def test_wrong_ack_closes_failed_connection():
    peer = FirmwareSerial(wrong_ack=3)
    with pytest.raises(ProtocolError, match="Respuesta inesperada"):
        make_device(peer).open()
    assert peer.closed


def test_incomplete_reply_times_out_and_closes():
    peer = FirmwareSerial(silent=True)
    with pytest.raises(ProtocolError, match="0 de 5 bytes"):
        make_device(peer, timeout=0.1).open()
    assert peer.closed


def test_cancellation_closes_connection():
    peer = FirmwareSerial()
    device = make_device(peer)
    device.cancel.set()
    with pytest.raises(Cancelled):
        device.open()
    assert peer.closed


def test_rejects_port_reconfiguration_while_open():
    device = make_device(FirmwareSerial())
    device.open()
    with pytest.raises(ValueError, match="Desconecta"):
        device.configure(replace(device.settings, baudrate=115200))
    device.close()


def test_rejects_impossible_firmware_confirmation():
    class InvalidFirmware(FirmwareSerial):
        def read(self, count):
            if self.packets[-1][0] == 2 and len(self.receive) == 5:
                self.receive[:] = b"\x02\x00\x00\x00\x00"
            return super().read(count)
    peer = InvalidFirmware()
    with pytest.raises(ValueError, match="repetitions"):
        make_device(peer).open()
    assert peer.closed
