from PIL import Image
from PIL import ImageFont
from luma.core.render import canvas
from joystick import Joystick
import os

class CameraInfo:
    def __init__(self, id):
        self.id = id

pads = [
    {'key': 'A', 'box': (2, 0, 62, 30), 'state': False, 'stored': False},
    {'key': 'B', 'box': (65, 0, 127, 30), 'state': False, 'stored': False},
    {'key': 'C', 'box': (2, 33, 62, 63), 'state': False, 'stored': False},
    {'key': 'D', 'box': (65, 33, 127, 63), 'state': False, 'stored': False}
]

roboto_bold = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'font/RobotoMono-Bold.ttf'), 20)
roboto_small = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'font/RobotoMono-Medium.ttf'), 15)
roboto_bold_s = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'font/RobotoMono-Medium.ttf'), 12)
roboto_medium = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'font/RobotoMono-Medium.ttf'), 10)


class PadDisplay:
    def __init__(self, device):
        self._device = device
        self._need_update = True
        if self._device is None:
            return

        self._max_speed = 0.0
        self._cam = None

        logo = Image.open(os.path.join(os.path.dirname(__file__), 'dragonfly.png')).convert("RGBA")
        background = Image.new("RGBA", self._device.size, "black")
        pos = ((self._device.width - logo.width) // 2, (self._device.height - logo.height) // 2)
        background.paste(logo, pos)
        self._device.display(background.convert(self._device.mode))

    def update(self):
        if self._device is None or not self._need_update:
            return

        with canvas(self._device) as draw:
            for p in pads:
                if p['state']:
                    if p['stored']:
                        draw.rectangle(p['box'], outline='green', fill='white')
                        draw.text((p['box'][0] + 22, p['box'][1] + 3), p['key'], fill='black', font=roboto_bold)
                    else:
                        draw.rectangle(p['box'], outline='white', fill='white')
                        draw.text((p['box'][0] + 25, p['box'][1] + 7), p['key'], fill='black', font=roboto_small)
                else:
                    if p['stored']:
                        draw.rectangle(p['box'], outline='green', fill='black')
                        draw.text((p['box'][0] + 22, p['box'][1] + 3), p['key'], fill='white', font=roboto_bold)
                    else:
                        draw.rectangle(p['box'], outline='white', fill='black')
                        draw.text((p['box'][0] + 25, p['box'][1] + 7), p['key'], fill='white', font=roboto_small)

                draw.text((0, 100), "Cam {}".format(self._cam.id), fill='white', font=roboto_bold)

                draw.text((0, 130), "Max speed:", fill='white', font=roboto_bold_s)
                draw.text((75, 132), "{:>3}%".format(round(100 * self._max_speed)), fill='white', font=roboto_medium)
        self._need_update = False

    def update_status(self, cam, speed):
        cam: CameraInfo
        if cam is None:
            return

        if self._device is None:
            return

        if self._max_speed == speed and self._cam == cam:
            return

        self._max_speed = speed
        self._cam = cam
        self._update()

    def _update(self):
        self._need_update = True

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

    def pad_stored(self, pad, is_stored):
        p = self._get_pad(pad)
        if p is None:
            return
        p['stored'] = is_stored