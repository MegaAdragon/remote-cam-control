import time

from pad_display import PadDisplay

try:
    import touchphat
except (ImportError, OSError):
    print("Touch PHAT not supported")
    import touchphat_mock as touchphat

pads = ['Back', 'A', 'B', 'C', 'D', 'Enter']


class PadHandler:
    _display: PadDisplay
    def __init__(self, display):
        self._selectedPad = None
        self._last_blink = 0
        self._toggle = False
        self._start_blink = False
        self._display = display
        self._on_stored_pos = None
        pass

    def startup(self):
        self._all_off()
        for pad in pads:
            self.set_pad(pad, True)
            time.sleep(0.1)
        time.sleep(0.2)
        for pad in pads[::-1]:
            self.set_pad(pad, False)
            time.sleep(0.1)

    def confirm(self, pad):
        # fast blink
        for i in range(0, 5):
            self.set_pad(pad, True)
            time.sleep(0.1)
            self.set_pad(pad, False)
            time.sleep(0.1)

    def set_selected(self, key):
        self.stop_blink()
        self._selectedPad = key

    def start_blink(self):
        if self._start_blink:
            return
        self._toggle_selected()
        self._start_blink = True

    def stop_blink(self):
        if not self._start_blink:
            return
        self._start_blink = False
        self._toggle = False
        self.set_pad(self._selectedPad, self._toggle)
        self._selectedPad = None

    def set_pad(self, pad, state):
        touchphat.set_led(pad, state)
        if self._display is not None:
            self._display.set_pad(pad, state)

    def on_position(self, key):
        if key is not None:
            self._on_stored_pos = key
            self.set_pad(self._on_stored_pos, True)  # currently on this position

        if key is None and self._on_stored_pos is not None:
            self.set_pad(self._on_stored_pos, False)
            self._on_stored_pos = key
            return

    def _toggle_selected(self):
        self.set_pad(self._selectedPad, self._toggle)
        self._toggle = not self._toggle
        self._last_blink = time.time()

    def _all_off(self):
        touchphat.all_off()
        if self._display is not None:
            self._display.all_off()

    def process(self):
        if self._start_blink and time.time() - self._last_blink > 0.3:
            self._toggle_selected()
