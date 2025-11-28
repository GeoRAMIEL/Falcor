add_plugin(NSSMPasses)

target_sources(NSSMPasses PRIVATE
    ShadowDepth.3d.slang
    ShadowProjection.cs.slang
    NSSMFeaturePass.cs.slang
    ShadowDepthPass.cpp
    ShadowDepthPass.h
    ShadowProjectionPass.cpp
    ShadowProjectionPass.h
    NSSMFeaturePass.cpp
    NSSMFeaturePass.h
    NSSMPasses.cpp
)

target_copy_shaders(NSSMPasses RenderPasses/NSSMPasses)

target_source_group(NSSMPasses "RenderPasses")
