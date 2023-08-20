import math
import serial
import time

SYNC_BUFFER_SIZE = 6  # Placeholder value
HARMONIC_SYNC_TX_IRQ_TIMEOUT = 1000  # Placeholder value
millis = lambda: int(time.time() * 1000)  # Placeholder for millis function

def debug(msg, *args):  # Placeholder for debug function
    print(msg % args)

class SyncState:
    def __init__(self, port):
        self._serial = serial.Serial(
            port, 115200, 
            timeout=0, parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
        )
        self._last_interrupt = 0
        self.initState()

    def initState(self):
        self._buffer = [0] * SYNC_BUFFER_SIZE
        self._buffer[0] = 0x80
        self._index = 0
        self._wait_for_sync = True
        self._last_clock = 0
        self._last_beat = 0
        self._last_step = 0
        self._last_reset = 0

    def isAlive(self):
        return millis() - self._last_interrupt < 10

    def txIRQTimeout(self):
        if millis() - self._last_interrupt >= HARMONIC_SYNC_TX_IRQ_TIMEOUT:
            ready = self._serial.readyForTransmit()
            debug("Sync TX IRQ timeout at %d (ready: %s)", millis(), 'yes' if ready else 'no')
            return True
        else:
            return False

    # For RootNote
    def setRootNote(self, root):
        self._buffer[0] = (self._buffer[0] & ~0x0f) | (root % 12)

    def rootNote(self):
        return self._buffer[0] & 0x0f

    def setDegreeNr(self, degree_nr):
        self._buffer[1] = (self._buffer[1] & ~0x0f) | degree_nr

    def degreeNr(self):
        return self._buffer[1] & 0x0f

    def setModeNr(self, mode_nr):
        self._buffer[2] = (self._buffer[2] & ~0x0f) | mode_nr

    def modeNr(self):
        return self._buffer[2] & 0x0f

    def setTransposition(self, trans):
        trans = max(-64, min(63, trans))
        self._buffer[3] = (self._buffer[3] & ~0x7f) | ((trans + 64) & 0x7f)

    def transposition(self):
        return (self._buffer[3] & 0x7f) - 64

    # For detune
    def setChaoticDetune(self, detune):
        # Clamp detune value between -1.0 and 1.0
        detune = max(-1.0, min(1.0, detune))
        # Convert to an integer in the range [0, 126]
        detune_int = int(detune * 63.0) + 63
        # Store the lower 7 bits in _buffer[4]
        self._buffer[4] = detune_int & 0x7f

    def chaoticDetune(self):
        # Convert 7-bit integer back to float
        detune_int = self._buffer[4] - 63
        return float(detune_int) / 63.0

    def setHarmonicShift(self, shift):
        # Convert range [-11, 11] to [5, 27]
        self._buffer[5] = shift + 16

    def harmonicShift(self):
        # Convert back to range [-11, 11]
        return self._buffer[5] - 16

    # For Clock
    def setClock(self, clock):
        self._buffer[0] = (self._buffer[0] & ~0x70) | ((clock % 8) << 4)

    def clock(self):
        return (self._buffer[0] & 0x70) >> 4

    def gotNextClock(self):
        b = self.clock()
        got = b != self._last_clock
        self._last_clock = b
        return got

    # For Beat
    def setBeat(self, beat):
        self._buffer[1] = (self._buffer[1] & ~0x70) | ((beat % 8) << 4)

    def beat(self):
        return (self._buffer[1] & 0x70) >> 4

    def gotNextBeat(self):
        b = self.beat()
        got = b != self._last_beat
        self._last_beat = b
        return got

    # For Step
    def setStep(self, step):
        self._buffer[2] = (self._buffer[2] & ~0x70) | ((step % 8) << 4)

    def step(self):
        return (self._buffer[2] & 0x70) >> 4

    def gotNextStep(self):
        this_step = self.step()
        got = this_step != self._last_step
        self._last_step = this_step
        return got

    # For Reset
    def setReset(self, reset_value):
        self._buffer[5] = (self._buffer[5] & ~0x60) | ((reset_value % 4) << 5)

    def reset(self):
        return (self._buffer[5] & 0x60) >> 5

    def gotNextReset(self):
        this_reset = self.reset()
        got = this_reset != self._last_reset
        self._last_reset = this_reset
        return got

    # Remaining functions...

    def handleRxIRQ(self, byte):
        self._last_interrupt = millis()
        if byte & 0x80:
            self._wait_for_sync = False
            self._index = 0
            self._buffer[0] = byte
        elif not self._wait_for_sync:
            self._buffer[self._index + 1] = byte


    def handleTxIRQ(self):
        self._last_interrupt = millis()
        byte = self._buffer[self._index]
        self._index = (self._index + 1) % SYNC_BUFFER_SIZE
        self._last_sent_byte = byte
        return byte

    def dump(self):
        debug("Sync: " + " ".join([f"{x:02x}" for x in self._buffer]))


    def sendNext(self):
        byte = self._buffer[self._index]
        print(byte)
        self._serial.write([byte])  # Send the byte over the serial line
        self._index = (self._index + 1) % SYNC_BUFFER_SIZE
        self._last_sent_byte = byte

    def startSending(self, interval_ms):
        while True:

            self.sendNext()
            # time.sleep(interval_ms)  # Sleep for the specified interval in milliseconds


if __name__ == "__main__":
    # Create an instance
    # sync = SyncState(port="/dev/ttyAMA0")
    sync = SyncState(port="/dev/ttyS0")



    sync.setRootNote(0)
    sync.setDegreeNr(0)
    sync.setModeNr(0)
    sync.setTransposition(5)
    sync.setClock(0)
    sync.setBeat(0)
    sync.setStep(0)
    sync.setReset(0)
    sync.setChaoticDetune(0)
    sync.setHarmonicShift(0)
    # ... Set other data
    
    # Start sending data
    sync.startSending(interval_ms=0.02) # or any other suitable interval based on your application