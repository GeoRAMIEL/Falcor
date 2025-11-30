from falcor import *
from falcor.falcor_ext import RenderGraph, createPass, renderFrame
import random
import math
import json
from randomization_applier import apply_randomization
import tqdm

ENABLE_COLOR_RENDER = False

def render_graph_PathTracer():
    g = RenderGraph("PathTracer")
    PathTracer = createPass("PathTracer", {'samplesPerPixel': 64, 'maxSurfaceBounces': 0, 'maxDiffuseBounces': 0, 'maxSpecularBounces': 0, 'maxTransmissionBounces': 0})
    g.addPass(PathTracer, "PathTracer")
    VBufferRT = createPass("VBufferRT", {'samplePattern': 'Stratified', 'sampleCount': 64, 'useAlphaTest': True})
    g.addPass(VBufferRT, "VBufferRT")
    AccumulatePass2S = createPass("AccumulatePass", {'enabled': True, 'precisionMode': 'Single', 'outputFormat': 'R32Float'})
    g.addPass(AccumulatePass2S, "ShadowFactorAccumulate")
    OptixDenoiser = createPass("OptixDenoiser")
    g.addPass(OptixDenoiser, "ShadowDenoiser")
    g.addEdge("VBufferRT.vbuffer", "PathTracer.vbuffer")
    g.addEdge("VBufferRT.viewW", "PathTracer.viewW")
    g.addEdge("VBufferRT.mvec", "PathTracer.mvec")
    g.addEdge("PathTracer.shadowFactor", "ShadowFactorAccumulate.input")
    # denoise
    g.addEdge("ShadowFactorAccumulate.output", "ShadowDenoiser.color")
    g.addEdge("PathTracer.guideNormal", "ShadowDenoiser.normal")

    AccumulatePass1 = createPass("AccumulatePass", {'enabled': True, 'precisionMode': 'Single'})
    g.addPass(AccumulatePass1, "AccumulatePass1")
    ToneMapper = createPass("ToneMapper", {'autoExposure': False, 'exposureCompensation': 0.0})
    g.addPass(ToneMapper, "ToneMapper")
    g.addEdge("PathTracer.color", "AccumulatePass1.input")
    g.addEdge("AccumulatePass1.output", "ToneMapper.src")

    if ENABLE_COLOR_RENDER:
        g.markOutput("ToneMapper.dst")
    #g.markOutput("PathTracer.shadowFactor")
    #g.markOutput("ShadowFactorAccumulate.output")
    g.markOutput("ShadowDenoiser.output")
    return g

test_graph = render_graph_PathTracer()
try: m.addGraph(test_graph)
except NameError: None

m.frameCapture.outputDir = "/workspace/develop/falcor_scenes/mogwai_gt_renders"
#m.frameCapture.outputDir = "/data/mogwai_gt_renders"
m.frameCapture.baseFilename = "Mogwai"

# load randomization settings
randomizaiton_file_path = "/workspace/develop/falcor_scenes/EmeraldSquare_v4_1/randomization_settings.json"
with open(randomizaiton_file_path, 'r') as f:
    randomization_settings = json.load(f)
print(f"Loaded {len(randomization_settings)} randomization settings from {randomizaiton_file_path}")

framesToGen = 10
accumulation_frames = 10
m.clock.exitFrame = accumulation_frames*framesToGen
# capture frames 1*accumulation_frames, 2*accumulation_frames, ..., N*accumulation_frames
m.frameCapture.addFrames(m.activeGraph, range(accumulation_frames, accumulation_frames*framesToGen+1, accumulation_frames))

frameIndex = 0

progress_bar = tqdm.tqdm(
    total=framesToGen,
    desc="gt images rendered")

def onSceneUpdate(scene, time):
    global frameIndex
    # only update on frame 1, accumulation_frames+1, 2*accumulation_frames+1, ..., N*accumulation_frames+1
    if frameIndex % accumulation_frames != 1:
        frameIndex += 1
        return

    #print(f"======== onSceneUpdate called. time={time}. ========")

    settingIndex = (frameIndex - 1) // accumulation_frames - 1 # delay randomization loading by 1
    if settingIndex < 0:
        frameIndex += 1
        progress_bar.update(1)
        return
    if settingIndex >= len(randomization_settings):
        print(f"No more randomization settings available for frameIndex={frameIndex}, settingIndex={settingIndex}")
        frameIndex += 1
        progress_bar.update(1)
        return
    apply_randomization(scene, randomization_settings, settingIndex)
    
    frameIndex += 1

    progress_bar.update(1)

m.sceneUpdateCallback = onSceneUpdate


