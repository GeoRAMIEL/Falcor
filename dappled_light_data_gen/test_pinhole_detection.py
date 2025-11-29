from falcor import *
from falcor.falcor_ext import RenderGraph, createPass, renderFrame

def render_graph_MinimalPathTracer():
    g = RenderGraph("MinimalPathTracer")
    AccumulatePass = createPass("AccumulatePass", {'enabled': True, 'precisionMode': 'Single'})
    g.addPass(AccumulatePass, "AccumulatePass")
    ToneMapper = createPass("ToneMapper", {'autoExposure': False, 'exposureCompensation': 0.0})
    g.addPass(ToneMapper, "ToneMapper")
    MinimalPathTracer = createPass("MinimalPathTracer", {'maxBounces': 3})
    g.addPass(MinimalPathTracer, "MinimalPathTracer")
    VBufferRT = createPass("VBufferRT", {'samplePattern': 'Stratified', 'sampleCount': 64})
    g.addPass(VBufferRT, "VBufferRT")
    g.addEdge("AccumulatePass.output", "ToneMapper.src")
    g.addEdge("VBufferRT.vbuffer", "MinimalPathTracer.vbuffer")
    g.addEdge("VBufferRT.viewW", "MinimalPathTracer.viewW")
    g.addEdge("MinimalPathTracer.color", "AccumulatePass.input")
    g.markOutput("ToneMapper.dst")
    return g

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

def pinhole_detection_graph():
    g = RenderGraph("SunShadowMap")
    # Shadow depth pass
    SunShadowMapPass = createPass("ShadowDepthPass", {'shadowCamera': 'sunCamera', 'outputSize': 4096, 'forceCullMode': True, 'cull': 'None'})
    g.addPass(SunShadowMapPass, "SunShadowMapPass")

    # GBuffer pass
    GBufferPass = createPass("GBufferRT", {'samplePattern': 'Center', 'sampleCount': 1})
    g.addPass(GBufferPass, "GBufferRT")

    # Shadow depth feature extraction pass (pinhole detection)
    ShadowDepthFeatureExtraction = createPass("ShadowDepthFeatureExtraction", {'shadowCamera': 'sunCamera', 'outputSize': 4096, 'varRadiusW': 0.1})
    g.addPass(ShadowDepthFeatureExtraction, "ShadowDepthFeatureExtraction")

    # NSSM feature pass
    NSSMFeaturePass = createPass("NSSMFeaturePass", {'shadowCamera': 'sunCamera', 'light': 'Sun Light Distant', 'shadowBias': 0.0002})
    g.addPass(NSSMFeaturePass, "NSSMFeaturePass")

    g.addEdge("SunShadowMapPass.shadowDepth", "ShadowDepthFeatureExtraction.shadowDepth")
    g.addEdge("SunShadowMapPass.shadowDepth", "NSSMFeaturePass.shadowDepth")
    g.addEdge("GBufferRT.depth", "NSSMFeaturePass.GBufferDepth")
    g.addEdge("GBufferRT.guideNormalW", "NSSMFeaturePass.GBufferNormal")
    g.addEdge("ShadowDepthFeatureExtraction.stdMap", "NSSMFeaturePass.lightSpaceShadowDepthStd")
    g.addEdge("ShadowDepthFeatureExtraction.pinholeMap", "NSSMFeaturePass.lightSpacePinholeMap")
    g.addEdge("ShadowDepthFeatureExtraction.dvgMap", "NSSMFeaturePass.lightSpaceDivergenceMap")

    g.markOutput("SunShadowMapPass.shadowDepth")
    g.markOutput("ShadowDepthFeatureExtraction.avgMap")
    g.markOutput("ShadowDepthFeatureExtraction.stdMap")
    g.markOutput("ShadowDepthFeatureExtraction.pinholeMap")
    g.markOutput("ShadowDepthFeatureExtraction.dvgMap")
    g.markOutput("NSSMFeaturePass.projectedShadowDepthStd")
    g.markOutput("NSSMFeaturePass.projectedPinholeMap")
    g.markOutput("NSSMFeaturePass.projectedDivergenceMap")
    return g

pinhole_graph = pinhole_detection_graph()
path_tracer_graph = render_graph_MinimalPathTracer()
try: m.addGraph(pinhole_graph)
except NameError: None
#try: m.addGraph(path_tracer_graph)
#except NameError: None

m.frameCapture.outputDir = "/workspace/develop/falcor_scenes/mogwai_renders"
m.frameCapture.baseFilename = "Mogwai"

m.clock.exitFrame = 2
m.frameCapture.addFrames(m.activeGraph, [1])

def onSceneUpdate(scene, time):
    print("======== onSceneUpdate called. ========")
    print("==== scene:", scene)
    print("==== time:", time)
    # TODO: randomize scene object properties here
m.sceneUpdateCallback = onSceneUpdate

#sunCam = m.scene.cameras[0]  # assuming sun camera is the first added
#mainCam = m.scene.cameras[1]  # assuming main camera is the second added
#print("sunCamera:", sunCam.position, sunCam.target)
#print("mainCamera:", mainCam.position, mainCam.target)

