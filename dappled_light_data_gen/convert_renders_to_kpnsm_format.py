import numpy as np
from tqdm import tqdm
import time
import matplotlib.pyplot as plt
import argparse
import yaml
import os
from datetime import datetime
import cv2
import OpenEXR
import Imath

def read_exr_channel(file_path, channel_name, scale):
    exr_file = OpenEXR.InputFile(file_path)
    header = exr_file.header()
    dw = header['dataWindow']
    width = dw.max.x - dw.min.x + 1
    height = dw.max.y - dw.min.y + 1
    FLOAT = Imath.PixelType(Imath.PixelType.HALF)
    channel_data = exr_file.channel(channel_name, FLOAT)
    channel_data_np = np.frombuffer(channel_data, dtype=np.float16)
    channel_data_np = channel_data_np.astype(np.float32)
    channel_data_np.shape = (height, width)
    return channel_data_np / scale

def read_exr_data(folder_path, exr_file, channels, scale=1.0):
    full_exr_file = os.path.join(folder_path, f"{exr_file}.exr")
    data = [read_exr_channel(full_exr_file, ch, scale) for ch in channels]
    return np.stack(data, axis=0)

# just some renaming for now
# Mogwai.NSSMFeaturePass.ce.1.exr => Mogwai.MyGBuffer.ce.15.exr
# Mogwai.NSSMFeaturePass.cv.1.exr => Mogwai.MyGBuffer.cv.15.exr
# Mogwai.NSSMFeaturePass.distEtoR.1.exr => Mogwai.MyGBuffer.distE.15.exr
# Mogwai.NSSMFeaturePass.distVtoR.1.exr => Mogwai.MyGBuffer.distV.15.exr
# Mogwai.GBufferRT.guideNormalW.1.exr => Mogwai.MyGBuffer.normW.15.exr
# Mogwai.NSSMFeaturePass.posW.1.exr => Mogwai.MyGBuffer.posW.15.exr
# Mogwai.NSSMFeaturePass.shadowMask.1.exr => Mogwai.MyShadowMap.color.15.exr
# Mogwai.NSSMFeaturePass.shadowMask.1.exr => Mogwai.MyGBuffer.visibility.70.exr

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_folder', type=str, required=True, help='Input folder containing Mogwai renders')
    parser.add_argument('--output_folder', type=str, required=True, help='Output folder for KPN-SM formatted data')
    args = parser.parse_args()

    input_folder = args.input_folder
    output_folder = args.output_folder
    os.makedirs(output_folder, exist_ok=True)

    # just convert using the exact names for now, no need to read and write the data
    file_mappings = [
        ("Mogwai.NSSMFeaturePass.ce.1.exr", "Mogwai.MyGBuffer.ce.15.exr"),
        ("Mogwai.NSSMFeaturePass.cv.1.exr", "Mogwai.MyGBuffer.cv.15.exr"),
        ("Mogwai.NSSMFeaturePass.distEtoR.1.exr", "Mogwai.MyGBuffer.distE.15.exr"),
        ("Mogwai.NSSMFeaturePass.distVtoR.1.exr", "Mogwai.MyGBuffer.distV.15.exr"),
        ("Mogwai.GBufferRT.guideNormalW.1.exr", "Mogwai.MyGBuffer.normW.15.exr"),
        ("Mogwai.NSSMFeaturePass.posW.1.exr", "Mogwai.MyGBuffer.posW.15.exr"),
        ("Mogwai.NSSMFeaturePass.shadowMask.1.exr", "Mogwai.MyShadowMap.color.15.exr"),
        ("Mogwai.NSSMFeaturePass.shadowMask.1.exr", "Mogwai.MyGBuffer.visibility.70.exr")
    ]

    for in_file, out_file in file_mappings:
        in_path = os.path.join(input_folder, in_file)
        out_path = os.path.join(output_folder, out_file)
        print(f"Copying {in_path} to {out_path}")
        os.system(f"cp {in_path} {out_path}")
