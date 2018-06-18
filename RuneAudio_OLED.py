#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Title        : RuneAudio_OLED.py
Author       : zzeromin, member of Raspberrypi Village and Tentacle Team
Creation Date: Apr 30, 2017
Blog         : http://rasplay.org, http://forums.rasplay.org/
Github       : https://github.com/rasplay, https://github.com/zzeromin
Cafe         : http://cafe.naver.com/raspigamer
Thanks to    : smyani
Free and open for all to use. But put credit where credit is due.

reference    :
 https://brunch.co.kr/@gogamza/6
 https://github.com/haven-jeon/piAu_volumio
 http://blog.naver.com/kjnam100/220805352857
 https://pypi.python.org/pypi/Pillow/2.1.0

 installed python package: python2-pip, i2c-tools, python-imaging, python-mpd2, gcc
 This code edited for rpi2 runeaudio by zzeromin

install      :
pacman -Syy
pacman -S python2-pip
pacman -S gcc
pacman -S python2-imaging
pip install python-mpd2
git clone https://github.com/adafruit/Adafruit_Python_GPIO.git
git clone https://github.com/adafruit/Adafruit_Python_SSD1306.git
git clone https://github.com/zzeromin/RuneAudio-OLED.git
"""

import time
import os
from sys import exit
from subprocess import *
from time import *
from datetime import datetime
#import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
#import Image
#import ImageDraw
#import ImageFont

from mpd import MPDClient, MPDError, CommandError
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

# Raspberry Pi pin configuration:
RST = 24
# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0

# 128x64 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)


class PollerError(Exception):
    """Fatal error in poller."""


class MPDPoller(object):
    def __init__(self, host="localhost", port="6600", password=None):
        self._host = host
        self._port = port
        self._password = password
        self._client = MPDClient()

    def connect(self):
        try:
            self._client.connect(self._host, self._port)
        # Catch socket errors
        except IOError as err:
            errno, strerror = err
            raise PollerError("Could not connect to '%s': %s" %
                              (self._host, strerror))

        # Catch all other possible errors
        # ConnectionError and ProtocolError are always fatal.  Others may not
        # be, but we don't know how to handle them here, so treat them as if
        # they are instead of ignoring them.
        except MPDError as e:
            raise PollerError("Could not connect to '%s': %s" %
                              (self._host, e))

        if self._password:
            try:
                self._client.password(self._password)

            # Catch errors with the password command (e.g., wrong password)
            except CommandError as e:
                raise PollerError("Could not connect to '%s': "
                                  "password commmand failed: %s" %
                                  (self._host, e))

            # Catch all other possible errors
            except (MPDError, IOError) as e:
                raise PollerError("Could not connect to '%s': "
                                  "error with password command: %s" %
                                  (self._host, e))

    def disconnect(self):
        # Try to tell MPD we're closing the connection first
        try:
            self._client.close()

        # If that fails, don't worry, just ignore it and disconnect
        except (MPDError, IOError):
            pass

        try:
            self._client.disconnect()

        # Disconnecting failed, so use a new client object instead
        # This should never happen.  If it does, something is seriously broken,
        # and the client object shouldn't be trusted to be re-used.
        except (MPDError, IOError):
            self._client = MPDClient()

    def poll(self):
        try:
            song = self._client.currentsong()
            stats = self._client.status()

            if stats['state'] == 'stop':
                return(None)

            if 'artist' not in song:
                artist = song['name']
            else:
                artist = song['artist']

            if 'title' not in song:
                title = ""
            else:
                title = song['title']

            song_info = ""

            if 'audio' not in stats:
                audio = ""
            else:
                frequency = stats['audio'].split(':')[0]
                z, f = divmod(int(frequency), 1000)
                if (f == 0): frequency = str(z) + " kHz"
                else: frequency = str(float(frequency) / 1000) + "kHz"
                song_info += stats['audio'].split(':')[1] + "bit " + frequency

            bitrate = stats['bitrate']
            song_info += " " + stats['bitrate'] + "kbps"

#            total_time = song['time']
            songplayed = stats['elapsed']
            m, s = divmod(float(songplayed), 60)
#            m, s = divmod(float(elapsed_time), 60)
            h, m = divmod(m, 60)

            vol = stats['volume']


        # Couldn't get the current song, so try reconnecting and retrying
        except (MPDError, IOError):
            # No error handling required here
            # Our disconnect function catches all exceptions, and therefore
            # should never raise any.
            self.disconnect()

            try:
                self.connect()

            # Reconnecting failed
            except PollerError as e:
                raise PollerError("Reconnecting failed: %s" % e)

            try:
                song = self._client.currentsong()

            # Failed again, just give up
            except (MPDError, IOError) as e:
                raise PollerError("Couldn't retrieve current song: %s" % e)

        # Hurray!  We got the current song without any errors!
#        print(song)
#        print(songplayed)
#        print(song_info)
#        print(audio)
        eltime = "%d:%02d:%02d" % (h, m, s)
        return({'artist': artist, 'title': title, 'eltime': eltime, 'volume': int(vol), 'song_info': song_info})

def run_cmd(cmd):
    # runs whatever is in the cmd variable in the terminal
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.communicate()[0]
    return output

def get_ip_address(cmd, cmdeth):
    # ip & date information
    ipaddr = run_cmd(cmd)

    # selection of wlan or eth address
    count = len(ipaddr)
    if count == 0 :
        ipaddr = run_cmd(cmdeth)
    return ipaddr

def main():

    # Initialize library.
    disp.begin()

    # Clear display.
    disp.clear()
    disp.display()

    # Create blank image for drawing.
    # Make sure to create image with mode '1' for 1-bit color.
    width = disp.width
    height = disp.height
    image = Image.new('1', (width, height))

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    # Draw some shapes.
    # First define some constants to allow easy resizing of shapes.
    padding = 2
    shape_width = 20
    top = padding
    bottom = height-padding
    x = padding
    # Load default font.
    poller = MPDPoller()
    poller.connect()
    font_art = ImageFont.truetype('/root/RuneAudio_OLED/NanumGothic.ttf', 13)
    font_tit = ImageFont.truetype('/root/RuneAudio_OLED/NanumGothic.ttf', 13)
    font_info = ImageFont.truetype('/root/RuneAudio_OLED/NotoSansUI-Regular.ttf', 12)
    #get ip address of eth0 connection
    cmdeth = "ip addr show eth0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1"
    #get ip address of wlan0 connection
    cmd = "ip addr show wlan0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1"
    #cmd = "ip addr show wlan1 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1"

    #get ip address of eth0 connection    
    ipaddr = get_ip_address(cmd, cmdeth)

    while True:
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        status = poller.poll()
        if status is None:
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            msg1 = "Welcome RuneAudio"
            msg2 = "RAS Yolo Pi"
            ipaddr = get_ip_address(cmd, cmdeth)
            draw.text((0, top), unicode(msg1).center(1,' '), font=font_tit, fill=255)
            draw.text((0, top+15), unicode(msg2).center(2, ' '), font=font_tit, fill=255)
            draw.text((0, top+30), datetime.now().strftime( "%b %d %H:%M:%S" ), font=font_info, fill=255)
            draw.text((0, top+45), "IP " + ipaddr, font=font_info, fill=255)
            disp.image(image)
            disp.display()
            continue

        artist = status['artist']
        title = status['title']
        eltime = status['eltime']
        vol = status['volume']
        song_info = status['song_info']
        print eltime

        div_vol = vol // 10
        vol_str = ""
        for i in range(div_vol):
            vol_str = vol_str + '+'
        for i in range(10 - div_vol):
            vol_str = vol_str + '-'

        titleLength = len(title)
        txtFind = title[0]
        if txtFind.isalpha():
            titleLine3 = 40
            titleLine2 = 22
            titleIndex1 = 17
            titleIndex2 = 35
        else:
            titleLine3 = 60
            titleLine2 = 24
            titleIndex1 = 16
            titleIndex2 = 32

        print (titleLength, txtFind.isalpha())

        title = unicode(title)

        if titleLength > titleLine3:
            draw.text((0, top), unicode(artist), font=font_art, fill=255)
            draw.text((0, top+15), title[0:titleIndex1], font=font_tit, fill=255)
            draw.text((0, top+31), title[titleIndex1:titleIndex2], font=font_tit, fill=255)
            draw.text((0, top+46), title[titleIndex2:60], font=font_tit, fill=255)

        elif titleLength > titleLine2:
            draw.text((0, top), unicode(artist), font=font_art, fill=255)
            draw.text((0, top+15), title[0:titleIndex1], font=font_tit, fill=255)
            draw.text((0, top+32), title[titleIndex1:titleIndex2], font=font_tit, fill=255)
            draw.text((0, top+46), eltime, font=font_info, fill=255)
            draw.text((90, top+46), "Vol " + str(vol), font=font_info, fill=255)
#            draw.text((0, top+45), song_info, font=font_info, fill=255)

        else:
            draw.text((0, top), unicode(artist), font=font_art, fill=255)
            draw.text((0, top+17), unicode(title), font=font_tit, fill=255)
            draw.text((0, top+32), eltime, font=font_info, fill=255)
            draw.text((90, top+32), "Vol " + str(vol), font=font_info, fill=255)
            draw.text((0, top+45), song_info, font=font_info, fill=255)

        disp.image(image)
        disp.display()
        sleep(1)


if __name__ == "__main__":
    import sys

    try:
        main()

    # Catch fatal poller errors
    except PollerError as e:
        sys.stderr.write("Fatal poller error: %s" % e)
        sys.exit(1)

    # Catch all other non-exit errors
    except Exception as e:
        sys.stderr.write("Unexpected exception: %s" % e)
        sys.exit(1)

    # Catch the remaining exit errors
    except:
        sys.exit(0)
