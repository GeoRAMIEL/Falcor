#include "ShadowDepthPass.h"
#include "ShadowProjectionPass.h"
#include "NSSMFeaturePass.h"
#include "ShadowDepthFeatureExtraction.h"

extern "C" FALCOR_API_EXPORT void registerPlugin(Falcor::PluginRegistry& registry)
{
    registry.registerClass<RenderPass, ShadowDepthPass>();
    registry.registerClass<RenderPass, ShadowProjectionPass>();
    registry.registerClass<RenderPass, NSSMFeaturePass>();
    registry.registerClass<RenderPass, ShadowDepthFeatureExtraction>();
}
