#!/usr/bin/env python3

import time
import glob
import math

from collections import deque

from evdev import (
    InputDevice,
    UInput,
    ecodes as e,
)


# ======================================================
# DEVICE
# ======================================================

DEVICE_NAME_PREFIX = "HTIX5288:00 0911:5288"
REQUIRED_ABS_CODES = {
    e.ABS_MT_SLOT,
    e.ABS_MT_POSITION_X,
    e.ABS_MT_POSITION_Y,
    e.ABS_MT_TRACKING_ID,
}


def find_device():

    for path in glob.glob("/dev/input/event*"):

        try:
            dev = InputDevice(path)
            capabilities = dev.capabilities()
            abs_codes = {
                code
                for code, _ in capabilities.get(e.EV_ABS, [])
            }

            if (
                dev.name.startswith(DEVICE_NAME_PREFIX)
                and REQUIRED_ABS_CODES.issubset(abs_codes)
            ):
                return dev

        except (OSError, PermissionError):
            pass

    raise RuntimeError("HTIX5288 multitouch event device not found")


src = find_device()

try:
    src.grab()
except OSError as exc:
    raise RuntimeError(
        f"Could not exclusively grab {src.path}: {exc}"
    ) from exc

print(
    f"Running exclusively on {src.path}: {src.name}",
    flush=True
)



# ======================================================
# VIRTUAL DEVICE
# ======================================================

ui = UInput(

    {
        e.EV_KEY:
        [
            e.BTN_LEFT,
            e.BTN_RIGHT,
            e.BTN_MIDDLE,
        ],

        e.EV_REL:
        [
            e.REL_X,
            e.REL_Y,
            e.REL_WHEEL,
            e.REL_HWHEEL,
        ],
    },

    name="HTIX5288 Virtual Mouse",
    vendor=0x0911,
    product=0x5288
)



# ======================================================
# SETTINGS
# ======================================================

SENSITIVITY = 0.55

DEADZONE = 2

SMOOTH = 4

# Reject impossible single-frame jumps caused by slot changes or
# incomplete multitouch frames. Normal motion stays well below this.
MAX_POINTER_DELTA = 180


# tap

TAP_TIME = 0.22

TAP_DISTANCE = 25

THREE_FINGER_TAP_TIME = 0.35

THREE_FINGER_TAP_DISTANCE = 40



# scroll

SCROLL_THRESHOLD = 10

HSCROLL_THRESHOLD = 10



# hold click

HOLD_TIME = 0.90

HOLD_DISTANCE = 15



# ======================================================
# STATE
# ======================================================

slot = 0

fingers = {}

previous_finger_count = 0



motion_x = deque(maxlen=SMOOTH)

motion_y = deque(maxlen=SMOOTH)



last_scroll_x = None

last_scroll_y = None



gesture_start = 0

gesture_fingers = 0

gesture_max_move = 0

gesture_total_move = 0



scroll_active = False



# hold state

left_hold = False

right_hold = False

hold_triggered = False



# ======================================================
# HELPERS
# ======================================================


def button_down(btn):

    ui.write(
        e.EV_KEY,
        btn,
        1
    )

    ui.syn()



def button_up(btn):

    ui.write(
        e.EV_KEY,
        btn,
        0
    )

    ui.syn()



def click(btn):

    button_down(btn)

    time.sleep(0.03)

    button_up(btn)



def move(dx,dy):

    dx=int(dx)
    dy=int(dy)

    if dx == 0 and dy == 0:
        return


    ui.write(
        e.EV_REL,
        e.REL_X,
        dx
    )

    ui.write(
        e.EV_REL,
        e.REL_Y,
        dy
    )

    ui.syn()



def wheel(v):

    if v:

        ui.write(
            e.EV_REL,
            e.REL_WHEEL,
            v
        )

        ui.syn()



def hwheel(v):

    if v:

        ui.write(
            e.EV_REL,
            e.REL_HWHEEL,
            v
        )

        ui.syn()



# ======================================================
# LOOP
# ======================================================

for ev in src.read_loop():


    if ev.type == e.EV_ABS:


        if ev.code == e.ABS_MT_SLOT:

            slot = ev.value



        elif ev.code == e.ABS_MT_POSITION_X:

            if slot in fingers:

                fingers[slot]["x"] = ev.value



        elif ev.code == e.ABS_MT_POSITION_Y:

            if slot in fingers:

                fingers[slot]["y"] = ev.value



        elif ev.code == e.ABS_MT_TRACKING_ID:


            # =============================
            # FINGER DOWN
            # =============================

            if ev.value >= 0:


                if len(fingers) == 0:

                    gesture_start = time.time()

                    gesture_fingers = 0

                    gesture_max_move = 0

                    gesture_total_move = 0

                    scroll_active = False

                    hold_triggered = False



                fingers[slot] = {

                    "x":None,
                    "y":None,

                    "oldx":None,
                    "oldy":None,

                    "maxmove":0
                }



                gesture_fingers=max(
                    gesture_fingers,
                    len(fingers)
                )



            # =============================
            # FINGER UP
            # =============================

            else:


                if slot in fingers:

                    gesture_max_move=max(
                        gesture_max_move,
                        fingers[slot]["maxmove"]
                    )

                    del fingers[slot]
    elif ev.type == e.EV_SYN:


        count=len(fingers)

        # Finger-count changes invalidate movement baselines. Without this,
        # lifting one finger after scrolling can reuse stale coordinates and
        # emit a very large relative movement (the observed cursor teleport).
        if count != previous_finger_count:

            motion_x.clear()
            motion_y.clear()

            last_scroll_x=None
            last_scroll_y=None

            for finger in fingers.values():

                if finger["x"] is not None and finger["y"] is not None:

                    finger["oldx"]=finger["x"]
                    finger["oldy"]=finger["y"]

                else:

                    finger["oldx"]=None
                    finger["oldy"]=None

            previous_finger_count=count



        # Include movement from the current frame before deciding whether a
        # stationary touch should become a held button. The old order checked
        # for a hold first, which could press BTN_LEFT just as movement began.
        pending_move = 0

        if count == 1:

            finger = next(iter(fingers.values()))

            if (
                finger["x"] is not None
                and finger["y"] is not None
                and finger["oldx"] is not None
                and finger["oldy"] is not None
            ):

                pending_move = math.hypot(
                    finger["x"]-finger["oldx"],
                    finger["y"]-finger["oldy"]
                )

        elif count == 2 and last_scroll_x is not None:

            if all(
                finger["x"] is not None and finger["y"] is not None
                for finger in fingers.values()
            ):

                avg_x=sum(finger["x"] for finger in fingers.values())/2
                avg_y=sum(finger["y"] for finger in fingers.values())/2

                pending_move = math.hypot(
                    avg_x-last_scroll_x,
                    avg_y-last_scroll_y
                )


        # =================================
        # HOLD CLICK DETECTION
        # =================================

        if (
            not hold_triggered
            and
            count > 0
            and
            not scroll_active
            and
            time.time()-gesture_start > HOLD_TIME
            and
            gesture_total_move + pending_move < HOLD_DISTANCE
        ):


            # -----------------------------
            # ONE FINGER = LEFT HOLD
            # -----------------------------

            if (
                count == 1
                and
                not left_hold
            ):

                button_down(
                    e.BTN_LEFT
                )

                left_hold=True

                hold_triggered=True



            # -----------------------------
            # TWO FINGERS = RIGHT HOLD
            # -----------------------------

            elif (
                count == 2
                and
                not right_hold
            ):

                button_down(
                    e.BTN_RIGHT
                )

                right_hold=True

                hold_triggered=True





        # =================================
        # ONE FINGER MOVE
        # =================================

        if count == 1:


            f=next(iter(fingers.values()))



            if f["x"] is None or f["y"] is None:

                continue


            if f["oldx"] is None or f["oldy"] is None:

                f["oldx"]=f["x"]
                f["oldy"]=f["y"]

                continue


            dx=f["x"]-f["oldx"]
            dy=f["y"]-f["oldy"]


            f["oldx"]=f["x"]
            f["oldy"]=f["y"]


            # A slot transition or incomplete report can occasionally produce
            # a delta spanning most of the touchpad. Drop that single frame
            # instead of converting it into a cursor teleport.
            if (
                abs(dx) > MAX_POINTER_DELTA
                or abs(dy) > MAX_POINTER_DELTA
            ):

                motion_x.clear()
                motion_y.clear()
                hold_triggered=True

                continue


            dist=math.hypot(dx,dy)

            gesture_total_move += dist



            f["maxmove"]=max(
                f["maxmove"],
                dist
            )



            gesture_max_move=max(
                gesture_max_move,
                dist
            )



            # ruch anuluje możliwość hold

            if dist > HOLD_DISTANCE:

                hold_triggered=True



            if (
                abs(dx)<DEADZONE
                and
                abs(dy)<DEADZONE
            ):

                continue



            motion_x.append(dx)

            motion_y.append(dy)



            move(
                sum(motion_x)/len(motion_x)*SENSITIVITY,
                sum(motion_y)/len(motion_y)*SENSITIVITY
            )





        # =================================
        # TWO FINGER SCROLL
        # =================================

        elif count == 2:


            if any(
                f["x"] is None or f["y"] is None
                for f in fingers.values()
            ):

                continue


            avg_x=sum(
                f["x"]
                for f in fingers.values()
            )/2


            avg_y=sum(
                f["y"]
                for f in fingers.values()
            )/2




            if last_scroll_x is None:

                last_scroll_x=avg_x
                last_scroll_y=avg_y

                continue




            dx=avg_x-last_scroll_x

            dy=avg_y-last_scroll_y

            gesture_total_move += math.hypot(dx,dy)


            last_scroll_x=avg_x

            last_scroll_y=avg_y




            # dominujący kierunek


            if abs(dy) > abs(dx):


                if abs(dy)>SCROLL_THRESHOLD:


                    scroll_active=True

                    hold_triggered=True



                    gesture_max_move=max(
                        gesture_max_move,
                        abs(dy)
                    )



                    wheel(
                        -int(
                            dy /
                            SCROLL_THRESHOLD
                        )
                    )



            else:


                if abs(dx)>HSCROLL_THRESHOLD:


                    scroll_active=True

                    hold_triggered=True



                    gesture_max_move=max(
                        gesture_max_move,
                        abs(dx)
                    )



                    hwheel(
                        -int(
                            dx /
                            HSCROLL_THRESHOLD
                        )
                    )






        # =================================
        # RELEASE
        # =================================

        elif count == 0:



            # -----------------------------
            # release held buttons
            # -----------------------------


            if left_hold:

                button_up(
                    e.BTN_LEFT
                )

                left_hold=False



            if right_hold:

                button_up(
                    e.BTN_RIGHT
                )

                right_hold=False






            duration=time.time()-gesture_start




            # -----------------------------
            # TAP CLICK
            # tylko jeżeli nie był hold
            # i nie był scroll
            # -----------------------------


            if (
                not scroll_active
                and
                not hold_triggered
            ):


                if (
                    gesture_fingers == 1
                    and
                    duration < TAP_TIME
                    and
                    gesture_max_move < TAP_DISTANCE
                ):


                    click(
                        e.BTN_LEFT
                    )




                elif (
                    gesture_fingers == 2
                    and
                    duration < TAP_TIME
                    and
                    gesture_max_move < TAP_DISTANCE
                ):


                    click(
                        e.BTN_RIGHT
                    )


                elif (
                    gesture_fingers == 3
                    and
                    duration < THREE_FINGER_TAP_TIME
                    and
                    gesture_max_move < THREE_FINGER_TAP_DISTANCE
                ):


                    click(
                        e.BTN_MIDDLE
                    )





            gesture_fingers=0

            gesture_max_move=0

            gesture_total_move=0

            scroll_active=False

            hold_triggered=False


            last_scroll_x=None

            last_scroll_y=None


            motion_x.clear()

            motion_y.clear()
