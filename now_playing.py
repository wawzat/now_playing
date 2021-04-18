# Get currently playing track from Spotify
# James S. Lucas - 20200808

import RPi.GPIO as GPIO
#from datetime import date
#import re
import config
import sys
import datetime
from operator import itemgetter
from smbus import SMBus
from time import sleep
import statistics
from random import randint
#import re
from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT, TINY_FONT, SINCLAIR_FONT, LCD_FONT
import spotipy
import spotipy.util as util
import spotipy.oauth2 as oauth2

scope = "user-library-read user-read-playback-state user-read-currently-playing"

pwr_pin = 27

GPIO.setmode(GPIO.BCM)
GPIO.setup(pwr_pin, GPIO.OUT)
GPIO.output(pwr_pin, GPIO.LOW)


# LED Matrix Arduino I2C address
addr_led = 0x06

bus = SMBus(1)

num_i2c_errors = 0
last_i2c_error_time = datetime.datetime.now()


def i2c_error_tracker():
    global last_i2c_error_time
    global num_i2c_errors
    global pwr_pin
    duration_since_last_error = datetime.datetime.now() - last_i2c_error_time
    last_i2c_error_time = datetime.datetime.now()
    if duration_since_last_error.total_seconds() <= 2:
        num_i2c_errors += 1
        print(str(num_i2c_errors))
    elif duration_since_last_error.total_seconds() > 2:
        num_i2c_errors = 0
    if num_i2c_errors > 2:
        num_i2c_errors = 0
        #GPIO.setmode(GPIO.BCM)
        #GPIO.setup(pwr_pin, GPIO.OUT)
        GPIO.output(pwr_pin, GPIO.LOW)
        sleep(2)
        GPIO.output(pwr_pin, GPIO.HIGH)
        sleep(4)
    return


def StringToBytes(src): 
    '''Function converts a string to an array of bytes'''
    converted = [] 
    for b in src: 
        converted.append(ord(b)) 
        #print(converted)
    return converted


def write_matrix(msg, display_num, led_write_time):
    '''Function writes the command string to the LED Arduino'''
    try:
        byteValue = StringToBytes(msg)
        num_chars = len(byteValue)
        num_whole_blocks, chars_in_last_block = divmod(num_chars, 30)
        if chars_in_last_block > 0:
            num_blocks = num_whole_blocks + 1
        else:
             num_blocks = num_whole_blocks
        for b in range(num_blocks):
            if b <= (num_blocks - 2):
                #rem_chars = num_chars - ((b + 1) * 30)
                strt_range = b * 30
                end_range = strt_range + 30
                msg = byteValue[strt_range : end_range]
                bus.write_i2c_block_data(addr_led, 0x01, msg)
                sleep(.0005)
            else:
                #rem_chars = 0
                strt_range = b * 30
                end_range = num_chars
                msg = byteValue[strt_range : end_range]
                msg.append(ord(display_num))
                print(str(strt_range) + "/" + str(end_range) + "/" + str(len(msg)))
                bus.write_i2c_block_data(addr_led, 0x02, msg)
                led_write_time = datetime.datetime.now()
                sleep(.0005)
        return led_write_time
    except OSError as e:
        #led_write_time = datetime.datetime.now()
        print("LED Matrix I2C Communication Error")
        print(" ")
        i2c_error_tracker()
        return led_write_time
        pass


def spotify_authenticate():
    token = util.prompt_for_user_token(
        config.USERNAME,
        scope,
        client_id=config.SPOTIPY_CLIENT_ID,
        client_secret=config.SPOTIPY_CLIENT_SECRET,
        redirect_uri='http://localhost:8080'
        )
    return token


def get_track(token):
    if token:
        sp = spotipy.Spotify(auth=token)
        results = sp.current_user_playing_track()
        #json_formatted_str = json.dumps(results, indent=2)
        #print(json_formatted_str)
        artist_name = results['item']['album']['artists'][0]['name']
        track_name = results['item']['name']
        album_name = results['item']['album']['name']
        output_string = f"{artist_name} - {track_name} - {album_name}"
        #print(output_string)
        return track_name

# Main
try:
    led_write_time_2 = 0
    #GPIO.output(pwr_pin, GPIO.HIGH)
    sleep(4)
    token = spotify_authenticate()
    while True:
        track_name = "X"
        #track_name = get_track(token)
        print(track_name)
        led_write_time_2 = write_matrix(track_name, "0", led_write_time_2)
        sleep(15)
except KeyboardInterrupt:
    print(" ")
    print("End by Ctrl-C")
    sleep(3)
    GPIO.output(pwr_pin, GPIO.LOW)
    sleep(.5)
    GPIO.cleanup()
    sleep(1)
    exit()