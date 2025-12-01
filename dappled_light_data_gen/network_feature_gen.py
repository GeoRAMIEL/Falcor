from falcor import *
from falcor.falcor_ext import RenderGraph, createPass, renderFrame
import random
import math
import json
from randomization_applier import apply_randomization
import tqdm

IS_TEST_RUN = False
#IS_TEST_RUN = True
#GENERATE_FOR_TRAINING = True
GENERATE_FOR_TRAINING = False

def render_graph_test():
    g = RenderGraph("test_graph")

    # Shadow map pass
    SunShadowMapPass = createPass("ShadowDepthPass", {'shadowCamera': 'sunCamera', 'outputSize': 4096, 'forceCullMode': True, 'cull': 'None'})
    g.addPass(SunShadowMapPass, "SunShadowMapPass")

    # Shadow depth feature extraction pass (pinhole detection)
    ShadowDepthFeatureExtraction = createPass("ShadowDepthFeatureExtraction", {'shadowCamera': 'sunCamera', 'outputSize': 4096, 'varRadiusW': 0.1})
    g.addPass(ShadowDepthFeatureExtraction, "ShadowDepthFeatureExtraction")

    # GBuffer pass
    GBufferPass = createPass("GBufferRT", {'samplePattern': 'Center', 'sampleCount': 1})
    g.addPass(GBufferPass, "GBufferRT")

    NSSMFeaturePass = createPass("NSSMFeaturePass", {'shadowCamera': 'sunCamera', 'light': 'Sun Light Distant', 'shadowBias': 0.0005})
    g.addPass(NSSMFeaturePass, "NSSMFeaturePass")

    g.addEdge("SunShadowMapPass.shadowDepth", "NSSMFeaturePass.shadowDepth")
    g.addEdge("SunShadowMapPass.shadowDepth", "ShadowDepthFeatureExtraction.shadowDepth")

    g.addEdge("GBufferRT.depth", "NSSMFeaturePass.GBufferDepth")
    g.addEdge("GBufferRT.guideNormalW", "NSSMFeaturePass.GBufferNormal")
    g.addEdge("ShadowDepthFeatureExtraction.stdMap", "NSSMFeaturePass.lightSpaceShadowDepthStd")
    g.addEdge("ShadowDepthFeatureExtraction.pinholeMap", "NSSMFeaturePass.lightSpacePinholeMap")
    g.addEdge("ShadowDepthFeatureExtraction.dvgMap", "NSSMFeaturePass.lightSpaceDivergenceMap")

    #g.markOutput("SunShadowMapPass.shadowDepth")
    #g.markOutput("GBufferRT.guideNormalW")
    g.markOutput("NSSMFeaturePass.shadowMask")
    g.markOutput("NSSMFeaturePass.cv")
    g.markOutput("NSSMFeaturePass.ce")
    g.markOutput("NSSMFeaturePass.distRtoB")
    g.markOutput("NSSMFeaturePass.distVtoR")
    #g.markOutput("NSSMFeaturePass.posW")
    g.markOutput("NSSMFeaturePass.projectedShadowDepthStd")
    g.markOutput("NSSMFeaturePass.projectedDivergenceMap")
    return g

test_graph = render_graph_test()
try: m.addGraph(test_graph)
except NameError: None

if IS_TEST_RUN:
    m.frameCapture.outputDir = "/workspace/develop/falcor_scenes/mogwai_feature_renders"
else:
    if GENERATE_FOR_TRAINING:
        m.frameCapture.outputDir = "/data/nssm_data/train/mogwai_feature_renders"
    else:
        m.frameCapture.outputDir = "/data/nssm_data/validation/mogwai_feature_renders"
m.frameCapture.baseFilename = "Mogwai"
print(f"Output folder set to: {m.frameCapture.outputDir}")

# load randomization settings
randomizaiton_file_path = "/no/path/rnd.json"
if GENERATE_FOR_TRAINING:
    # For training
    randomizaiton_file_path = "/workspace/develop/Falcor/dappled_light_data_gen/randomization_settings_train.json"
else:
    # For validation
    randomizaiton_file_path = "/workspace/develop/Falcor/dappled_light_data_gen/randomization_settings_val.json"
with open(randomizaiton_file_path, 'r') as f:
    randomization_settings = json.load(f)
print(f"Loaded {len(randomization_settings)} randomization settings from {randomizaiton_file_path}")

framesToGen = 10
if not IS_TEST_RUN:
    if GENERATE_FOR_TRAINING:
        framesToGen = 10000
    else:
        framesToGen = 1000
m.clock.exitFrame = framesToGen
m.frameCapture.addFrames(m.activeGraph, range(1, framesToGen + 1))

frameIndex = 0

progress_bar = tqdm.tqdm(
    total=framesToGen,
    desc="feature group rendered")

def onSceneUpdate(scene, time):
    global frameIndex
    if frameIndex == 0:
        frameIndex += 1
        return
    #print(f"======== onSceneUpdate called. time={time}. ========")
    
    settingIndex = frameIndex - 1
    if settingIndex >= len(randomization_settings):
        print(f"No more randomization settings available for frameIndex={frameIndex}, settingIndex={settingIndex}")
        frameIndex += 1
        progress_bar.update(1)
        return
    
    apply_randomization(scene, randomization_settings, settingIndex)

    frameIndex += 1

    progress_bar.update(1)


m.sceneUpdateCallback = onSceneUpdate

