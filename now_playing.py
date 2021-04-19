# Get currently playing track from Spotify
# James S. Lucas - 20210418

import RPi.GPIO as GPIO
#from datetime import date
import config
#import sys
import datetime
#from operator import itemgetter
from smbus import SMBus
import atexit
from time import sleep
#import statistics
from random import randint
import spotipy
import spotipy.util as util
#import spotipy.oauth2 as oauth2
import json

scope = "user-library-read user-read-playback-state user-read-currently-playing"

pwr_pin = 27

GPIO.setmode(GPIO.BCM)
GPIO.setup(pwr_pin, GPIO.OUT)
GPIO.output(pwr_pin, GPIO.LOW)

# Stepper Arduino I2C address
addr_stepper = 0x08

# LED Matrix Arduino I2C address
addr_led = 0x06

bus = SMBus(1)

num_i2c_errors = 0
last_i2c_error_time = datetime.datetime.now()


def exit_function():
    '''Function disconnects stream and resets motor positions to zero. 
    Called by exception handler'''
    print(" ")
    print("End by atexit")
    global pwr_pin
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pwr_pin, GPIO.OUT)
    indicator_pos_1 = 0
    indicator_pos_2 = 0
    write_time = datetime.datetime.now()
    sleep(1)
    write_time = move_stepper(str(indicator_pos_1), str(indicator_pos_2), write_time)
    sleep(4)
    GPIO.output(pwr_pin, GPIO.LOW)
    sleep(1)
    GPIO.cleanup()
    sleep(1)
   #system("stty echo")
    exit()


atexit.register(exit_function)


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


def writeData(motor_num, value):
    '''Function writes the command string to the  Stepper Arduino'''
    try:
        byteValue = StringToBytes(value)
        #print(byteValue)
        bus.write_i2c_block_data(addr_stepper, motor_num, byteValue)
        #sleep(.02)
    except OSError as e:
        print("Stepper I2C Communication Error")
        print(" ")
        i2c_error_tracker()
        pass


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
                #print(str(strt_range) + "/" + str(end_range) + "/" + str(len(msg)))
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


def move_stepper(indicator_pos_1, indicator_pos_2, write_time):
    '''Function prepares the command string and sends to WriteData()'''
    # Format is XYYYY where X is motor number and YYYY is 1-4 digit indicator postion
    elapsed_time = datetime.datetime.now() - write_time
    if elapsed_time.total_seconds() > .2:
        #command = indicator_pos_1
        motor_num = 0x01 
        position = indicator_pos_1
        writeData(motor_num, position)
        #print("B: " + str(indicator_pos_2))
        sleep(.00005)
        motor_num = 0x02
        position = indicator_pos_2
        writeData(motor_num, position)
        #print("T: " + str(indicator_pos_2))
        write_time = datetime.datetime.now()
    return write_time


def spotify_authenticate():
    token = util.prompt_for_user_token(
        config.USERNAME,
        scope,
        client_id=config.SPOTIPY_CLIENT_ID,
        client_secret=config.SPOTIPY_CLIENT_SECRET,
        redirect_uri='http://localhost:8080'
        )
    sp = spotipy.Spotify(auth=token)
    return sp


def get_track(sp):
    results = sp.current_user_playing_track()
    #json_formatted_str = json.dumps(results, indent=2)
    #print(json_formatted_str)
    progress_ms = results['progress_ms']
    duration_ms = results['item']['duration_ms']
    percent_complete = progress_ms / duration_ms * 100
    print("{:.1f}%".format(percent_complete))
    artist_name = results['item']['album']['artists'][0]['name']
    track_name = results['item']['name']
    album_name = results['item']['album']['name']
    album_string = f" -  {artist_name}  -  {album_name}  - "
    track_string = f" {track_name} "
    return album_string, track_string, percent_complete

# Main
try:
    led_write_time_1 = datetime.datetime.now()
    led_write_time_2 = datetime.datetime.now()
    write_time = datetime.datetime.now()
    previous_pct_complete = 0
    GPIO.output(pwr_pin, GPIO.HIGH)
    write_time = move_stepper("0", "0", write_time)
    sleep(4)
    sp = spotify_authenticate()
    while True:
        album_string, track_string, percent_complete = get_track(sp)
        pct_complete_change = percent_complete - previous_pct_complete
        if pct_complete_change < 10 or pct_complete_change > 33:
            previous_pct_complete = percent_complete
            led_write_time_1 = write_matrix(album_string, "1", led_write_time_1)
            sleep(1.5)
            led_write_time_2 = write_matrix(track_string, "0", led_write_time_2)
            print("Change: " + str(pct_complete_change))
        write_time = move_stepper("0", str(int(percent_complete * 22 + 150)), write_time)
        sleep(5)
except KeyboardInterrupt:
    print(" ")
    print("End by Ctrl-C")
    sleep(3)
    GPIO.output(pwr_pin, GPIO.LOW)
    sleep(.5)
    GPIO.cleanup()
    sleep(1)
    exit()