add_plugin(NSSMPasses)

target_sources(NSSMPasses PRIVATE
    ShadowDepth.3d.slang
    ShadowDepthPass.cpp
    ShadowDepthPass.h
)

target_copy_shaders(NSSMPasses RenderPasses/NSSMPasses)

target_source_group(NSSMPasses "RenderPasses")
