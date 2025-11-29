from falcor import *
from falcor.falcor_ext import RenderGraph, createPass, renderFrame

def render_graph_test():
    g = RenderGraph("test_graph")

    SunShadowMapPass = createPass("ShadowDepthPass", {'shadowCamera': 'sunCamera', 'outputSize': 4096, 'forceCullMode': True, 'cull': 'None'})
    g.addPass(SunShadowMapPass, "SunShadowMapPass")

    GBufferPass = createPass("GBufferRT", {'samplePattern': 'Center', 'sampleCount': 1})
    g.addPass(GBufferPass, "GBufferRT")

    #ShadowProjectionPass = createPass("ShadowProjectionPass", {'shadowCamera': 'sunCamera', 'shadowBias': 0.0002})
    #g.addPass(ShadowProjectionPass, "ShadowProjectionPass")

    #g.addEdge("SunShadowMapPass.shadowDepth", "ShadowProjectionPass.shadowDepth")
    #g.addEdge("GBufferRT.depth", "ShadowProjectionPass.GBufferDepth")

    NSSMFeaturePass = createPass("NSSMFeaturePass", {'shadowCamera': 'sunCamera', 'light': 'Sun Light Distant', 'shadowBias': 0.0002})
    g.addPass(NSSMFeaturePass, "NSSMFeaturePass")

    g.addEdge("SunShadowMapPass.shadowDepth", "NSSMFeaturePass.shadowDepth")
    g.addEdge("GBufferRT.depth", "NSSMFeaturePass.GBufferDepth")
    g.addEdge("GBufferRT.guideNormalW", "NSSMFeaturePass.GBufferNormal")

    #SceneDebugger = createPass('SceneDebugger')
    #g.addPass(SceneDebugger, 'SceneDebugger')

    g.markOutput("SunShadowMapPass.shadowDepth")
    g.markOutput("GBufferRT.guideNormalW")
    #g.markOutput("ShadowProjectionPass.shadowMask")
    g.markOutput("NSSMFeaturePass.shadowMask")
    g.markOutput("NSSMFeaturePass.cv")
    g.markOutput("NSSMFeaturePass.ce")
    g.markOutput("NSSMFeaturePass.distRtoB")
    g.markOutput("NSSMFeaturePass.distEtoR")
    g.markOutput("NSSMFeaturePass.distVtoR")
    g.markOutput("NSSMFeaturePass.distEtoB")
    g.markOutput("NSSMFeaturePass.posW")
    #g.markOutput("SceneDebugger.output")
    return g

def render_graph_sun_shadow_map():
    g = RenderGraph("SunShadowMap")
    SunShadowMapPass = createPass("ShadowDepthPass", {'shadowCamera': 'sunCamera', 'outputSize': 4096, 'forceCullMode': True, 'cull': 'None'})
    g.addPass(SunShadowMapPass, "SunShadowMapPass")
    ShadowDepthFeatureExtraction = createPass("ShadowDepthFeatureExtraction", {'shadowCamera': 'sunCamera', 'outputSize': 4096, 'varRadiusW': 0.3})
    g.addPass(ShadowDepthFeatureExtraction, "ShadowDepthFeatureExtraction")
    g.addEdge("SunShadowMapPass.shadowDepth", "ShadowDepthFeatureExtraction.shadowDepth")
    g.markOutput("SunShadowMapPass.shadowDepth")
    g.markOutput("ShadowDepthFeatureExtraction.avgMap")
    g.markOutput("ShadowDepthFeatureExtraction.stdMap")
    g.markOutput("ShadowDepthFeatureExtraction.pinholeMap")
    return g

test_graph = render_graph_sun_shadow_map()
try: m.addGraph(test_graph)
except NameError: None

m.frameCapture.outputDir = "/workspace/develop/Falcor/dappled_light_data_gen/mogwai_renders"
m.frameCapture.baseFilename = "Mogwai"

m.clock.exitFrame = 2
m.frameCapture.addFrames(m.activeGraph, [1])

def onSceneUpdate(scene, time):
    print("======== onSceneUpdate called. ========")
    print("==== scene:", scene)
    print("==== time:", time)
    # TODO: randomize scene object properties here
m.sceneUpdateCallback = onSceneUpdate

sunCam = m.scene.cameras[0]  # assuming sun camera is the first added
mainCam = m.scene.cameras[1]  # assuming main camera is the second added
print("sunCamera:", sunCam.position, sunCam.target)
print("mainCamera:", mainCam.position, mainCam.target)

