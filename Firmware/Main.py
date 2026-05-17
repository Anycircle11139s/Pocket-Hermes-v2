"""
Hermes - Hack Club Project
esp32 s3 (Seeed XIAO) Firmware
"""

from machine import I2C, Pin
import ssd1306
import time
import struct

# ── Pin definitions (from schematic) ─────────────────────────────────────────
I2C_SDA  = 6   # XIAO D4 / PA8
I2C_SCL  = 7   # XIAO D5 / PA9
ENC_A    = 26  # XIAO D0 / PA02
ENC_B    = 27  # XIAO D1 / PA4
ENC_SW   = 28  # XIAO D2 / PA10

# ── LM75AD constants ──────────────────────────────────────────────────────────
LM75_ADDR     = 0x48  # A0=A1=A2=GND
LM75_TEMP_REG = 0x00

# ── OLED constants ────────────────────────────────────────────────────────────
OLED_WIDTH  = 128
OLED_HEIGHT = 32
OLED_ADDR   = 0x3C

# ── Counter ───────────────────────────────────────────────────────────────────
counter = 0

# ── Rotary encoder state ──────────────────────────────────────────────────────
enc_last_a  = 1
enc_last_b  = 1
enc_sw_last = 1

# ── Initialise hardware ───────────────────────────────────────────────────────
i2c = I2C(1, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=400_000)

oled = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_ADDR)
oled.write_cmd(0xA0)  # flip horizontally
oled.write_cmd(0xC0)  # flip vertically

enc_pin_a  = Pin(ENC_A,  Pin.IN, Pin.PULL_UP)
enc_pin_b  = Pin(ENC_B,  Pin.IN, Pin.PULL_UP)
enc_pin_sw = Pin(ENC_SW, Pin.IN, Pin.PULL_UP)


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_lm75() -> float:
    """Read temperature from LM75AD, return value in C."""
    i2c.writeto(LM75_ADDR, bytes([LM75_TEMP_REG]))
    raw = i2c.readfrom(LM75_ADDR, 2)
    value = struct.unpack(">H", raw)[0] >> 5
    if value & 0x400:
        value -= 0x800
    return value * 0.125


def read_encoder() -> int:
    """
    Decode one quadrature step.
    Returns +1 (CW), -1 (CCW), or 0 (no change).
    """
    global enc_last_a, enc_last_b

    a = enc_pin_a.value()
    b = enc_pin_b.value()

    direction = 0
    if a != enc_last_a:
        if a == 0 and b == 1:
            direction = +1
        elif a == 0 and b == 0:
            direction = -1

    enc_last_a = a
    enc_last_b = b
    return direction


def draw_screen(temp_c: float) -> None:
    """Render temperature and counter to the OLED."""
    temp_f = temp_c * 9.0 / 5.0 + 32.0

    oled.fill(0)

    # ── Temperature ──
    oled.text("Temp:", 0, 0)
    oled.text("{:.1f}C  {:.1f}F".format(temp_c, temp_f), 0, 10)

    # ── Counter ──
    oled.text("Count: {}".format(counter), 0, 22)

    oled.show()


# ── Boot splash ───────────────────────────────────────────────────────────────
oled.fill(0)
oled.text("  Hermes", 20, 4)
oled.text("Hack Club", 20, 16)
oled.show()
time.sleep(1.5)

# ── Main loop ─────────────────────────────────────────────────────────────────
last_temp_read = 0
temp_c         = 0.0

while True:
    now = time.ticks_ms()

    # Read temperature every 1 s
    if time.ticks_diff(now, last_temp_read) >= 1000:
        try:
            temp_c = read_lm75()
        except OSError:
            temp_c = float("nan")
        last_temp_read = now
        draw_screen(temp_c)

    # Poll encoder
    delta = read_encoder()
    if delta != 0:
        counter += delta
        draw_screen(temp_c)

    time.sleep_ms(2)
