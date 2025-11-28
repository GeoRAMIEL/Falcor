from falcor import *
from falcor.falcor_ext import RenderGraph, createPass, renderFrame

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
    g.markOutput("PathTracer.shadowFactor")
    return g


#shadow_depth_graph = render_graph_sun_shadow_map()
#try: m.addGraph(shadow_depth_graph)
#except NameError: None

test_graph = render_graph_PathTracer()
try: m.addGraph(test_graph)
except NameError: None

m.frameCapture.outputDir = "/workspace/develop/Falcor/dappled_light_data_gen/mogwai_renders"
m.frameCapture.baseFilename = "Mogwai"

m.clock.exitFrame = 2
m.frameCapture.addFrames(m.activeGraph, [1])

def onSceneUpdate(scene, time):
    print("======== onSceneUpdate called. ========")
m.sceneUpdateCallback = onSceneUpdate


