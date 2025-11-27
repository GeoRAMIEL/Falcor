add_plugin(NSSMPasses)

target_sources(NSSMPasses PRIVATE
    ShadowDepth.3d.slang
    ShadowProjection.cs.slang
    ShadowDepthPass.cpp
    ShadowDepthPass.h
    ShadowProjectionPass.cpp
    ShadowProjectionPass.h
    NSSMPasses.cpp
)

target_copy_shaders(NSSMPasses RenderPasses/NSSMPasses)

target_source_group(NSSMPasses "RenderPasses")
