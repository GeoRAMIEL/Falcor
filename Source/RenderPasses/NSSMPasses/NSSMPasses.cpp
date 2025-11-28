#include "ShadowDepthPass.h"
#include "ShadowProjectionPass.h"
#include "NSSMFeaturePass.h"

extern "C" FALCOR_API_EXPORT void registerPlugin(Falcor::PluginRegistry& registry)
{
    registry.registerClass<RenderPass, ShadowDepthPass>();
    registry.registerClass<RenderPass, ShadowProjectionPass>();
    registry.registerClass<RenderPass, NSSMFeaturePass>();
}
