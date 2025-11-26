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
    GBufferPass = createPass("GBufferRT", {'samplePattern': 'Stratified', 'sampleCount': 16})
    g.addPass(GBufferPass, "GBufferRT")
    #SceneDebugger = createPass('SceneDebugger')
    #g.addPass(SceneDebugger, 'SceneDebugger')
    g.markOutput("SunShadowMapPass.shadowDepth")
    g.markOutput("GBufferRT.guideNormalW")
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

m.clock.exitFrame = 4
m.frameCapture.addFrames(m.activeGraph, [1, 2, 3])

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

# Capture frames with clock paused and then exit

#m.clock.pause()
#for f in [1, 2, 3]:
#    # Shadow first
#    m.scene.camera = sunCam
#    m.renderGraph(shadow_depth_graph)
#    m.setActiveGraph(shadow_depth_graph)
#
#    # Inject shadow map if needed:
#    # shadow_tex = gShadow.getOutput("Shadow.depth")
#    # m.updatePass(gMain, "Lighting", Dictionary({"shadowMap": shadow_tex}))
#
#    # Main render
#    m.scene.camera = mainCam
#    m.setActiveGraph(test_graph)
#
#    # Capture this frame from the active graph (gMain)
#    m.frameCapture.capture()
