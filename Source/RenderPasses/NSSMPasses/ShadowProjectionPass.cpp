#include "ShadowProjectionPass.h"
#include "RenderGraph/RenderPassStandardFlags.h"

namespace
{
const std::string kShadowProjectionPassProgramFile = "RenderPasses/NSSMPasses/ShadowProjection.cs.slang";

const std::string kShadowDepthName = "shadowDepth";
const std::string kGBufferDepthName = "GBufferDepth";
const std::string kShadowMaskName = "shadowMask";
// Scripting options.
const char kMainCamera[] = "mainCamera";
const char kShadowCamera[] = "shadowCamera";
const char kShadowBias[] = "shadowBias";

const std::string kShadowProjectionPassData = "gShadowProjectionPassData";
} // namespace

ShadowProjectionPass::ShadowProjectionPass(ref<Device> pDevice, const Properties& props) : RenderPass(pDevice)
{
    parseProperties(props);

    // Initialize compute state
    mpState = ComputeState::create(mpDevice);

    mpFbo = Fbo::create(mpDevice);
}

Properties ShadowProjectionPass::getProperties() const
{
    Properties props;
    props[kShadowCamera] = mShadowCameraName;
    props[kShadowBias] = mShadowBias;
    return props;
}

RenderPassReflection ShadowProjectionPass::reflect(const CompileData& compileData)
{
    const uint2 sz = RenderPassHelpers::calculateIOSize(RenderPassHelpers::IOSize::Default, {}, compileData.defaultTexDims);
    
    RenderPassReflection reflector;
    reflector.addInput(kShadowDepthName, "Shadow Depth Map")
        .bindFlags(ResourceBindFlags::ShaderResource);
    reflector.addInput(kGBufferDepthName, "G-Buffer Depth buffer")
        .bindFlags(ResourceBindFlags::ShaderResource);
    reflector.addOutput(kShadowMaskName, "Shadow mask")
        .format(ResourceFormat::R8Unorm)
        .bindFlags(ResourceBindFlags::UnorderedAccess | ResourceBindFlags::ShaderResource)
        .texture2D(sz.x, sz.y);
    return reflector;
}

void ShadowProjectionPass::execute(RenderContext* pRenderContext, const RenderData& renderData)
{
    // renderData holds the requested resources
    // auto& pTexture = renderData.getTexture("src");

    // Update refresh flag if options that affect the output have changed.
    auto& dict = renderData.getDictionary();
    if (mOptionsChanged)
    {
        auto flags = dict.getValue(kRenderPassRefreshFlags, RenderPassRefreshFlags::None);
        dict[Falcor::kRenderPassRefreshFlags] = flags | Falcor::RenderPassRefreshFlags::RenderOptionsChanged;
        mOptionsChanged = false;
    }

    // get input and output textures
    auto pShadowDepthTex = renderData.getTexture(kShadowDepthName);
    auto pGBufferDepthTex = renderData.getTexture(kGBufferDepthName);
    auto pShadowMaskTex = renderData.getTexture(kShadowMaskName);

    // Update frame dimension based on render pass output.
    FALCOR_ASSERT(pShadowMaskTex);
    updateFrameDim(uint2(pShadowMaskTex->getWidth(), pShadowMaskTex->getHeight()));

    // clear target
    pRenderContext->clearUAV(pShadowMaskTex->getUAV().get(), float4(1.f, 1.f, 1.f, 1.f));

    // If there is no scene, clear target and return.
    if (mpScene == nullptr)
    {
        return;
    }

    // Check for scene changes.
    if (is_set(mpScene->getUpdates(), IScene::UpdateFlags::RecompileNeeded))
    {
        recreatePrograms();
    }

    // Create depth pass program.
    if (!mpProgram)
    {
        mpProgram = Program::createCompute(mpDevice,
                        kShadowProjectionPassProgramFile,
                        "shadowProjection",
                        mpScene->getSceneDefines(),
                        SlangCompilerFlags::TreatWarningsAsErrors);
        mpVars = ProgramVars::create(mpDevice, mpProgram->getReflector());
    }

    /*if (!mpShadowProjectionBlock)
    {
        ref<const ParameterBlockReflection> pReflection = mpProgram->getReflector()->getParameterBlock(kShadowProjectionPassData);
        FALCOR_ASSERT(pReflection);
        mpShadowProjectionBlock = ParameterBlock::create(mpDevice, pReflection);
        bindParameterBlock();
    }

    mpVars->setParameterBlock(kShadowProjectionPassData, mpShadowProjectionBlock);*/

    // set shader parameters
    auto var = mpVars->getRootVar();
    var["gShadowDepth"] = pShadowDepthTex;
    var["gGBufferDepth"] = pGBufferDepthTex;
    var["gShadowMask"] = pShadowMaskTex;
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

    // dispatch CS
    FALCOR_ASSERT(mpProgram);
    uint3 numGroups = div_round_up(uint3(mFrameDim.x, mFrameDim.y, 1u), mpProgram->getReflector()->getThreadGroupSize());
    mpState->setProgram(mpProgram);
    pRenderContext->dispatch(mpState.get(), mpVars.get(), numGroups);
}

void ShadowProjectionPass::renderUI(Gui::Widgets& widget)
{
    // Controls for output size.
    // SKIP this, not using UI
}

void ShadowProjectionPass::parseProperties(const Properties& props)
{
    for (const auto& [key, value] : props)
    {
        if (key == kShadowCamera)
            mShadowCameraName = (std::string)value;
        else if (key == kShadowBias)
            mShadowBias = (float)value;
    }
}

void ShadowProjectionPass::setScene(RenderContext* pRenderContext, const ref<Scene>& pScene)
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

void ShadowProjectionPass::recreatePrograms()
{
    mpProgram = nullptr;
    mpVars = nullptr;
}

void ShadowProjectionPass::updateFrameDim(const uint2 frameDim)
{
    FALCOR_ASSERT(frameDim.x > 0 && frameDim.y > 0);
    mFrameDim = frameDim;
    mInvFrameDim = 1.f / float2(frameDim);
}

ref<Texture> ShadowProjectionPass::getOutput(const RenderData& renderData) const
{
    // This helper fetches the render pass output with the given name and verifies it has the correct size.
    FALCOR_ASSERT(mFrameDim.x > 0 && mFrameDim.y > 0);
    auto pTex = renderData.getTexture(kShadowMaskName);
    if (pTex && (pTex->getWidth() != mFrameDim.x || pTex->getHeight() != mFrameDim.y))
    {
        FALCOR_THROW("ShadowProjectionPass: Pass output has mismatching size.");
    }
    return pTex;
}