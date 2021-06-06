from PIL import Image
from PIL import ImageFont

from joystick import Joystick

try:
    from luma.core.render import canvas
except (ImportError, OSError):
    import pygame
    screen = pygame.display.set_mode((128, 64))


class CameraInfo:
    def __init__(self, id):
        self.id = id
        self.pan = 0
        self.tilt = 0
        self.zoom = 0


class StatusDisplay:
    _joystick: Joystick

    def __init__(self, device, joystick):
        self._device = device
        self._joystick = joystick

        if self._device is None:
            return

        img_path = 'dragonfly.png'
        logo = Image.open(img_path).convert("RGBA")
        background = Image.new("RGBA", self._device.size, "black")
        pos = ((self._device.width - logo.width) // 2, 0)
        background.paste(logo, pos)
        #surface = pygame.image.fromstring(background.tobytes(), background.size, "RGBA")
        #screen.blit(surface, (0,0))
        #pygame.display.update()
        self._device.display(background.convert(self._device.mode))

    def update(self, cam):
        cam: CameraInfo
        if cam is None:
            return

        if self._device is None:
            return

        roboto_bold = ImageFont.truetype('font/RobotoMono-Bold.ttf', 20)
        roboto_bold_s = ImageFont.truetype('font/RobotoMono-Bold.ttf', 12)
        roboto_medium = ImageFont.truetype('font/RobotoMono-Medium.ttf', 10)
        with canvas(self._device) as draw:
            pos = "{:>8}"
            draw.text((0, 0), "Cam {}".format(cam.id), fill='white', font=roboto_bold)

            draw.text((0, 30), "Max speed:", fill='white', font=roboto_bold_s)
            draw.text((75, 32), "{:>3}%".format(round(100 * self._joystick.max_speed)), fill='white', font=roboto_medium)

            draw.text((0, 50), "Zoom:", fill='white', font=roboto_bold_s)
            #draw.text((40, 52), "{:>3}%".format(100), fill='white', font=roboto_medium)
            draw.text((40, 52), '-', fill='white', font=roboto_medium)

            # draw.text((0, 22), "P:", fill='white', font=roboto_bold_s)
            # draw.text((20, 24), pos.format(cam.pan), fill='white', font=roboto_medium)
            # draw.text((0, 36), "T:", fill='white', font=roboto_bold_s)
            # draw.text((20, 38), pos.format(cam.tilt), fill='white', font=roboto_medium)
            # draw.text((0, 50), "Z:", fill='white', font=roboto_bold_s)
            # draw.text((20, 52), pos.format(cam.zoom), fill='white', font=roboto_medium)
            #
            # draw.text((88, 22), "Speed:", fill='white', font=roboto_bold_s)
            # draw.text((88, 38), "{:>3}%".format(100), fill='white', font=roboto_medium)


