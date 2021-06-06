from PIL import Image
from PIL import ImageFont

from joystick import Joystick

try:
    from luma.core.render import canvas
except (ImportError, OSError):
    pass

pads = [
    {'key': 'A', 'box': (0, 0, 60, 30), 'state': False},
    {'key': 'B', 'box': (63, 0, 123, 30), 'state': False},
    {'key': 'C', 'box': (0, 33, 60, 63), 'state': False},
    {'key': 'D', 'box': (63, 33, 123, 63), 'state': False}
]

roboto_bold = ImageFont.truetype('font/RobotoMono-Bold.ttf', 25)


class PadDisplay:
    def __init__(self, device):
        self._device = device
        if self._device is None:
            return

        logo = Image.open('dragonfly.png').convert("RGBA")
        background = Image.new("RGBA", self._device.size, "black")
        pos = ((self._device.width - logo.width) // 2, 0)
        background.paste(logo, pos)
        self._device.display(background.convert(self._device.mode))

    def _update(self):
        if self._device is None:
            return

        with canvas(self._device) as draw:
            for p in pads:
                if p['state']:
                    draw.rectangle(p['box'], outline='white', fill='white')
                    draw.text((p['box'][0] + 20, p['box'][1]), p['key'], fill='black', font=roboto_bold)
                else:
                    draw.rectangle(p['box'], outline='white', fill='black')
                    draw.text((p['box'][0] + 20, p['box'][1]), p['key'], fill='white', font=roboto_bold)

    def all_off(self):
        for p in pads:
            p['state'] = False
        self._update()

    def all_on(self):
        for p in pads:
            p['state'] = True
        self._update()

    def _get_pad(self, pad):
        for p in pads:
            if p['key'] is pad:
                return p
        return None

    def set_pad(self, pad, state):
        p = self._get_pad(pad)
        if p is None:
            return
        p['state'] = state
        self._update()
