from falcor import *
from falcor.falcor_ext import RenderGraph, createPass, renderFrame
import random
import math
import json

#const std::string kSamplesPerPixel = "samplesPerPixel";
#const std::string kMaxSurfaceBounces = "maxSurfaceBounces";
#const std::string kMaxDiffuseBounces = "maxDiffuseBounces";
#const std::string kMaxSpecularBounces = "maxSpecularBounces";
#const std::string kMaxTransmissionBounces = "maxTransmissionBounces";

def render_graph_PathTracer():
    g = RenderGraph("PathTracer")
    PathTracer = createPass("PathTracer", {'samplesPerPixel': 64, 'maxSurfaceBounces': 1, 'maxDiffuseBounces': 1, 'maxSpecularBounces': 1, 'maxTransmissionBounces': 1})
    g.addPass(PathTracer, "PathTracer")
    VBufferRT = createPass("VBufferRT", {'samplePattern': 'Stratified', 'sampleCount': 64, 'useAlphaTest': True})
    g.addPass(VBufferRT, "VBufferRT")
    AccumulatePass1 = createPass("AccumulatePass", {'enabled': True, 'precisionMode': 'Single'})
    g.addPass(AccumulatePass1, "AccumulatePass1")
    AccumulatePass2 = createPass("AccumulatePass", {'enabled': True, 'precisionMode': 'Single'})
    g.addPass(AccumulatePass2, "AccumulatePass2")
    ToneMapper = createPass("ToneMapper", {'autoExposure': False, 'exposureCompensation': 0.0})
    g.addPass(ToneMapper, "ToneMapper")
    g.addEdge("VBufferRT.vbuffer", "PathTracer.vbuffer")
    g.addEdge("VBufferRT.viewW", "PathTracer.viewW")
    g.addEdge("VBufferRT.mvec", "PathTracer.mvec")
    g.addEdge("PathTracer.color", "AccumulatePass1.input")
    g.addEdge("AccumulatePass1.output", "ToneMapper.src")
    g.addEdge("PathTracer.shadowFactor", "AccumulatePass2.input")
    #g.markOutput("ToneMapper.dst")
    #g.markOutput("PathTracer.shadowFactor")
    g.markOutput("AccumulatePass2.output")
    return g

test_graph = render_graph_PathTracer()
try: m.addGraph(test_graph)
except NameError: None

m.frameCapture.outputDir = "/workspace/develop/falcor_scenes/mogwai_gt_renders"
m.frameCapture.baseFilename = "Mogwai"

# randomization setting format
#[
#    {
#        "mainCamera": {
#            "position": [
#                -26.538925785515005,
#                5.550253543686567,
#                45.633266010163524
#            ],
#            "target": [
#                -27.3023573753774,
#                4.596173390729017,
#                30.783376941272767
#            ]
#        },
#        "sunCamera": {
#            "position": [
#                -26.538925785515005,
#                55.550253543686566,
#                45.633266010163524
#            ],
#            "target": [
#                -4.65926217645762,
#                -37.027741116411974,
#                76.46499033867387
#            ]
#        },
#        "sunLight": {
#            "direction": [
#                0.21879663609057384,
#                -0.9257799466009854,
#                0.3083172432851035
#            ]
#        }
#    },
#]
randomizaiton_file_path = "/workspace/develop/falcor_scenes/EmeraldSquare_v4_1/randomization_settings.json"
with open(randomizaiton_file_path, 'r') as f:
    randomization_settings = json.load(f)
print(f"Loaded {len(randomization_settings)} randomization settings from {randomizaiton_file_path}")

m.clock.exitFrame = 100
# capture frames 10, 20, ..., 100
m.frameCapture.addFrames(m.activeGraph, range(10, 101, 10))
#capture frames 9, 19, ..., 99
#m.frameCapture.addFrames(m.activeGraph, range(9, 100, 10))

frameIndex = 0

def onSceneUpdate(scene, time):
    global frameIndex
    # only update on frame 1, 11, 21, ..., 91
    if frameIndex % 10 != 1:
        frameIndex += 1
        return

    print(f"======== onSceneUpdate called. time={time}. ========")
    # TODO: randomize scene object properties here
    #mainCam = scene.cameras[0]  # assuming main camera is the first added
    #sunCam = scene.cameras[1] # assuming sun camera is the second added
    #sunLight = scene.getLight('Sun Light Distant')
#
    #sunDir = float3(random.uniform(-0.4, 0.4), -1.0, random.uniform(-0.4, 0.4))
    #sunDir = sunDir / math.sqrt(sunDir.x**2 + sunDir.y**2 + sunDir.z**2)
    #sunLight.direction = sunDir
#
    #mainCamActivityCenter = float3(-40.0, 3.0, 40.0)
    #mainCamActivityMaxRadius = 25.0
    #mainCamActivityMinRadius = 10.0
    #mainCamMinHeight = 1.0
    #mainCamMaxHeight = 6.0
    ## calculate a random position around the activity center
    #angle = random.uniform(0, 2 * math.pi)
    #radius = random.uniform(mainCamActivityMinRadius, mainCamActivityMaxRadius)
    #height = random.uniform(mainCamMinHeight, mainCamMaxHeight)
    #mainCam.position = float3(
    #    mainCamActivityCenter.x + radius * math.cos(angle),
    #    height,
    #    mainCamActivityCenter.z + radius * math.sin(angle)
    #)
    #mainCam.target = float3(
    #    mainCamActivityCenter.x + random.uniform(-15.0, 15.0),
    #    mainCamActivityCenter.y + random.uniform(-2.0, 2.0),
    #    mainCamActivityCenter.z + random.uniform(-15.0, 15.0)
    #)
#
    #orthoSize = 100.0
    #sunCam.position = mainCam.position + float3(0, 50.0, 0)
    #sunCam.target = sunCam.position + sunDir * orthoSize
#
    #print("sunCamera:", sunCam.position, sunCam.target)
    #print("mainCamera:", mainCam.position, mainCam.target)
#
    ## TODO: pre-generate randomized scene object properties and set them here
#

    settingIndex = (frameIndex - 1) // 10
    if settingIndex >= len(randomization_settings):
        print(f"No more randomization settings available for frameIndex={frameIndex}, settingIndex={settingIndex}")
        frameIndex += 1
        return
    setting = randomization_settings[settingIndex]
    mainCam = scene.cameras[0]  # assuming main camera is the first added
    sunCam = scene.cameras[1] # assuming sun camera is the second added
    sunLight = scene.getLight('Sun Light Distant')
    print(f"mainCam pos: {setting['mainCamera']['position']}, target: {setting['mainCamera']['target']}")

    mainCam.position = float3(setting['mainCamera']['position'][0], setting['mainCamera']['position'][1], setting['mainCamera']['position'][2])
    mainCam.target = float3(setting['mainCamera']['target'][0], setting['mainCamera']['target'][1], setting['mainCamera']['target'][2])
    sunCam.position = float3(setting['sunCamera']['position'][0], setting['sunCamera']['position'][1], setting['sunCamera']['position'][2])
    sunCam.target = float3(setting['sunCamera']['target'][0], setting['sunCamera']['target'][1], setting['sunCamera']['target'][2])
    sunLight.direction = float3(setting['sunLight']['direction'][0], setting['sunLight']['direction'][1], setting['sunLight']['direction'][2])

    frameIndex += 1

m.sceneUpdateCallback = onSceneUpdate


