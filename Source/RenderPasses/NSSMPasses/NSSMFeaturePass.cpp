#include "NSSMFeaturePass.h"
#include "RenderGraph/RenderPassStandardFlags.h"

namespace
{
const std::string kNSSMFeaturePassProgramFile = "RenderPasses/NSSMPasses/NSSMFeaturePass.cs.slang";

const std::string kShadowDepthName = "shadowDepth";
const std::string kGBufferDepthName = "GBufferDepth";
const std::string kGBufferNormalName = "GBufferNormal";
const std::string kShadowMaskName = "shadowMask";
const std::string kNdotLName = "NdotL";
const std::string kBlockerDistanceName = "blockerDistance";
const std::string kCvName = "cv";

// Scripting options.
const char kShadowCamera[] = "shadowCamera";
const char kLightName[] = "light";
const char kShadowBias[] = "shadowBias";
}

NSSMFeaturePass::NSSMFeaturePass(ref<Device> pDevice, const Properties& props) : RenderPass(pDevice)
{
    parseProperties(props);

    // Initialize compute state
    mpState = ComputeState::create(mpDevice);
}

Properties NSSMFeaturePass::getProperties() const
{
    Properties props;
    props[kShadowCamera] = mShadowCameraName;
    props[kLightName] = mLightName;
    props[kShadowBias] = mShadowBias;
    return props;
}

RenderPassReflection NSSMFeaturePass::reflect(const CompileData& compileData)
{
    const uint2 sz = RenderPassHelpers::calculateIOSize(RenderPassHelpers::IOSize::Default, {}, compileData.defaultTexDims);

    RenderPassReflection reflector;
    reflector.addInput(kShadowDepthName, "Shadow Depth Map")
        .bindFlags(ResourceBindFlags::ShaderResource);
    reflector.addInput(kGBufferDepthName, "G-Buffer Depth buffer")
        .bindFlags(ResourceBindFlags::ShaderResource);
    reflector.addInput(kGBufferNormalName, "G-Buffer Normal buffer")
        .bindFlags(ResourceBindFlags::ShaderResource);

    reflector.addOutput(kShadowMaskName, "Shadow mask")
        .format(ResourceFormat::R32Float)
        .bindFlags(ResourceBindFlags::UnorderedAccess | ResourceBindFlags::ShaderResource)
        .texture2D(sz.x, sz.y);

    reflector.addOutput(kNdotLName, "N dot L")
        .format(ResourceFormat::R32Float)
        .bindFlags(ResourceBindFlags::UnorderedAccess | ResourceBindFlags::ShaderResource)
        .texture2D(sz.x, sz.y);

    reflector.addOutput(kBlockerDistanceName, "Blocker distance")
        .format(ResourceFormat::R32Float)
        .bindFlags(ResourceBindFlags::UnorderedAccess | ResourceBindFlags::ShaderResource)
        .texture2D(sz.x, sz.y);

    reflector.addOutput(kCvName, "Receiver normal dot view direction")
        .format(ResourceFormat::R32Float)
        .bindFlags(ResourceBindFlags::UnorderedAccess | ResourceBindFlags::ShaderResource)
        .texture2D(sz.x, sz.y);

    return reflector;
}

void NSSMFeaturePass::execute(RenderContext* pRenderContext, const RenderData& renderData)
{
    auto& dict = renderData.getDictionary();
    if (mOptionsChanged)
    {
        auto flags = dict.getValue(kRenderPassRefreshFlags, RenderPassRefreshFlags::None);
        dict[Falcor::kRenderPassRefreshFlags] = flags | Falcor::RenderPassRefreshFlags::RenderOptionsChanged;
        mOptionsChanged = false;
    }

    // Get input and output textures.
    auto pShadowDepthTex = renderData.getTexture(kShadowDepthName);
    auto pGBufferDepthTex = renderData.getTexture(kGBufferDepthName);
    auto pGBufferNormalTex = renderData.getTexture(kGBufferNormalName);

    auto pShadowMaskTex = renderData.getTexture(kShadowMaskName);
    auto pNdotLTex = renderData.getTexture(kNdotLName);
    auto pBlockerDistanceTex = renderData.getTexture(kBlockerDistanceName);
    auto pCvTex = renderData.getTexture(kCvName);

    // Update frame dimension based on render pass output.
    FALCOR_ASSERT(pShadowMaskTex);
    updateFrameDim(uint2(pShadowMaskTex->getWidth(), pShadowMaskTex->getHeight()));

    // Clear outputs.
    float4 one = float4(1.f, 1.f, 1.f, 1.f);
    pRenderContext->clearUAV(pShadowMaskTex->getUAV().get(), one);
    pRenderContext->clearUAV(pNdotLTex->getUAV().get(), float4(0.f));
    pRenderContext->clearUAV(pBlockerDistanceTex->getUAV().get(), float4(0.f));
    pRenderContext->clearUAV(pCvTex->getUAV().get(), float4(0.f));

    // If there is no scene, just return.
    if (mpScene == nullptr)
    {
        return;
    }

    // Check for scene changes.
    if (is_set(mpScene->getUpdates(), IScene::UpdateFlags::RecompileNeeded))
    {
        recreatePrograms();
    }

    // Create compute program.
    if (!mpProgram)
    {
        mpProgram = Program::createCompute(mpDevice,
                        kNSSMFeaturePassProgramFile,
                        "nssmFeaturePass",
                        mpScene->getSceneDefines(),
                        SlangCompilerFlags::TreatWarningsAsErrors);
        mpVars = ProgramVars::create(mpDevice, mpProgram->getReflector());
    }

    // Set shader parameters.
    auto var = mpVars->getRootVar();
    var["gShadowDepth"] = pShadowDepthTex;
    var["gGBufferDepth"] = pGBufferDepthTex;
    var["gGBufferNormal"] = pGBufferNormalTex;
    var["gShadowMask"] = pShadowMaskTex;
    var["gNdotL"] = pNdotLTex;
    var["gBlockerDistance"] = pBlockerDistanceTex;
    var["gCv"] = pCvTex;
    var["PerFrameCB"]["gResolution"] = mFrameDim;
    var["PerFrameCB"]["gInvResolution"] = mInvFrameDim;

    if (mpScene->getCamera())
        mpScene->getCamera()->bindShaderData(var["PerFrameCB"]["gMainCamera"]);

    const std::vector<ref<Camera>>& allCameras = mpScene->getCameras();
    for (const auto& pCam : allCameras)
    {
        if (pCam->getName() != mShadowCameraName) continue;
        pCam->bindShaderData(var["PerFrameCB"]["gShadowCamera"]);
        break;
    }

    var["PerFrameCB"]["gShadowBias"] = mShadowBias;

    // TODO: Set light data if needed; for now the shader will derive a light direction from the shadow camera.

    // Dispatch compute shader.
    FALCOR_ASSERT(mpProgram);
    uint3 numGroups = div_round_up(uint3(mFrameDim.x, mFrameDim.y, 1u), mpProgram->getReflector()->getThreadGroupSize());
    mpState->setProgram(mpProgram);
    pRenderContext->dispatch(mpState.get(), mpVars.get(), numGroups);
}

void NSSMFeaturePass::renderUI(Gui::Widgets& widget)
{
    // No UI for now.
}

void NSSMFeaturePass::parseProperties(const Properties& props)
{
    for (const auto& [key, value] : props)
    {
        if (key == kShadowCamera)
            mShadowCameraName = (std::string)value;
        else if (key == kLightName)
            mLightName = (std::string)value;
        else if (key == kShadowBias)
            mShadowBias = (float)value;
    }
}

void NSSMFeaturePass::setScene(RenderContext* pRenderContext, const ref<Scene>& pScene)
{
    mUpdateFlagsConnection = {};
    mUpdateFlags = IScene::UpdateFlags::None;

    mpScene = pScene;

    if (pScene)
    {
        mUpdateFlagsConnection = mpScene->getUpdateFlagsSignal().connect([&](IScene::UpdateFlags flags) { mUpdateFlags |= flags; });
    }

    recreatePrograms();
}

void NSSMFeaturePass::recreatePrograms()
{
    mpProgram = nullptr;
    mpVars = nullptr;
}

void NSSMFeaturePass::updateFrameDim(const uint2 frameDim)
{
    FALCOR_ASSERT(frameDim.x > 0 && frameDim.y > 0);
    mFrameDim = frameDim;
    mInvFrameDim = 1.f / float2(frameDim);
}
