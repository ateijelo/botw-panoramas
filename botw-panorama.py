#!/usr/bin/env python

from __future__ import print_function

from subprocess import call
import argparse
import sys
import cv2
import os

def log(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()

def hugin_tool(cmd):
    global step

    in_pto = "step{}.pto".format(step - 1)
    out_pto = "step{}.pto".format(step)

    if IN in cmd:
        i = cmd.index(IN)
        cmd[i] = in_pto

    if OUT in cmd:
        i = cmd.index(OUT)
        cmd[i] = out_pto

    if options.first_step <= step:
        call(cmd)
    else:
        log("Skipping step", step, ":", *cmd)

    step += 1
    return out_pto

def crop_images(images):
    cropped_imgs = []
    for img in images:
        cropped_imgs.append(img[66:720, 0:1280])
    return cropped_imgs

def remove_crosshair(images, crosshair_mask):
    result = []
    mask = cv2.imread(crosshair_mask)
    mask = cv2.split(mask)[0]
    for i, img in enumerate(images):
        result.append(cv2.inpaint(img, mask, 6, cv2.INPAINT_NS))
    return result

def load_images(image_filenames):
    imgs = []
    for filename in image_filenames:
        imgs.append(cv2.imread(filename))
    return imgs

def write_images(name_format, images):
    filenames = []
    for i, img in enumerate(images):
        filename = name_format.format(prefix, i)
        cv2.imwrite(filename, img)
        filenames.append(filename)
    return filenames

if __name__ == "__main__":
    default_crosshair_mask = os.path.join(os.path.dirname(__file__), "crosshair-mask-1-digit.png")

    parser = argparse.ArgumentParser()
    parser.add_argument("--first-step", type=int, default=1)
    parser.add_argument("--crosshair-mask", default=default_crosshair_mask)
    parser.add_argument("images", nargs="+")
    options = parser.parse_args()

    IN = -1
    OUT = -2

    step = 1

    name_format = "nocross-cropped-{}.png"

    if options.first_step <= 1:
        log("Loading images... ", end="")
        images = load_images(options.images)
        log("done.")

        log("Removing crosshairs... ", end="")
        images = remove_crosshair(images, options.crosshair_mask)
        log("done.")

        log("Cropping... ", end="")
        images = crop_images(images)
        log("done.")

        log("Saving to files... ", end="")
        image_filenames = write_images(name_format, images)
        log("done.")
    else:
        image_filenames = []
        for i, img in enumerate(options.images):
            image_filenames.append(name_format.format(i))


    # create the Hugin project file
    hugin_tool(["pto_gen","--fov","35","-o",OUT] + image_filenames)

    # control points
    hugin_tool(["cpfind","--multirow","10",IN,"-o",OUT])

    # find vertical lines
    hugin_tool(["linefind",IN,"-o",OUT])

    # align
    hugin_tool(["autooptimiser","-a","-l","-s",IN,"-o",OUT])

    # set some pano settings (straighten, center, crop)
    hugin_tool(["pano_modify","-s","-c",IN,"-o",OUT])

    # stitch
    hugin_tool(["hugin_executor","-t4","--stitching",IN])
