# python (paho)
# subscribing to env/tele/sonoff_755F13/STATE
# if between 1900h and 0700h

#  if power 1 and power2 = ON (doors closed): blink green on every status message received
#  if either power = OFF: steady red
#  if no status received for 20 min, blink red

# else off

import paho.mqtt.client as mqtt
import ssl
import datetime, threading, time
import RPi.GPIO as GPIO     #import RPi.GPIO module
from time import sleep

# initialize LEDs
#################
LED_GREEN = 38
LED_RED   = 40      #pin no. as per BOARD, GPIO21 as per BCM
GPIO.setwarnings(False)     #disable warnings
GPIO.setmode(GPIO.BOARD)    #set pin numbering format
GPIO.setup(LED_GREEN, GPIO.OUT)
GPIO.setup(LED_RED, GPIO.OUT)
GPIO.output(LED_RED, GPIO.LOW) # Turn off
ledredstate=False
GPIO.output(LED_GREEN, GPIO.LOW) # Turn off
ledgreenstate=False

shine = True
cur_hour = datetime.datetime.today().hour
last_message = time.time()
next_call = time.time()
next_blink = time.time()
errorstate = False

##### TEST  
last_message = 0
#####  END TEST


def blink_red():
    global next_blink
    global ledredstate
#    print ("ledredstate: "+str(ledredstate))
#    print ("errorstate: "+str(errorstate))

    ledredstate = not ledredstate
    if ledredstate:
        GPIO.output(LED_RED, GPIO.HIGH) # Toggle
    else:
        GPIO.output(LED_RED, GPIO.LOW) # Toggle

    if errorstate:
        next_blink = next_blink+1
        threading.Timer( next_blink - time.time(), blink_red ).start()

def watchdog():
  global next_call
  print datetime.datetime.now()
  global cur_hour 
  global shine
  global errorstate

  cur_hour = datetime.datetime.today().hour

  #determine if we have to signal door status at all
  if ((cur_hour > 17) or (cur_hour < 9)):
    print("Nighttime - time to shine: "+str(cur_hour))
    shine=True
  else:
    print("Sunshine is enough: "+str(cur_hour))
    shine=False
  
  # determine whether we're in error state and have to signal that
  if ((time.time() - last_message) > 1200):
    if not errorstate: # only run the below if error state wasn't already set
        errorstate = True # we havn't received a message, so we're in errorstate
        print("warning! Last message received at "+ str(last_message))
        blink_red()
  next_call = next_call+120
  threading.Timer( next_call - time.time(), watchdog ).start()


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("env/tele/sonoff_755F13/STATE")
    client.subscribe("env/stat/sonoff_755F13/POWER1")
    client.subscribe("env/stat/sonoff_755F13/POWER2")
    client.subscribe("test")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global last_message
    global errorstate
    errorstate = False # we have received a new message, so cancel error state
    last_message = time.time()
    print(str(last_message) +" "+ msg.topic+" "+str(msg.payload))
    #cancel red blink (just in case we've been in an error condition before)
    if (shine):
        print("It's dark outside")
        if ("OFF" in msg.payload):
            print("a door is open - turn red LED on")
            GPIO.output(LED_RED, GPIO.HIGH) 
        else:
            print("all seems fine. blink green once")
            GPIO.output(LED_RED, GPIO.LOW) 
            GPIO.output(LED_GREEN, GPIO.HIGH)
            sleep(1)                  # Sleep for 1 second
            GPIO.output(LED_GREEN, GPIO.LOW)



client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set("root", "xxx")
client.tls_set(ca_certs="ca.crt.pem", certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLSv1_1, ciphers=None)
client.tls_insecure_set(True)

client.connect("192.168.2.5", 8883, 60)

watchdog()

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
