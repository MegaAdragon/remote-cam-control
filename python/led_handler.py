import time

try:
    import touchphat
except (ImportError, OSError):
    print("Touch PHAT not supported")
    import touchphat_mock as touchphat

pads = ['Back', 'A', 'B', 'C', 'D', 'Enter']


class LedHandler:
    def __init__(self):
        self._selectedPad = None
        self._last_blink = 0
        self._toggle = False
        self._start_blink = False
        pass

    def startup(self):
        touchphat.all_off()
        for pad in pads:
            touchphat.set_led(pad, True)
            time.sleep(0.1)
        time.sleep(0.2)
        for pad in pads[::-1]:
            touchphat.set_led(pad, False)
            time.sleep(0.1)

    def confirm(self, key):
        # fast blink
        for i in range(0, 5):
            touchphat.set_led(key, True)
            time.sleep(0.1)
            touchphat.set_led(key, False)
            time.sleep(0.1)

    def set_selected(self, key):
        self.stop_blink()
        self._selectedPad = key

    def start_blink(self):
        if self._start_blink:
            return
        self._toggle_pad()
        self._start_blink = True

    def stop_blink(self):
        if not self._start_blink:
            return
        self._start_blink = False
        self._toggle = False
        touchphat.set_led(self._selectedPad, self._toggle)
        self._selectedPad = None

    def _toggle_pad(self):
        touchphat.set_led(self._selectedPad, self._toggle)
        self._toggle = not self._toggle
        self._last_blink = time.time()

    def process(self):
        if self._start_blink and time.time() - self._last_blink > 0.3:
            self._toggle_pad()
