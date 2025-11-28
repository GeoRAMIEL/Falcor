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
    VBufferRT = createPass("VBufferRT", {'samplePattern': 'Stratified', 'sampleCount': 16})
    g.addPass(VBufferRT, "VBufferRT")
    g.addEdge("AccumulatePass.output", "ToneMapper.src")
    g.addEdge("VBufferRT.vbuffer", "MinimalPathTracer.vbuffer")
    g.addEdge("VBufferRT.viewW", "MinimalPathTracer.viewW")
    g.addEdge("MinimalPathTracer.color", "AccumulatePass.input")
    g.markOutput("ToneMapper.dst")
    return g

def render_graph_PathTracer():
    g = RenderGraph("PathTracer")
    PathTracer = createPass("PathTracer", {'samplesPerPixel': 16})
    g.addPass(PathTracer, "PathTracer")
    VBufferRT = createPass("VBufferRT", {'samplePattern': 'Stratified', 'sampleCount': 16, 'useAlphaTest': True})
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
    return g

def render_graph_BSDFViewer():
    g = RenderGraph("BSDFViewer")
    BSDFViewer = createPass("BSDFViewer", {'materialID': 0})
    g.addPass(BSDFViewer, "BSDFViewer")
    AccumulatePass = createPass("AccumulatePass", {'enabled': True, 'precisionMode': 'Double'})
    g.addPass(AccumulatePass, "AccumulatePass")
    g.addEdge("BSDFViewer.output", "AccumulatePass.input")
    g.markOutput("AccumulatePass.output")
    return g

def render_graph_SceneDebugger():
    g = RenderGraph('SceneDebugger')
    SceneDebugger = createPass('SceneDebugger')
    g.addPass(SceneDebugger, 'SceneDebugger')
    g.markOutput('SceneDebugger.output')
    return g

def render_graph_test():
    g = RenderGraph("test_graph")

    SunShadowMapPass = createPass("ShadowDepthPass", {'shadowCamera': 'sunCamera', 'forceCullMode': True, 'cull': 'None'})
    g.addPass(SunShadowMapPass, "SunShadowMapPass")

    GBufferPass = createPass("GBufferRT", {'samplePattern': 'Center', 'sampleCount': 1})
    g.addPass(GBufferPass, "GBufferRT")

    #ShadowProjectionPass = createPass("ShadowProjectionPass", {'shadowCamera': 'sunCamera', 'shadowBias': 0.005})
    #g.addPass(ShadowProjectionPass, "ShadowProjectionPass")

    #g.addEdge("SunShadowMapPass.shadowDepth", "ShadowProjectionPass.shadowDepth")
    #g.addEdge("GBufferRT.depth", "ShadowProjectionPass.GBufferDepth")

    NSSMFeaturePass = createPass("NSSMFeaturePass", {'shadowCamera': 'sunCamera', 'light': 'Sun Light Distant', 'shadowBias': 0.005})
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
    SunShadowMapPass = createPass("ShadowDepthPass", {'shadowCamera': 'sunCamera', 'forceCullMode': True, 'cull': 'None'})
    g.addPass(SunShadowMapPass, "SunShadowMapPass")
    g.markOutput("SunShadowMapPass.shadowDepth")
    return g

#shadow_depth_graph = render_graph_sun_shadow_map()
#try: m.addGraph(shadow_depth_graph)
#except NameError: None

#test_graph = render_graph_MinimalPathTracer()
#test_graph = render_graph_PathTracer()
#test_graph = render_graph_BSDFViewer()
#test_graph = render_graph_SceneDebugger()
test_graph = render_graph_test()
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

