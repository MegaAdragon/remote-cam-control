from PIL import Image
from PIL import ImageFont
import os
from luma.core.render import canvas
from joystick import Joystick

roboto_bold = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'font/RobotoMono-Bold.ttf'), 20)
roboto_bold_s = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'font/RobotoMono-Bold.ttf'), 12)
roboto_medium = ImageFont.truetype(os.path.join(os.path.dirname(__file__), 'font/RobotoMono-Medium.ttf'), 10)

class CameraInfo:
    def __init__(self, id):
        self.id = id


class StatusDisplay:
    _joystick: Joystick

    def __init__(self, device):
        self._device = device
        self._max_speed = 0.0
        self._cam = None

        if self._device is None:
            return

    def update(self, cam, speed):
        cam: CameraInfo
        if cam is None:
            return

        if self._device is None:
            return

        if self._max_speed == speed and self._cam == cam:
            return

        self._max_speed = speed
        self._cam = cam

        with canvas(self._device) as draw:
            draw.text((0, 100), "Cam {}".format(cam.id), fill='white', font=roboto_bold)

            draw.text((0, 130), "Max speed:", fill='white', font=roboto_bold_s)
            draw.text((75, 132), "{:>3}%".format(round(100 * speed)), fill='white', font=roboto_medium)

            #draw.text((0, 50), "Zoom:", fill='white', font=roboto_bold_s)
            #draw.text((40, 52), "{:>3}%".format(100), fill='white', font=roboto_medium)
            #draw.text((40, 52), '-', fill='white', font=roboto_medium)

            # draw.text((0, 22), "P:", fill='white', font=roboto_bold_s)
            # draw.text((20, 24), pos.format(cam.pan), fill='white', font=roboto_medium)
            # draw.text((0, 36), "T:", fill='white', font=roboto_bold_s)
            # draw.text((20, 38), pos.format(cam.tilt), fill='white', font=roboto_medium)
            # draw.text((0, 50), "Z:", fill='white', font=roboto_bold_s)
            # draw.text((20, 52), pos.format(cam.zoom), fill='white', font=roboto_medium)
            #
            # draw.text((88, 22), "Speed:", fill='white', font=roboto_bold_s)
            # draw.text((88, 38), "{:>3}%".format(100), fill='white', font=roboto_medium)


