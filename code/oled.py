#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Kai Xi 郗锴, Sheng Lyu 吕晟, Taylor Lee 李远朝 & Xose Pérez"
__copyright__ = "Copyright 2022 RAKWireless"
__license__ = "MIT"
__maintainer__ = "RAKWireless"
__email__ = "xose.perez@rakwireless.com"

import sys
import threading
import netifaces
import psutil
import re
import subprocess
import requests
import json
import time

import board
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

WIDTH = 128
HEIGHT = 64
BORDER = 5
DELAY = 5
AVAIL_WIDTH = 120
AVAIL_HIGH = 40
MAX_BUCKET_COUNT = 36
START_WIDTH = 5

# -----------------------------------------------------------------------------
# Pages
# -----------------------------------------------------------------------------

def network(draw):
    
    # Create blank image for drawing
    font = ImageFont.load_default()
    (font_width, font_height) = font.getsize("H")
    y = 0
    
    draw.rectangle((0, 0, oled.width - 1, font_height - 1), outline=255, fill=255)
    draw.text((0, y), "NETWORK", font=font, fill=0)
    y += font_height

    # Get IP
    ifaces = netifaces.interfaces()
    pattern = "^bond.*|^[ewr].*|^br.*|^lt.*|^umts.*|^lan.*"

    # Get bridge interfaces created by docker 
    p = subprocess.run('docker network ls -f driver=bridge --format "br-{{.ID}}"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    br_docker_ifaces = p.stdout.decode()
    
    for iface in ifaces:
        # Match only interface names starting with e (Ethernet), br (bridge), w (wireless), r (some Ralink drivers use>
        # Get rid off of the br interface created by docker
        if re.match(pattern, iface) and iface not in br_docker_ifaces:
            ifaddresses = netifaces.ifaddresses(iface)
            ipv4_addresses = ifaddresses.get(netifaces.AF_INET)
            if ipv4_addresses:
                for address in ipv4_addresses:
                    addr = address['addr']
                    draw.text((0, y), ("%s: %s" % (iface[:6], addr)), font=font, fill=255)
                    y += font_height

    return True

def stats(draw):
    
    # Create blank image for drawing
    font = ImageFont.load_default()
    (font_width, font_height) = font.getsize("H")
    y = 0
    
    draw.rectangle((0, 0, oled.width - 1, font_height - 1), outline=255, fill=255)
    draw.text((0, y), "STATS", font=font, fill=0)
    y += font_height

    # Get cpu percent
    cpu = psutil.cpu_percent(None)
    draw.text((0, y), ("CPU: %.1f%%" % cpu), font=font, fill=255)
    y += font_height
 
    # Get free memory percent
    memory = 100 - psutil.virtual_memory().percent
    draw.text((0, y), ("Free memory: %.1f%%" % memory), font=font, fill=255)
    y += font_height

    # Get temperature
    p = subprocess.run('vcgencmd measure_temp 2> /dev/null | sed \'s/temp=//\'', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    draw.text((0, y), ("Temperature: %s" % p.stdout.decode()), font=font, fill=255)
    y += font_height

    # Get uptime
    p = subprocess.run('uptime -p | sed \'s/up //\' | sed \'s/ hours*/h/\' | sed \'s/ minutes*/m/\' | sed \'s/,//\'', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    draw.text((0, y), ("Uptime: %s" % p.stdout.decode()), font=font, fill=255)
    y += font_height

    return True

def lorawan(draw):

    font = ImageFont.load_default()
    (font_width, font_height) = font.getsize("H")

    # require bucket data from log2api
    url = "http://127.0.0.1:8888/api/metrics"
    try:
        res = requests.get(url)
    except:
        return False

    bucket_data = json.loads(res.text)
    bucket_count = min(bucket_data.get('bucket_count'), MAX_BUCKET_COUNT)
    bucket_size = bucket_data.get('bucket_size')
    buckets = bucket_data['buckets']
    totals = bucket_data['totals']
    rx_max = int(totals['rx_max'])
    if rx_max == 0:
        return False

    # calculate the width of each bucket and real bucket count displayed.
    bucket_width = int(AVAIL_WIDTH / bucket_count) - 1

    # calculate the pixel of every packet
    unit = float(AVAIL_HIGH / rx_max)

    # draw y-axis, the packet count of each bucket.
    draw.line((3, 0, 3, 60), width=1, fill=128)
    draw.line((3, 0, 0, 3), width=1, fill=128)
    draw.line((3, 0, 6, 3), width=1, fill=128)

    # draw x-axis, the time.
    draw.line((3, 60, 127, 60), width=1, fill=128)
    draw.line((124, 63, 127, 60), width=1, fill=128)
    draw.line((124, 57, 127, 60), width=1, fill=128)
    draw.text((121, 45), "t", font=font, fill=255)

    # draw every bucket 
    for i in range(bucket_count):
        tmp = buckets.get(str(i), {'rx': 0, 'tx': 0})
        rx = tmp['rx']
        draw.rectangle(
            (START_WIDTH + i * bucket_width, 60, START_WIDTH + (i + 1) * bucket_width - 2, 60 - int(rx * unit) - 1), 
            outline=1, 
            fill=1
        )
    
    # draw top line
    top = "LAST %dm, MAX:%d"%(bucket_count * bucket_size / 60, rx_max)
    draw.text((10, 0), top, font=font, fill=255)
    
    return True

# -----------------------------------------------------------------------------
# State machine
# -----------------------------------------------------------------------------

def show_page(page):

    # Prepare canvas
    image = Image.new("1", (oled.width, oled.height))
    draw = ImageDraw.Draw(image)

    response = False
    while not response:
        
        # Show page (returns false if the page should not be displayed)
        response = pages[page](draw)
        
        # Update next page
        # We are not showing page 0 (intro) again
        page = page + 1
        if page >= len(pages):
            page = 0


    # Update screen
    oled.fill(0)
    oled.image(image)
    oled.show()
    
    # Return pointer to next page
    return page

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------

class RepeatTimer(threading.Timer):
    page = 0
    def run(self):
        while not self.finished.wait(self.interval):
            self.page = self.function(self.page, *self.args, **self.kwargs)

try:
    i2c = board.I2C()
    time.sleep(1)
    oled = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c)
except Exception:
    print("OLED screen not found")
    sys.exit()

pages = [network, stats, lorawan]
show_page(0)
timer = RepeatTimer(DELAY, show_page)
timer.start()

