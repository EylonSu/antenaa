'''
    Differential turret control demo for Arduino-based turret using serial communication.
    Protocol uses serial (USB) connection with 9600 baud rate. Commands are sent as text strings, and responses are received as text strings:
    - INIT: Initialize the turret to pan=90, tilt=90.
    - MOVE,<pan>,<tilt>: Move the turret to specified pan and tilt angles.
        NOTE: 
            pan limits = 5 to 175 degrees
            tilt limits = 60 to 160 degrees
    - GET: Retrieve the current position of the turret.

    Every command returns OK:<pan>,<tilt> if successful, or LINIT if pan/tilt is out of limits.

    Ver 0.1 
    6.10.2026 YDT 
'''



import sys
import time

try:
    import serial
except ImportError:
    print("pyserial is required. Install it with: pip install pyserial")
    sys.exit(1)


PORT = "COM8"  # update to the correct serial port 
BAUD_RATE = 9600


def read_line(ser):
    line = ser.readline()
    if not line:
        return ""
    return line.decode("utf-8", errors="ignore").strip()


def send_command(ser, command):
    print(f">> {command}")
    ser.write((command + "\n").encode("utf-8"))
    ser.flush()
    time.sleep(0.25)

    response = ""
    deadline = time.time() + 2.0
    while time.time() < deadline:
        line = read_line(ser)
        if line:
            response = line
            break
        time.sleep(0.05)

    if response == "":
        print("<< <no response>")
        return ""

    print(f"<< {response}")
    return response


def main():
    print(f"Using serial port: {PORT} at {BAUD_RATE} baud")

    with serial.Serial(PORT, BAUD_RATE, timeout=1) as ser:
        time.sleep(2)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        #test INIT command
        send_command(ser, "INIT")

        try:
            pan = int(input("Enter pan angle: ").strip())
            tilt = int(input("Enter tilt angle: ").strip())
        except ValueError:
            print("Invalid input. Please enter integer angles.")
            sys.exit(1)

        #test MOVE command
        send_command(ser, f"MOVE,{pan},{tilt}")
        #test GET command
        send_command(ser, "GET")


if __name__ == "__main__":
    main()
