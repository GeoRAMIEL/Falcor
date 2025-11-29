from falcor import *
from falcor.falcor_ext import RenderGraph, createPass, renderFrame
import random
import math

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
    AccumulatePass = createPass("AccumulatePass", {'enabled': True, 'precisionMode': 'Single'})
    g.addPass(AccumulatePass, "AccumulatePass")
    ToneMapper = createPass("ToneMapper", {'autoExposure': False, 'exposureCompensation': 0.0})
    g.addPass(ToneMapper, "ToneMapper")
    g.addEdge("VBufferRT.vbuffer", "PathTracer.vbuffer")
    g.addEdge("VBufferRT.viewW", "PathTracer.viewW")
    g.addEdge("VBufferRT.mvec", "PathTracer.mvec")
    g.addEdge("PathTracer.color", "AccumulatePass.input")
    g.addEdge("AccumulatePass.output", "ToneMapper.src")
    g.markOutput("ToneMapper.dst")
    g.markOutput("PathTracer.shadowFactor")
    return g

test_graph = render_graph_PathTracer()
try: m.addGraph(test_graph)
except NameError: None

m.frameCapture.outputDir = "/workspace/develop/falcor_scenes/mogwai_gt_renders"
m.frameCapture.baseFilename = "Mogwai"

m.clock.exitFrame = 100
# capture frames 10, 20, ..., 100
m.frameCapture.addFrames(m.activeGraph, range(10, 101, 10))

frameIndex = 0

def onSceneUpdate(scene, time):
    global frameIndex
    # only update on frame 1, 11, 21, ..., 91
    if frameIndex % 10 != 1:
        frameIndex += 1
        return

    print(f"======== onSceneUpdate called. time={time}. ========")
    # TODO: randomize scene object properties here
    mainCam = scene.cameras[0]  # assuming main camera is the first added
    sunCam = scene.cameras[1] # assuming sun camera is the second added
    sunLight = scene.getLight('Sun Light Distant')

    sunDir = float3(random.uniform(-0.4, 0.4), -1.0, random.uniform(-0.4, 0.4))
    sunDir = sunDir / math.sqrt(sunDir.x**2 + sunDir.y**2 + sunDir.z**2)
    sunLight.direction = sunDir

    mainCamActivityCenter = float3(-40.0, 3.0, 40.0)
    mainCamActivityMaxRadius = 25.0
    mainCamActivityMinRadius = 10.0
    mainCamMinHeight = 1.0
    mainCamMaxHeight = 6.0
    # calculate a random position around the activity center
    angle = random.uniform(0, 2 * math.pi)
    radius = random.uniform(mainCamActivityMinRadius, mainCamActivityMaxRadius)
    height = random.uniform(mainCamMinHeight, mainCamMaxHeight)
    mainCam.position = float3(
        mainCamActivityCenter.x + radius * math.cos(angle),
        height,
        mainCamActivityCenter.z + radius * math.sin(angle)
    )
    mainCam.target = float3(
        mainCamActivityCenter.x + random.uniform(-15.0, 15.0),
        mainCamActivityCenter.y + random.uniform(-2.0, 2.0),
        mainCamActivityCenter.z + random.uniform(-15.0, 15.0)
    )

    orthoSize = 100.0
    sunCam.position = mainCam.position + float3(0, 50.0, 0)
    sunCam.target = sunCam.position + sunDir * orthoSize

    print("sunCamera:", sunCam.position, sunCam.target)
    print("mainCamera:", mainCam.position, mainCam.target)

    # TODO: pre-generate randomized scene object properties and set them here

    frameIndex += 1

m.sceneUpdateCallback = onSceneUpdate


